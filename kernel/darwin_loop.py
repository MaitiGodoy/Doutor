import asyncio
import random
import logging

logger = logging.getLogger("doutor.darwin_loop")

async def start_darwin_background(orchestrator):
    while True:
        try:
            await asyncio.sleep(300)
        except asyncio.CancelledError:
            break
        if random.random() < 0.05:
            logger.info("[Darwin] Ciclo de mutação acionado (5% chance)...")
            darwin = orchestrator.agents.get("the_darwin")
            if darwin and hasattr(darwin, "mutate_prompt"):
                try:
                    result = await darwin.mutate_prompt(orchestrator.state_mgr.get_run_history(limit=5))
                    if result.get("new_prompt_section"):
                        logger.info(f"[Darwin] Mutação gerada: {result['new_prompt_section'][:80]}...")
                except Exception as e:
                    logger.warning(f"[Darwin] Falha silenciosa: {e}")
