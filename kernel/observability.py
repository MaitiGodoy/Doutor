import os
import time
import json
from typing import Dict, Any, Optional, Callable
from functools import wraps

# Try to import Langfuse, but don't break if not available
try:
    from langfuse import Langfuse
    LANGFUSE_AVAILABLE = True
except ImportError:
    LANGFUSE_AVAILABLE = False

class ObservabilityManager:
    def __init__(self):
        self.langfuse = None
        self.enabled = False
        self._init_langfuse()

    def _init_langfuse(self):
        host = os.getenv("LANGFUSE_HOST", "http://localhost:3000")
        public_key = os.getenv("LANGFUSE_PUBLIC_KEY")
        secret_key = os.getenv("LANGFUSE_SECRET_KEY")
        
        if LANGFUSE_AVAILABLE and public_key and secret_key:
            try:
                self.langfuse = Langfuse(
                    host=host,
                    public_key=public_key,
                    secret_key=secret_key
                )
                self.enabled = True
            except Exception as e:
                print(f"[Observability] Langfuse initialization failed: {e}")
                self.enabled = False
        else:
            print("[Observability] Langfuse not configured or unavailable. Running in fallback mode.")

    def trace_llm_call(self, agent_name: str, phase: str):
        """
        Decorator to trace LLM calls.
        Usage: @observability.trace_llm_call("agent_name", "phase")
        """
        def decorator(func: Callable):
            @wraps(func)
            async def wrapper(*args, **kwargs):
                start_time = time.time()
                # Extract prompt from args/kwargs - assuming first arg is prompt or there's a 'prompt' kwarg
                prompt = ""
                if args:
                    prompt = str(args[0])
                elif 'prompt' in kwargs:
                    prompt = kwargs['prompt']
                
                # Execute the function
                result = await func(*args, **kwargs)
                
                end_time = time.time()
                latency = (end_time - start_time) * 1000  # ms
                
                # Extract response content
                response_content = ""
                if result and isinstance(result, dict):
                    response_content = result.get("response", {}).get("content", "")
                
                # Estimate tokens (rough approximation)
                tokens_estimated = len(prompt.split()) + len(response_content.split())
                
                # Trace to Langfuse if enabled
                if self.enabled and self.langfuse:
                    try:
                        self.langfuse.trace(
                            name=f"{agent_name}_{phase}",
                            input=prompt,
                            output=response_content,
                            metadata={
                                "agent": agent_name,
                                "phase": phase,
                                "latency_ms": latency,
                                "tokens_estimated": tokens_estimated
                            }
                        )
                    except Exception as e:
                        print(f"[Observability] Failed to trace to Langfuse: {e}")
                
                # In a real system, we would also push to Prometheus metrics here
                # For now, we just print if debugging
                # print(f"[Observability] Traced {agent_name}@{phase}: {tokens_estimated} tokens, {latency:.2f}ms")
                
                return result
            return wrapper
        return decorator

    def pipeline_event(self, event_type: str, run_id: str, phase: str = None, **kwargs):
        """
        Log pipeline-level events.
        """
        if self.enabled and self.langfuse:
            try:
                self.langfuse.trace(
                    name=f"pipeline_{event_type}",
                    input={"event_type": event_type, "run_id": run_id, "phase": phase},
                    metadata=kwargs
                )
            except Exception as e:
                print(f"[Observability] Failed to log pipeline event: {e}")

# Global instance
observability = ObservabilityManager()

# Convenience decorator
def trace_llm_call(agent_name: str, phase: str):
    return observability.trace_llm_call(agent_name, phase)