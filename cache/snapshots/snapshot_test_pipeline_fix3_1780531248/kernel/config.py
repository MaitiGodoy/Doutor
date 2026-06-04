import os
from pathlib import Path
from dotenv import load_dotenv

_env_path = Path(__file__).parent.parent / '.env'
load_dotenv(dotenv_path=_env_path)

# API Keys
OPENROUTER_KEY = os.getenv("OPENROUTER_API_KEY")
GROQ_KEY = os.getenv("GROQ_API_KEY")
HF_KEY = os.getenv("HUGGINGFACE_API_KEY")
FIREWORKS_KEY = os.getenv("FIREWORKS_API_KEY")
TOGETHER_KEY = os.getenv("TOGETHER_API_KEY")

# Twilio & Notifications
TWILIO_SID = os.getenv("TWILIO_SID")
TWILIO_TOKEN = os.getenv("TWILIO_TOKEN")
TWILIO_WHATSAPP_FROM = os.getenv("TWILIO_WHATSAPP_FROM", "+14155238886")
USER_PHONE = os.getenv("USER_PHONE")

# Webhook Secret
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET", "change-me-in-production")

# Provider URLs
PROVIDERS = {
    "openrouter": {"base": "https://openrouter.ai/api/v1", "headers": {"Authorization": f"Bearer {OPENROUTER_KEY}"}},
    "groq": {"base": "https://api.groq.com/openai/v1", "headers": {"Authorization": f"Bearer {GROQ_KEY}"}},
    "huggingface": {"base": "https://api-inference.huggingface.co/v1", "headers": {"Authorization": f"Bearer {HF_KEY}"}},
}

# Temperatures & Max Tokens (agent role names)
TEMPERATURES = {
    "the_scout": 0.4, "the_polymath": 0.7, "the_architect": 0.6,
    "the_director": 0.3, "the_constitution": 0.2,
    "the_wordsmiths": 0.8, "the_voice": 0.7, "the_producer": 0.3,
    "the_surgeon": 0.1, "the_inspector": 0.3, "the_scaler": 0.4,
    "the_empath": 0.6, "the_ranker": 0.3, "the_lateral": 0.75,
    "the_concierge": 0.5, "the_master_key": 0.1,
    "the_zoiao": 0.1, "the_omni_aa": 0.1,
    "the_minimalist": 0.3, "the_darwin": 0.7, "the_gossip": 0.9,
    "the_chronic": 0.95, "the_inner_spark": 0.3,
    "halbert": 0.9, "ogilvy": 0.7, "kennedy": 0.8,
    "the_senior_dev": 0.2,
    "the_prompt_architect": 0.3,
    "the_planner_alpha": 0.1,
    "the_planner_beta": 0.1,
    "the_senior_dev_core": 0.1,
    "the_senior_dev_ui": 0.1,
    "the_senior_dev_ops": 0.1,
}
MAX_TOKENS = {
    "the_scout": 2048, "the_polymath": 3072, "the_architect": 3072,
    "the_director": 2048, "the_constitution": 2048,
    "the_wordsmiths": 4096, "the_voice": 3072, "the_producer": 4096,
    "the_surgeon": 2048, "the_inspector": 3072, "the_scaler": 3072,
    "the_empath": 3072, "the_ranker": 2048, "the_lateral": 4096,
    "the_concierge": 2048, "the_master_key": 1024,
    "the_zoiao": 2048, "the_omni_aa": 3000,
    "the_minimalist": 1024, "the_darwin": 2048, "the_gossip": 4096,
    "the_chronic": 2048, "the_inner_spark": 1024,
    "halbert": 3072, "ogilvy": 3072, "kennedy": 3072,
    "the_senior_dev": 4096,
    "the_prompt_architect": 3072,
    "the_planner_alpha": 4096,
    "the_planner_beta": 4096,
    "the_senior_dev_core": 4096,
    "the_senior_dev_ui": 4096,
    "the_senior_dev_ops": 4096,
}

# Financial Guardrails (env-configurable)
FINANCIAL_GUARD = {
    "daily_spend_limit": float(os.getenv("DAILY_SPEND_LIMIT", "5.0")),
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

# Production Hardening Config
PRODUCTION = {
    "max_daily_run_hours": float(os.getenv("MAX_DAILY_RUN_HOURS", "2")),
    "cron_schedule": os.getenv("CRON_SCHEDULE", "0 8 * * *"),
    "webhook_secret": os.getenv("WEBHOOK_SECRET", "change-me"),
    "sandbox_timeout_sec": int(os.getenv("SANDBOX_TIMEOUT_SEC", "60")),
    "sandbox_memory_mb": int(os.getenv("SANDBOX_MEMORY_MB", "256")),
    "snapshot_before_run": os.getenv("SNAPSHOT_BEFORE_RUN", "true").lower() == "true",
    "generate_dashboard": os.getenv("GENERATE_DASHBOARD", "true").lower() == "true",
    "daily_backup_enabled": os.getenv("DAILY_BACKUP_ENABLED", "true").lower() == "true",
    "low_power_fallback_model": os.getenv("LOW_POWER_FALLBACK_MODEL", "microsoft/phi-3.5-mini-instruct"),
}
