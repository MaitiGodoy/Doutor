import argparse, json, os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from kernel.observability import ObservabilityDB
from kernel.semantic_memory import SemanticMemory
from kernel.tool_registry import ToolRegistry

def main():
    parser = argparse.ArgumentParser(description="Doutor Ops CLI")
    parser.add_argument("command", choices=["status", "logs", "memory", "tools", "eval"])
    parser.add_argument("--run-id", help="Filter by run ID")
    args = parser.parse_args()

    if args.command == "status":
        print("Doutor v4.6 operational. Modules: Sandbox, MasterKey, Eval, Darwin, Observability, Memory, Tools.")
    elif args.command == "logs":
        obs = ObservabilityDB()
        data = obs.query(run_id=args.run_id)
        print(json.dumps(data[-10:], indent=2))
    elif args.command == "memory":
        mem = SemanticMemory()
        print(json.dumps(mem.retrieve(["code", "plan"]), indent=2))
    elif args.command == "tools":
        reg = ToolRegistry()
        print(json.dumps(reg.registry["tools"], indent=2))
    elif args.command == "eval":
        print("Run `python -c 'from kernel.eval_harness import EvalHarness; print(EvalHarness().validate_output({\"files\":{}, \"tests\":\"\"}, \"code\"))'`")

if __name__ == "__main__":
    main()
