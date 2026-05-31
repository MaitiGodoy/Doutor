import json, asyncio, sys
from kernel.orchestrator import Orchestrator

async def main():
    # Example input
    input_data = {
        "type": "infoproduct",
        "niche": "Productivity for Developers",
        "audience": "Remote Engineers 25-40",
        "goal": "Waitlist + Pre-sale",
        "platforms": ["LinkedIn", "Twitter", "Email"],
        "tone": "Technical but accessible",
        "budget_limit": 0,
        "kpis": ["ctr", "conversion_rate"]
    }
    
    if len(sys.argv) > 1:
        with open(sys.argv[1], "r", encoding="utf-8") as f: 
            input_data = json.load(f)
        
    orch = Orchestrator(input_data)
    result = await orch.run_with_concierge()
    print(json.dumps(result, indent=2, ensure_ascii=False))

if __name__ == "__main__":
    asyncio.run(main())
