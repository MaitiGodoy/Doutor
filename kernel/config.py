import os
from pathlib import Path
from dotenv import load_dotenv

_env_path = Path(__file__).parent.parent / '.env'
load_dotenv(dotenv_path=_env_path)

# API Keys
OPENROUTER_KEY = os.getenv("OPENROUTER_API_KEY")
GROQ_KEY = os.getenv("GROQ_API_KEY")
HF_KEY = os.getenv("HUGGINGFACE_API_KEY")

# Twilio & Notifications
TWILIO_SID = os.getenv("TWILIO_SID")
TWILIO_TOKEN = os.getenv("TWILIO_TOKEN")
TWILIO_WHATSAPP_FROM = os.getenv("TWILIO_WHATSAPP_FROM", "+14155238886")
USER_PHONE = os.getenv("USER_PHONE")

# Provider URLs
PROVIDERS = {
    "openrouter": {"base": "https://openrouter.ai/api/v1", "headers": {"Authorization": f"Bearer {OPENROUTER_KEY}"}},
    "groq": {"base": "https://api.groq.com/openai/v1", "headers": {"Authorization": f"Bearer {GROQ_KEY}"}},
    "huggingface": {"base": "https://api-inference.huggingface.co/v1", "headers": {"Authorization": f"Bearer {HF_KEY}"}}
}

# Model Mapping (Free Tier Optimized)
MODELS = {
    "programming": {
        "planner_a": "meta-llama/llama-3.1-8b-instruct",
        "planner_b": "google/gemma-2-9b-it",
        "coder": "qwen/qwen-2.5-coder-7b-instruct",
        "auditor": "deepseek/deepseek-coder-v2-lite-instruct",
        "reviewer_e": "microsoft/phi-3.5-mini-instruct",
        "reviewer_f": "mistralai/mistral-7b-instruct",
        "tester": "qwen/qwen-2.5-coder-3b-instruct",
    },
    "marketing": {
        "planner_a": "meta-llama/llama-3.1-8b-instruct",
        "planner_b": "google/gemma-2-9b-it",
        "creator": "qwen/qwen-2.5-7b-instruct",
        "auditor": "deepseek/deepseek-coder-v2-lite-instruct",
        "reviewer_e": "microsoft/phi-3.5-mini-instruct",
        "reviewer_f": "mistralai/mistral-7b-instruct",
        "optimizer": "qwen/qwen-2.5-coder-3b-instruct",
    },
    "infoproduct": {
        "strategist_a": "meta-llama/llama-3.1-8b-instruct",
        "strategist_b": "google/gemma-2-9b-it",
        "producer": "qwen/qwen-2.5-7b-instruct",
        "auditor": "deepseek/deepseek-coder-v2-lite-instruct",
        "reviewer_e": "microsoft/phi-3.5-mini-instruct",
        "reviewer_f": "mistralai/mistral-7b-instruct",
        "optimizer": "qwen/qwen-2.5-coder-3b-instruct",
    }
}

# Temperatures & Max Tokens
TEMPERATURES = {
    "planner_a": 0.6, "planner_b": 0.7, "coder": 0.2, "auditor": 0.3,
    "reviewer_e": 0.5, "reviewer_f": 0.5, "tester": 0.4, "creator": 0.2,
    "optimizer": 0.4, "strategist_a": 0.6, "strategist_b": 0.7, "producer": 0.2
}
MAX_TOKENS = {
    "planner_a": 2048, "planner_b": 2048, "coder": 4096, "auditor": 2048,
    "reviewer_e": 2048, "reviewer_f": 2048, "tester": 1536, "creator": 4096,
    "optimizer": 1536, "strategist_a": 2048, "strategist_b": 2048, "producer": 4096
}

# Financial Guardrails (Hardcoded)
FINANCIAL_GUARD = {
    "daily_spend_limit": 0.0,
    "unlock_ads_after_revenue": 100.0,
    "reinvest_pct": 30,
    "auto_pause_roas": 1.5,
    "max_refund_rate": 10.0,
    "human_override_threshold": 500.0,
    "dry_run_required": True
}

# Optimization Flags
OPTIMIZATION = {
    "diff_only_mode": True,
    "json_compression": True,
    "stop_sequences": ["}\n", "```", "FIM", "</json>"],
    "context_trimming_pct": 0.8,
    "parallel_dispatch": True,
    "blind_review": True,
    "atomic_blocks": True,
    "max_retries": 3
}
