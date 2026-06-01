import asyncio
import json
import traceback

async def main():
    try:
        from kernel.orchestrator import Orchestrator
        input_data = {
            "project_path": "c:\\Users\\User\\.gemini\\antigravity-ide\\scratch\\Site-Portal-Maiti",
            "task": "Revisar o site completo, todo o código do portal, fazer diagnóstico, sugestão de melhorias, auditoria e debug."
        }
        orch = Orchestrator(input_data)
        print("Orchestrator loaded successfully.")
        res = await orch.run_with_concierge()
        print("Result:", json.dumps(res, indent=2))
    except Exception as e:
        print("Error encountered:")
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
