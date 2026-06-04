import os, json, time, hashlib, shutil, asyncio, logging
from pathlib import Path
from typing import Dict, List
from agents.base_agent import BaseAgent

logger = logging.getLogger("doutor.master_key")

class MasterKeyAgent(BaseAgent):
    def __init__(self, config: Dict, router):
        super().__init__("the_master_key", config, router)
        self.snapshot_dir = Path("cache/snapshots")
        self.snapshot_dir.mkdir(parents=True, exist_ok=True)
        self.git_enabled = shutil.which("git") is not None

    async def create_full_backup(self, run_id: str) -> str:
        timestamp = int(time.time())
        backup_name = f"snapshot_{run_id}_{timestamp}"
        backup_path = self.snapshot_dir / backup_name
        backup_path.mkdir(parents=True, exist_ok=True)
        ignore = shutil.ignore_patterns('.git', 'node_modules', '__pycache__', 'data', 'cache')
        root_dir = Path(__file__).parent.parent
        shutil.copytree(root_dir, backup_path, ignore=ignore, dirs_exist_ok=True)
        logger.info(f"[MasterKey] Full backup: {backup_path}")
        return str(backup_path)

    async def restore_full_backup(self, snapshot_path: str) -> dict:
        sp = Path(snapshot_path)
        if not sp.exists():
            return {"status": "error", "msg": "Snapshot not found"}
        root_dir = Path(__file__).parent.parent
        for item in sp.iterdir():
            dst = root_dir / item.name
            if item.is_dir():
                shutil.copytree(item, dst, dirs_exist_ok=True)
            else:
                shutil.copy2(item, dst)
        logger.info(f"[MasterKey] Restored from: {snapshot_path}")
        return {"status": "restored", "path": snapshot_path}

    async def create_snapshot(self, run_id: str, paths: List[str]) -> Dict:
        snapshot = {"run_id": run_id, "timestamp": time.time(), "files": {}, "git_state": None}
        try:
            if self.git_enabled:
                proc = await asyncio.create_subprocess_exec("git", "stash", "push", "-u", "-m", f"doutor-snapshot-{run_id}")
                await proc.wait()
                snapshot["git_state"] = "stashed"

            for p in paths:
                path = Path(p)
                if path.exists():
                    content = path.read_bytes()
                    h = hashlib.sha256(content).hexdigest()
                    snapshot["files"][str(path)] = {"hash": h, "size": len(content)}
                    backup_path = self.snapshot_dir / f"{run_id}_{path.name}.bak"
                    shutil.copy2(path, backup_path)

            meta_path = self.snapshot_dir / f"{run_id}_meta.json"
            meta_path.write_text(json.dumps(snapshot, indent=2), encoding="utf-8")
            return {"status": "success", "snapshot_id": run_id, "meta_path": str(meta_path), "files_backed_up": len(snapshot["files"])}
        except Exception as e:
            return {"status": "fail", "error": str(e)}

    async def restore_snapshot(self, run_id: str) -> Dict:
        meta_path = self.snapshot_dir / f"{run_id}_meta.json"
        if not meta_path.exists():
            return {"status": "fail", "error": "snapshot_not_found"}

        try:
            meta = json.loads(meta_path.read_text(encoding="utf-8"))

            if self.git_enabled and meta.get("git_state") == "stashed":
                proc = await asyncio.create_subprocess_exec("git", "stash", "pop")
                await proc.wait()

            restored = []
            warnings = []
            for file_str, info in meta.get("files", {}).items():
                backup_path = self.snapshot_dir / f"{run_id}_{Path(file_str).name}.bak"
                if backup_path.exists():
                    shutil.copy2(backup_path, file_str)
                    current_hash = hashlib.sha256(Path(file_str).read_bytes()).hexdigest()
                    if current_hash != info["hash"]:
                        warnings.append(f"hash_mismatch_on_{file_str}")
                    restored.append(file_str)

            return {"status": "success" if not warnings else "partial", "restored": restored, "warnings": warnings}
        except Exception as e:
            return {"status": "fail", "error": str(e)}

    async def intercept_and_execute(self, action_type: str, payload: Dict) -> Dict:
        blacklist = ["rm -rf /", ":(){:|:&};:", "mkfs", "dd if=/dev/zero"]
        cmd = payload.get("command", payload.get("content", ""))
        if any(b in cmd for b in blacklist):
            return {"status": "blocked", "reason": "blacklisted_command"}

        if action_type == "exec_shell":
            proc = await asyncio.create_subprocess_shell(cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
            stdout, stderr = await proc.communicate()
            return {"exit_code": proc.returncode, "stdout": stdout.decode(errors="replace")[:1000], "stderr": stderr.decode(errors="replace")[:500]}
        elif action_type == "write_file":
            path, content = payload.get("path"), payload.get("content", "")
            Path(path).parent.mkdir(parents=True, exist_ok=True)
            Path(path).write_text(content, encoding="utf-8")
            return {"exit_code": 0, "written": True, "path": path}
        return {"exit_code": 0, "note": "unsupported_action_type"}

    async def bypass_confirmation_loop(self, tool_name: str, args: Dict) -> Dict:
        return await self.intercept_and_execute(tool_name, args)

    def _log(self, data: Dict):
        entry = {"timestamp": time.time(), "status": data.get("status"), "snapshot_id": data.get("snapshot_id"), "error": data.get("error")}
        log_path = Path(self.config.get("log_path", "logs/master_key_decisions.jsonl"))
        log_path.parent.mkdir(parents=True, exist_ok=True)
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, default=str) + "\n")

# EOF
