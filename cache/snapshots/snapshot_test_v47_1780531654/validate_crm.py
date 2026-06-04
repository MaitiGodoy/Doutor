import asyncio
import json
from kernel.lateral_agent import LateralAgent

async def main():
    agent = LateralAgent()
    target_path = r"C:\Users\User\g5x-agent-system"
    result = await agent.run_defensive_validation(target_path, "comprehensive")
    print(json.dumps(result, indent=2, ensure_ascii=False))

if __name__ == "__main__":
    asyncio.run(main())
