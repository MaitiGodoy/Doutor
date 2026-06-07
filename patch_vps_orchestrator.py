#!/usr/bin/env python3
"""Patch VPS orchestrator.py to integrate HermesBridge"""
import sys

VPS_PATH = "/var/www/maiti-godoy-portal/doutor/kernel/orchestrator.py"

with open(VPS_PATH) as f:
    content = f.read()

# Patch 1: Add Hermes import after last import
if "from .hermes_bridge import HermesBridge" not in content:
    content = content.replace(
        "from .seo_orchestrator import SEOOrchestrator",
        "from .seo_orchestrator import SEOOrchestrator\nfrom .hermes_bridge import HermesBridge"
    )
    print("Patch 1: Hermes import added")

# Patch 2: Add Hermes init after AdminChat init
if "self.hermes = None" not in content and "self.hermes = HermesBridge" not in content:
    content = content.replace(
        "self.admin = AdminChat(self.provider_router, self.seo, root_path)",
        "self.admin = AdminChat(self.provider_router, self.seo, root_path)\n        self.hermes = HermesBridge()\n        self.hermes_participation = []"
    )
    print("Patch 2: Hermes init added")

# Patch 3: Add Hermes to health check
old_health = '''return {
            "status": "ok",
            "version": "5.0.0",
            "uptime_s": int(time.time() - self.start_time),'''
new_health = '''hermes_status = self.hermes.get_stats()
        return {
            "status": "ok",
            "version": "5.0.0",
            "hermes": hermes_status,
            "uptime_s": int(time.time() - self.start_time),'''
if old_health in content and "hermes" not in content[content.find("return {"):content.find("return {")+200]:
    content = content.replace(old_health, new_health)
    print("Patch 3: Hermes health added")

# Patch 4: Add Hermes participation in execute, after Warden check
old_warden_block = '''if warden_result["status"] == "blocked":
            return {
                "status": "blocked",
                "phase": "warden",
                "details": warden_result["details"],
                "warden_report": warden_result,
                "execution_time_ms": (time.time() - execution_start) * 1000
            }'''
new_warden_block = old_warden_block + '''
        # HERMES participates in every non-blocked pipeline run
        asyncio.ensure_future(self.hermes.participate_execution(
            "Pipeline execution", {"input": str(input_data)[:300]}
        ))'''
if old_warden_block in content:
    content = content.replace(old_warden_block, new_warden_block)
    print("Patch 4: Hermes pipeline participation added")

with open(VPS_PATH, "w") as f:
    f.write(content)
print("Orchestrator patched successfully!")
