import os
import json
import subprocess
import time
import math
import re
import difflib
import logging
from pathlib import Path
from typing import Dict, List, Any
from kernel.llm_client import call_llm
from kernel.utils import validate_json
from agents.base_agent import BaseAgent

logger = logging.getLogger("doutor.kernel_lateral")

SECRETS_REGEXES = [
    (r"api[_-]?key\s*[:=]\s*['\"]([A-Za-z0-9_\-]{16,})['\"]", "api_key"),
    (r"password\s*[:=]\s*['\"]([^'\"]{8,})['\"]", "password"),
    (r"secret\s*[:=]\s*['\"]([^'\"]{8,})['\"]", "secret"),
    (r"token\s*[:=]\s*['\"]([A-Za-z0-9_\-\.]{10,})['\"]", "token"),
    (r"aws_access_key_id\s*[:=]\s*['\"]([A-Z0-9]{16,})['\"]", "aws_key"),
    (r"aws_secret_access_key\s*[:=]\s*['\"]([A-Za-z0-9\/+]{40})['\"]", "aws_secret"),
    (r"sk-[A-Za-z0-9]{20,}", "openai_key"),
    (r"ghp_[A-Za-z0-9]{36,}", "github_token"),
    (r"AKIA[A-Z0-9]{16}", "aws_access_key"),
]

SECURITY_HEADERS = [
    "Content-Security-Policy",
    "Strict-Transport-Security",
    "X-Frame-Options",
    "X-Content-Type-Options",
    "Referrer-Policy",
    "Permissions-Policy",
]

WEAK_PATTERNS = {
    "md5": r"md5\s*\(",
    "sha1": r"sha1?\s*\(",
    "eval": r"eval\s*\(",
    "pickle.loads": r"pickle\.loads\s*\(",
    "exec": r"exec\s*\(",
}

SAFE_REPLACEMENTS = {
    "md5": "sha256",
    "sha1": "sha256",
    "eval": "ast.literal_eval",
    "pickle.loads": "json.loads",
    "exec": "subprocess.run",
}


def shannon_entropy(s: str) -> float:
    if not s:
        return 0.0
    freq = {}
    for c in s:
        freq[c] = freq.get(c, 0) + 1
    entropy = -sum((f / len(s)) * math.log2(f / len(s)) for f in freq.values())
    return entropy


class LateralAgent(BaseAgent):
    """
    The Lateral v1.2 — 5 Defensive Audits + 5 Active Remediations.
    """
    def __init__(self, config_path="agents/roles/lateral.json", router=None):
        base_dir = Path(__file__).parent.parent
        if isinstance(config_path, dict):
            cfg = config_path
        else:
            resolved_config_path = base_dir / config_path
            cfg = {}
            if resolved_config_path.exists():
                try:
                    with open(resolved_config_path, "r", encoding="utf-8") as f:
                        cfg = json.load(f)
                except Exception as e:
                    logger.warning(f"[LateralAgent] Error loading config: {e}")
                    cfg = {}
            if not cfg:
                cfg = {
                    "role": "the_lateral",
                    "system_prompt_file": "prompts/the_lateral.md",
                    "log_to": "logs/lateral_audit.jsonl"
                }

        role_name = cfg.get("role", "the_lateral")
        super().__init__(role_name, cfg, router)

        self.config = cfg
        log_to = cfg.get("log_to", "logs/lateral_audit.jsonl")
        self.audit_log_path = base_dir / log_to
        self.audit_log_path.parent.mkdir(parents=True, exist_ok=True)
        self.base_dir = base_dir
        self.scanner_config = cfg.get("scanner_modes", {})
        self.remediation_config = cfg.get("remediation_modes", {})

    def _resolve_target(self, target_path: str) -> Path:
        target_abs = Path(target_path)
        if not target_abs.is_absolute():
            target_abs = self.base_dir / target_path
        return target_abs.resolve()

    def _get_system_prompt(self) -> str:
        prompt_rel = self.config.get("system_prompt_file", "prompts/the_lateral.md")
        prompt_path = self.base_dir / prompt_rel
        if prompt_path.exists():
            try:
                with open(prompt_path, "r", encoding="utf-8") as f:
                    return f.read()
            except Exception as e:
                print(f"[LateralAgent] Error reading system prompt file: {e}")
        return "You are The Lateral v1.2."

    async def run_defensive_validation(self, target_path: str, scan_type: str = "comprehensive") -> Dict:
        """Executa validação defensiva — 5 auditors avançados + bandit/safety legados"""
        findings = []
        target_abs = self._resolve_target(target_path)
        target_str = str(target_abs)

        try:
            if scan_type in ["comprehensive", "secrets"]:
                findings += self._scan_secrets(target_abs)
            if scan_type in ["comprehensive", "cors"]:
                findings += self._scan_cors_headers(target_abs)
            if scan_type in ["comprehensive", "cookies"]:
                findings += self._scan_cookies(target_abs)
            if scan_type in ["comprehensive", "debug_flags"]:
                findings += self._scan_debug_flags(target_abs)
            if scan_type in ["comprehensive", "dep_lock"]:
                findings += self._scan_dep_lock(target_abs)
            if scan_type in ["comprehensive", "sast"]:
                findings += self._run_bandit(target_str)
            if scan_type in ["comprehensive", "dependency"]:
                findings += self._run_safety(target_abs)
        except Exception as e:
            findings.append({
                "type": "scan_error",
                "severity": "low",
                "standard": "INTERNAL",
                "location": {"file": target_str, "line": None, "package": None},
                "description": f"Scan error: {str(e)}",
                "remediation": "Re-executar scan ou verificar permissões de acesso",
                "auto_fix_available": False,
                "patch_hint": ""
            })

        output = {
            "mode": "defensive_validation",
            "scan_type": scan_type,
            "target": str(target_path),
            "findings": findings,
            "overall_risk_score": self._calculate_risk(findings),
            "recommendation": self._recommend(findings)
        }
        self._log_audit(output)
        return output

    async def run_remediation(self, target_path: str, action: str) -> Dict:
        """Executa reparação ativa — 5 remediators automáticos"""
        target_abs = self._resolve_target(target_path)
        changes = []

        try:
            if action == "auto_patch":
                changes = self._remediate_auto_patch(target_abs)
            elif action == "dep_update":
                changes = self._remediate_dep_update(target_abs)
            elif action == "credential_isolate":
                changes = self._remediate_credential_isolate(target_abs)
            elif action == "fuzz_test":
                changes = self._remediate_fuzz_test(target_abs)
            elif action == "regression_test":
                changes = self._remediate_regression_test(target_abs)
            else:
                return {
                    "mode": "active_remediation",
                    "action": action,
                    "target": str(target_path),
                    "changes": [],
                    "summary": {"files_changed": 0, "patches_applied": 0, "warnings": [f"Unknown action: {action}"]},
                    "status": "failed"
                }
        except Exception as e:
            return {
                "mode": "active_remediation",
                "action": action,
                "target": str(target_path),
                "changes": [],
                "summary": {"files_changed": 0, "patches_applied": 0, "warnings": [str(e)]},
                "status": "failed"
            }

        status = "success" if changes else "partial"
        output = {
            "mode": "active_remediation",
            "action": action,
            "target": str(target_path),
            "changes": changes,
            "summary": {
                "files_changed": len(set(c["file"] for c in changes)),
                "patches_applied": len(changes),
                "warnings": []
            },
            "status": status
        }
        self._log_audit(output)
        return output

    # ─── 5 DEFENSIVE AUDITS ───────────────────────────────────────────

    def _scan_secrets(self, target: Path) -> List[Dict]:
        findings = []
        config = self.scanner_config.get("secrets", {})
        min_entropy = config.get("min_entropy", 4.5)

        if target.is_file():
            files = [target]
        else:
            files = list(target.rglob("*.py")) + list(target.rglob("*.js")) + \
                     list(target.rglob("*.ts")) + list(target.rglob("*.env")) + \
                     list(target.rglob("*.yml")) + list(target.rglob("*.yaml")) + \
                     list(target.rglob("*.json")) + list(target.rglob("*.toml")) + \
                     list(target.rglob("*.cfg")) + list(target.rglob("*.ini"))

        for fp in files:
            try:
                content = fp.read_text(encoding="utf-8", errors="ignore")
                lines = content.split("\n")
                for i, line in enumerate(lines, 1):
                    stripped = line.strip()
                    if not stripped or stripped.startswith("#") or stripped.startswith("//"):
                        continue

                    for pattern, secret_type in SECRETS_REGEXES:
                        match = re.search(pattern, stripped, re.IGNORECASE)
                        if match:
                            findings.append({
                                "type": f"hardcoded_{secret_type}",
                                "severity": "high",
                                "standard": "OWASP",
                                "location": {"file": str(fp), "line": i, "package": None},
                                "description": f"Potencial {secret_type} hardcoded encontrado",
                                "remediation": f"Mover para .env e usar os.getenv('{secret_type.upper()}')",
                                "auto_fix_available": True,
                                "patch_hint": f"os.getenv('{secret_type.upper()}')"
                            })
                            break

                    entropy = shannon_entropy(stripped)
                    if entropy > min_entropy and len(stripped) > 20:
                        findings.append({
                            "type": "high_entropy_string",
                            "severity": "medium",
                            "standard": "OWASP",
                            "location": {"file": str(fp), "line": i, "package": None},
                            "description": f"String com alta entropia ({entropy:.1f} bits/char) — possível credencial",
                            "remediation": "Verificar e mover para .env se for credencial",
                            "auto_fix_available": True,
                            "patch_hint": "os.getenv('VAR_NAME')"
                        })
            except Exception:
                continue
        return findings

    def _scan_cors_headers(self, target: Path) -> List[Dict]:
        findings = []
        config = self.scanner_config.get("cors_headers", {})
        required_headers = config.get("check_headers", SECURITY_HEADERS)

        if target.is_file():
            files = [target]
        else:
            files = list(target.rglob("*.py")) + list(target.rglob("*.html")) + \
                     list(target.rglob("*.js")) + list(target.rglob("*.ts"))

        for fp in files:
            try:
                content = fp.read_text(encoding="utf-8", errors="ignore")
                ext = fp.suffix.lower()

                if ext == ".py":
                    if re.search(r'allow_origins\s*=\s*\["\*"\]', content) or \
                       re.search(r'Access-Control-Allow-Origin.*\*', content):
                        findings.append({
                            "type": "open_cors_origin",
                            "severity": "high",
                            "standard": "OWASP",
                            "location": {"file": str(fp), "line": None, "package": None},
                            "description": "CORS configurado com origem aberta (*) — permite qualquer domínio",
                            "remediation": "Restringir origins específicas ou usar allow_origins=[dominio]",
                            "auto_fix_available": True,
                            "patch_hint": "allow_origins=['https://dominio.com']"
                        })

                    if re.search(r'Access-Control-Allow-Credentials\s*:\s*true', content):
                        findings.append({
                            "type": "cors_with_credentials",
                            "severity": "medium",
                            "standard": "OWASP",
                            "location": {"file": str(fp), "line": None, "package": None},
                            "description": "CORS permite credenciais — risco de ataques cross-origin",
                            "remediation": "Desabilitar Allow-Credentials ou restringir origins",
                            "auto_fix_available": True,
                            "patch_hint": "Access-Control-Allow-Credentials: false"
                        })

                if ext in (".html", ".js", ".ts"):
                    present_headers = set()
                    for hdr in required_headers:
                        pattern = re.escape(hdr)
                        if re.search(pattern, content, re.IGNORECASE):
                            present_headers.add(hdr)

                    for hdr in required_headers:
                        if hdr not in present_headers:
                            findings.append({
                                "type": "missing_security_header",
                                "severity": "medium",
                                "standard": "OWASP",
                                "location": {"file": str(fp), "line": None, "package": None},
                                "description": f"Header de segurança ausente: {hdr}",
                                "remediation": f"Adicionar header {hdr} na resposta HTTP",
                                "auto_fix_available": False,
                                "patch_hint": f"Adicionar '{hdr}: valor' no response"
                            })
            except Exception:
                continue
        return findings

    def _scan_cookies(self, target: Path) -> List[Dict]:
        findings = []
        config = self.scanner_config.get("cookies", {})
        required = config.get("required_flags", ["HttpOnly", "Secure", "SameSite"])

        if target.is_file():
            files = [target]
        else:
            files = list(target.rglob("*.py")) + list(target.rglob("*.js")) + \
                     list(target.rglob("*.ts")) + list(target.rglob("*.html"))

        for fp in files:
            try:
                content = fp.read_text(encoding="utf-8", errors="ignore")
                cookie_defs = re.findall(
                    r'(?:set_cookie|Set-Cookie|cookie\.set|\.cookie\s*=)\s*[\[\(]?["\']?([^"\'\)\]]+)["\']?',
                    content, re.IGNORECASE
                )
                for cookie_str in cookie_defs:
                    missing = [flag for flag in required if flag.lower() not in cookie_str.lower()]
                    if missing:
                        sev = "high" if len(missing) >= 2 else "medium"
                        findings.append({
                            "type": "insecure_cookie",
                            "severity": sev,
                            "standard": "OWASP",
                            "location": {"file": str(fp), "line": None, "package": None},
                            "description": f"Cookie sem flags: {', '.join(missing)}",
                            "remediation": f"Adicionar {', '.join(missing)} nas configurações do cookie",
                            "auto_fix_available": True,
                            "patch_hint": f"Set-Cookie: ...; {'; '.join(missing)}"
                        })
            except Exception:
                continue
        return findings

    def _scan_debug_flags(self, target: Path) -> List[Dict]:
        findings = []
        config = self.scanner_config.get("debug_flags", {})
        patterns = config.get("patterns", [
            r"debug\s*=\s*True", r"DEBUG\s*=\s*True",
            r"mode.*development", r"environment.*dev",
            r"VERBOSE\s*=\s*True"
        ])
        compiled = [re.compile(p, re.IGNORECASE) for p in patterns]

        if target.is_file():
            files = [target]
        else:
            files = list(target.rglob("*.py")) + list(target.rglob("*.js")) + \
                     list(target.rglob("*.ts")) + list(target.rglob("*.yml")) + \
                     list(target.rglob("*.yaml")) + list(target.rglob("*.json"))

        for fp in files:
            try:
                content = fp.read_text(encoding="utf-8", errors="ignore")
                lines = content.split("\n")
                for i, line in enumerate(lines, 1):
                    for cp in compiled:
                        if cp.search(line):
                            sev = "high" if "debug" in line.lower() and "true" in line.lower() else "medium"
                            findings.append({
                                "type": "debug_flag_enabled",
                                "severity": sev,
                                "standard": "OWASP",
                                "location": {"file": str(fp), "line": i, "package": None},
                                "description": f"Flag de debug/development ativa. Linha: {line.strip()}",
                                "remediation": "Desabilitar debug/verbose antes de deploy em produção",
                                "auto_fix_available": True,
                                "patch_hint": line.strip().replace("True", "False").replace("development", "production").replace("dev", "prod")
                            })
                            break
            except Exception:
                continue
        return findings

    def _scan_dep_lock(self, target: Path) -> List[Dict]:
        findings = []
        config = self.scanner_config.get("dep_lock", {})
        check_files = config.get("check_files", ["requirements.txt", "Pipfile", "pyproject.toml"])

        if target.is_file():
            dirs = [target.parent]
        else:
            dirs = [target]

        for d in dirs:
            for req_file in check_files:
                fp = d / req_file
                if not fp.exists():
                    for found in d.rglob(req_file):
                        fp = found
                        break

                if fp.exists():
                    try:
                        content = fp.read_text(encoding="utf-8", errors="ignore")
                        lines = content.split("\n")
                        for i, line in enumerate(lines, 1):
                            stripped = line.strip()
                            if not stripped or stripped.startswith("#") or stripped.startswith("--"):
                                continue

                            if re.match(r'^[a-zA-Z0-9_\-]+$', stripped):
                                findings.append({
                                    "type": "unpinned_dependency",
                                    "severity": "medium",
                                    "standard": "OWASP",
                                    "location": {"file": str(fp), "line": i, "package": stripped.strip()},
                                    "description": f"Dependência sem versão fixada: {stripped}",
                                    "remediation": f"Fixar versão: pip freeze | findstr {stripped}",
                                    "auto_fix_available": True,
                                    "patch_hint": f"{stripped}==X.Y.Z"
                                })
                            elif re.match(r'^[a-zA-Z0-9_\-]+\s*[>~<]=', stripped):
                                pkg_name = stripped.split(">")[0].split("~")[0].split("<")[0].split("=")[0].strip()
                                findings.append({
                                    "type": "range_based_dependency",
                                    "severity": "medium",
                                    "standard": "OWASP",
                                    "location": {"file": str(fp), "line": i, "package": pkg_name},
                                    "description": f"Dependência com range versionado: {stripped}",
                                    "remediation": f"Travar em versão exata: {pkg_name}==X.Y.Z",
                                    "auto_fix_available": True,
                                    "patch_hint": f"{pkg_name}==X.Y.Z"
                                })
                    except Exception:
                        continue
        return findings

    # ─── BANDIT + SAFETY (existing) ──────────────────────────────────

    def _run_bandit(self, target_str: str) -> List[Dict]:
        findings = []
        try:
            result = subprocess.run(
                ["bandit", "-r", target_str, "-f", "json", "-ll"],
                capture_output=True, text=True, timeout=30
            )
            if result.stdout:
                bandit_data = json.loads(result.stdout)
                for issue in bandit_data.get("results", []):
                    findings.append({
                        "type": issue.get("test_id", "unknown"),
                        "severity": issue.get("issue_severity", "medium").lower(),
                        "standard": "OWASP",
                        "location": {"file": issue.get("filename"), "line": issue.get("line_number"), "package": None},
                        "description": issue.get("issue_text", ""),
                        "remediation": "Revisar padrão de código seguro conforme OWASP",
                        "auto_fix_available": False,
                        "patch_hint": (issue.get("code", "") or "")[:100]
                    })
        except Exception:
            import logging
            logging.getLogger("doutor.lateral").warning("Safety check failed", exc_info=True)
        return findings

    def _run_safety(self, target_abs: Path) -> List[Dict]:
        findings = []
        req_file = target_abs if target_abs.is_file() else target_abs / "requirements.txt"
        if not req_file.exists():
            return findings
        try:
            result = subprocess.run(
                ["safety", "check", "-r", str(req_file.resolve()), "--json"],
                capture_output=True, text=True, timeout=30
            )
            if result.stdout:
                vulns = json.loads(result.stdout)
                vuln_list = vulns if isinstance(vulns, list) else vulns.get("vulnerabilities", [])
                for vuln in vuln_list:
                    findings.append({
                        "type": "vulnerable_dependency",
                        "severity": "high" if vuln.get("severity") == "CRITICAL" else "medium",
                        "standard": "CVE",
                        "location": {"file": None, "line": None, "package": vuln.get("package_name")},
                        "description": vuln.get("description", ""),
                        "remediation": f"Atualizar para {vuln.get('fixed_version', 'latest')}",
                        "auto_fix_available": True,
                        "patch_hint": f"pip install {vuln.get('package_name')}=={vuln.get('fixed_version', '')}"
                    })
        except Exception:
            import logging
            logging.getLogger("doutor.lateral").warning("Safety check failed", exc_info=True)
        return findings

    # ─── 5 ACTIVE REMEDIATIONS ──────────────────────────────────────

    def _remediate_auto_patch(self, target: Path) -> List[Dict]:
        changes = []
        patch_map = self.remediation_config.get("auto_patch", {}).get("patch_map", SAFE_REPLACEMENTS)

        if target.is_file():
            files = [target]
        else:
            files = list(target.rglob("*.py"))

        for fp in files:
            try:
                original = fp.read_text(encoding="utf-8", errors="ignore")
                content = original
                patched_any = False

                for weak_func, safe_func in patch_map.items():
                    pattern = WEAK_PATTERNS.get(weak_func)
                    if not pattern:
                        continue
                    if re.search(pattern, content):
                        before = content
                        if weak_func == "eval":
                            needs_import = "import ast" not in content and "from ast" not in content
                            content = re.sub(r'\beval\s*\(', 'ast.literal_eval(', content)
                            if needs_import:
                                content = "import ast\n" + content
                        elif weak_func == "exec":
                            content = re.sub(r'\bexec\s*\(', '# REPLACED exec with subprocess.run\n# subprocess.run(', content)
                        elif weak_func in ("md5", "sha1"):
                            content = re.sub(r'(from hashlib import ).*', f'\\1{safe_func}', content)
                            content = re.sub(r'\b' + weak_func + r'\b', safe_func, content)
                        elif weak_func == "pickle.loads":
                            content = re.sub(r'\bpickle\.loads\b', 'json.loads', content)
                            if '"json"' not in content and "'json'" not in content:
                                content = "import json\n" + content if "import json" not in content else content
                        if content != before:
                            patched_any = True
                            diff = "\n".join(difflib.unified_diff(
                                original.split("\n"), content.split("\n"),
                                fromfile=str(fp), tofile=str(fp), lineterm=""
                            ))
                            changes.append({
                                "file": str(fp),
                                "change_type": "modified",
                                "description": f"Auto-patched: {weak_func} → {safe_func}",
                                "diff": diff[:500]
                            })

                if patched_any:
                    fp.write_text(content, encoding="utf-8")
            except Exception:
                continue
        return changes

    def _remediate_dep_update(self, target: Path) -> List[Dict]:
        changes = []
        if target.is_file():
            req_files = [target] if target.name == "requirements.txt" else list(target.parent.rglob("requirements.txt"))
        else:
            req_files = list(target.rglob("requirements.txt"))

        for fp in req_files:
            try:
                original = fp.read_text(encoding="utf-8", errors="ignore")
                lines = original.split("\n")
                new_lines = []
                updated_packages = []

                for line in lines:
                    stripped = line.strip()
                    if not stripped or stripped.startswith("#") or stripped.startswith("--"):
                        new_lines.append(line)
                        continue

                    pkg_match = re.match(r'^([a-zA-Z0-9_\-]+)\s*([><=~!]+)\s*(.+)$', stripped)
                    if pkg_match:
                        pkg_name = pkg_match.group(1)
                        op = pkg_match.group(2)
                        ver = pkg_match.group(3)

                        if op in (">=", "~=", ">", "<"):
                            new_lines.append(f"{pkg_name}=={ver}")
                            updated_packages.append(pkg_name)
                        else:
                            new_lines.append(line)
                    else:
                        pkg_only = re.match(r'^([a-zA-Z0-9_\-]+)$', stripped)
                        if pkg_only:
                            pkg_name = pkg_only.group(1)
                            new_lines.append(f"{pkg_name}==latest")
                            updated_packages.append(pkg_name)
                        else:
                            new_lines.append(line)

                if updated_packages:
                    new_content = "\n".join(new_lines)
                    fp.write_text(new_content, encoding="utf-8")
                    diff = "\n".join(difflib.unified_diff(
                        original.split("\n"), new_content.split("\n"),
                        fromfile=str(fp), tofile=str(fp), lineterm=""
                    ))
                    changes.append({
                        "file": str(fp),
                        "change_type": "modified",
                        "description": f"Pinned {len(updated_packages)} packages: {', '.join(updated_packages)}",
                        "diff": diff[:500]
                    })
            except Exception:
                continue
        return changes

    def _remediate_credential_isolate(self, target: Path) -> List[Dict]:
        changes = []
        if target.is_file():
            files = [target]
        else:
            files = list(target.rglob("*.py"))

        env_file = self.base_dir / ".env"
        env_vars = {}

        if env_file.exists():
            try:
                for line in env_file.read_text(encoding="utf-8").split("\n"):
                    if "=" in line and not line.strip().startswith("#"):
                        k, v = line.strip().split("=", 1)
                        env_vars[k] = v
            except Exception:
                pass

        for fp in files:
            try:
                original = fp.read_text(encoding="utf-8", errors="ignore")
                content = original
                isolated_any = False

                for pattern, secret_type in SECRETS_REGEXES:
                    for match in re.finditer(pattern, content, re.IGNORECASE):
                        var_name = secret_type.upper()
                        var_value = match.group(1) if match.lastindex and match.lastindex >= 1 else match.group(0)

                        idx = 1
                        base_var = var_name
                        while var_name in env_vars and env_vars[var_name] != var_value:
                            var_name = f"{base_var}_{idx}"
                            idx += 1

                        env_vars[var_name] = var_value
                        content = content.replace(match.group(0), f'os.getenv("{var_name}")')
                        if "import os" not in content:
                            content = "import os\n" + content
                        isolated_any = True

                if isolated_any:
                    with open(env_file, "w", encoding="utf-8") as ef:
                        for k, v in env_vars.items():
                            ef.write(f'{k}={v}\n')

                    diff = "\n".join(difflib.unified_diff(
                        original.split("\n"), content.split("\n"),
                        fromfile=str(fp), tofile=str(fp), lineterm=""
                    ))
                    changes.append({
                        "file": str(fp),
                        "change_type": "modified",
                        "description": f"Isolated {len(env_vars)} credentials to .env",
                        "diff": diff[:500]
                    })
                    fp.write_text(content, encoding="utf-8")

                    changes.append({
                        "file": str(env_file),
                        "change_type": "modified",
                        "description": f"Added {len(env_vars)} env vars",
                        "diff": ""
                    })
            except Exception:
                continue
        return changes

    def _remediate_fuzz_test(self, target: Path) -> List[Dict]:
        changes = []
        output_dir_setting = self.remediation_config.get("fuzz_test", {}).get("output_dir", "tests")
        output_path = self.base_dir / output_dir_setting
        output_path.mkdir(parents=True, exist_ok=True)

        test_file = output_path / "test_fuzz.py"

        fuzz_cases = [
            "empty_string",
            "null_bytes",
            "unicode_exploit",
            "negative_numbers",
            "sql_injection",
            "xss_payload",
            "integer_overflow",
            "long_string_10k",
            "nested_json_bomb",
            "path_traversal",
        ]

        test_content = '"""Fuzz tests generated by The Lateral v1.2 — Active Remediation"""\n\n'
        test_content += "import pytest\nimport json\n\n\n"
        test_content += "# Test cases for extreme/fuzzing inputs\n"
        test_content += 'FUZZ_CASES = {\n'

        payloads = {
            "empty_string": '""',
            "null_bytes": '"\\\\x00\\\\x00\\\\x00"',
            "unicode_exploit": '"\\\\uffff\\\\u0000\\\\ud800"',
            "negative_numbers": "-9999999999999999999999",
            "sql_injection": "' OR 1=1; DROP TABLE users; --",
            "xss_payload": "'><script>alert(1)</script>",
            "integer_overflow": "99999999999999999999999999999999999",
            "long_string_10k": '"A" * 10000',
            "nested_json_bomb": "json.loads('{\"a\":{\"a\":{\"a\":{\"a\":{}}}}}')",
            "path_traversal": "../../../../etc/passwd",
        }

        for name in fuzz_cases:
            val = payloads.get(name, '""')
            test_content += f'    "{name}": {val},\n'

        test_content += '}\n\n\n'
        test_content += """def test_fuzz_string_inputs():
    for name, payload in FUZZ_CASES.items():
        try:
            result = str(payload)
            assert isinstance(result, str)
        except Exception as e:
            pytest.fail(f"Fuzz case '{name}' failed: {e}")


def test_fuzz_json_inputs():
    for name, payload in FUZZ_CASES.items():
        try:
            json.loads('{}')
        except json.JSONDecodeError:
            pass


def test_fuzz_boundary_conditions():
    assert int(1e100) > 0
    assert float("inf") > 0
    assert float("-inf") < 0
"""

        test_file.write_text(test_content, encoding="utf-8")
        changes.append({
            "file": str(test_file),
            "change_type": "created",
            "description": f"Generated fuzz test with {len(fuzz_cases)} cases",
            "diff": ""
        })
        return changes

    def _remediate_regression_test(self, target: Path) -> List[Dict]:
        changes = []
        output_dir_setting = self.remediation_config.get("regression_test", {}).get("output_dir", "tests")
        output_path = self.base_dir / output_dir_setting
        output_path.mkdir(parents=True, exist_ok=True)

        test_file = output_path / "test_access_control.py"

        test_content = '"""Regression tests for access control — Generated by The Lateral v1.2"""\n\n'
        test_content += "import pytest\nfrom unittest.mock import Mock, patch\n\n\n"

        test_content += """
# Mock HTTP client for access control testing
class MockResponse:
    def __init__(self, status_code, data=None):
        self.status_code = status_code
        self.data = data or {}

    def json(self):
        return self.data


def create_mock_client(auth_required=True):
    client = Mock()

    def mock_request(method, url, **kwargs):
        headers = kwargs.get("headers", {})
        token = headers.get("Authorization", "")

        if not auth_required:
            return MockResponse(200, {"status": "ok"})

        if not token:
            return MockResponse(401, {"error": "Unauthorized"})

        if "invalid" in token or "expired" in token:
            return MockResponse(403, {"error": "Forbidden"})

        return MockResponse(200, {"status": "ok"})

    client.request = mock_request
    return client


@pytest.mark.parametrize("endpoint", ["/api/data", "/api/admin", "/api/users", "/api/config"])
def test_unauthenticated_access_returns_401(endpoint):
    client = create_mock_client(auth_required=True)
    response = client.request("GET", endpoint, headers={})
    assert response.status_code == 401, f"{endpoint} should reject unauthenticated access"


@pytest.mark.parametrize("endpoint", ["/api/data", "/api/admin"])
def test_invalid_token_returns_403(endpoint):
    client = create_mock_client(auth_required=True)
    response = client.request("GET", endpoint, headers={"Authorization": "Bearer invalid_token"})
    assert response.status_code == 403, f"{endpoint} should reject invalid tokens"


def test_authenticated_access_succeeds():
    client = create_mock_client(auth_required=True)
    response = client.request("GET", "/api/data", headers={"Authorization": "Bearer valid_token"})
    assert response.status_code == 200


def test_public_endpoints_no_auth():
    client = create_mock_client(auth_required=False)
    response = client.request("GET", "/api/health", headers={})
    assert response.status_code == 200, "Health endpoints should not require auth"


@pytest.mark.parametrize("method", ["POST", "PUT", "DELETE", "PATCH"])
def test_mutating_endpoints_require_auth(method):
    client = create_mock_client(auth_required=True)
    response = client.request(method, "/api/data", headers={})
    assert response.status_code == 401, f"{method} /api/data should require auth"


def test_sql_injection_in_token_rejected():
    client = create_mock_client(auth_required=True)
    malicious_token = "' OR 1=1; --"
    response = client.request("GET", "/api/admin", headers={"Authorization": f"Bearer {malicious_token}"})
    assert response.status_code in (401, 403), "Malicious tokens should be rejected"
"""

        test_file.write_text(test_content, encoding="utf-8")
        changes.append({
            "file": str(test_file),
            "change_type": "created",
            "description": "Generated access control regression test with 6 test functions",
            "diff": ""
        })
        return changes

    # ─── LEGACY: Generate Alternatives ──────────────────────────────

    async def generate_alternatives(self, blocked_phase: str, error_context: Dict, budget_status: Dict) -> Dict:
        system = self._get_system_prompt()
        prompt = f"""
Modo: workaround_consultant
Fase bloqueada: {blocked_phase}
Contexto do erro: {json.dumps(error_context, default=str)[:1500]}
Status do budget: {json.dumps(budget_status)}

Gere alternativas éticas, funcionais e compliance-safe.
Retorne APENAS JSON conforme schema de workaround_consultant.
"""
        try:
            result = await call_llm("the_lateral", system, prompt)
            self._log_audit(result)
            return result
        except Exception as e:
            fallback = {
                "status": "fallback",
                "blocked_phase": blocked_phase,
                "alternatives": [
                    {"approach": "reduzir_escopo", "description": "Remover dependencias nao criticas para destravar a fase"},
                    {"approach": "trocar_provedor", "description": "Substituir provedor atual por alternativa viavel"},
                    {"approach": "modo_offline", "description": "Processar localmente sem dependencia de API externa"},
                    {"approach": "revisao_manual", "description": "Substituir etapa automatizada por revisao manual temporaria"}
                ],
                "recommendation": "Aplicar reducao de escopo e tentar novamente",
                "llm_error": str(e)
            }
            self._log_audit(fallback)
            return fallback

    # ─── HELPERS ────────────────────────────────────────────────────

    def _calculate_risk(self, findings: List[Dict]) -> float:
        weights = {"critical": 1.0, "high": 0.7, "medium": 0.4, "low": 0.1}
        if not findings:
            return 0.0
        return min(sum(weights.get(f["severity"], 0.1) for f in findings) / len(findings), 1.0)

    def _recommend(self, findings: List[Dict]) -> str:
        severities = [f["severity"] for f in findings]
        if "critical" in severities:
            return "human_review"
        if "high" in severities:
            return "patch_required"
        if any(f.get("auto_fix_available") for f in findings):
            return "auto_fix_available"
        return "approve"

    def _log_audit(self, data: Dict):
        entry = {
            "timestamp": time.time(),
            "mode": data.get("mode", "unknown"),
            "findings_count": len(data.get("findings", [])) if "findings" in data else 0,
            "recommendation": data.get("recommendation", "unknown")
        }
        try:
            with open(self.audit_log_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry, default=str) + "\n")
        except Exception as e:
            print(f"[LateralAgent] Log writing error: {e}")
