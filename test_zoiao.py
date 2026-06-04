import os
import json
import asyncio
from agents.zoiao_agent import ZoiaoAgent
from kernel.provider_router import ProviderRouter

# Set the environment variable to allow the browser agent
os.environ["ALLOW_BROWSER_AGENT"] = "true"

# Create a mock router (we don't have a real one, but the Zoiao agent doesn't use the router in its execution)
class MockRouter:
    pass

router = MockRouter()

# Load the Zoiao agent configuration from the JSON file
with open("agents/roles/zoiao.json", "r", encoding="utf-8-sig") as f:
    config = json.load(f)

# Create the Zoiao agent
agent = ZoiaoAgent(config, router)

# Define a test objective
objective = "Navigate to https://example.com and extract the title of the page."

# Run the agent
async def test():
    result = await agent.execute_browser_task(objective)
    print(json.dumps(result, indent=2, ensure_ascii=False))

asyncio.run(test())
