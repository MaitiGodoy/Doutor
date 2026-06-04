import collections
import logging

logger = logging.getLogger("doutor.context_lru")

class ContextLRU:
    def __init__(self, maxsize: int = 50):
        self.cache = collections.OrderedDict()
        self.maxsize = maxsize

    def get(self, key: str):
        if key in self.cache:
            self.cache.move_to_end(key)
            return self.cache[key]
        return None

    def put(self, key: str, value):
        if key in self.cache:
            self.cache.move_to_end(key)
        self.cache[key] = value
        if len(self.cache) > self.maxsize:
            self.cache.popitem(last=False)

    def compress_if_needed(self, threshold_tokens: int = 3000):
        total_tokens = sum(len(str(v)) for v in self.cache.values()) // 4
        if total_tokens > threshold_tokens:
            keys_to_drop = list(self.cache.keys())[:len(self.cache) // 2]
            for k in keys_to_drop:
                del self.cache[k]
            logger.info(f"ContextLRU compressed: dropped {len(keys_to_drop)} keys ({total_tokens} -> {sum(len(str(v)) for v in self.cache.values()) // 4} tokens)")
            return {"status": "compressed", "dropped": keys_to_drop}
        return {"status": "ok", "estimated_tokens": total_tokens}
