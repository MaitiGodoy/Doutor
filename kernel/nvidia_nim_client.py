"""
NVIDIA NIM Client para Doutor Kernel
Usa API Key NGC/NIM para acessar modelos Nemotron, embeddings, etc.
"""
import os
import requests
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

@dataclass
class NIMResponse:
    content: str
    model: str
    tokens: Dict[str, int]
    latency_ms: float

class NVIDIANIMClient:
    def __init__(self, api_key: Optional[str] = None, base_url: str = "https://integrate.api.nvidia.com/v1"):
        self.api_key = api_key or os.getenv("NVIDIA_API_KEY")
        self.base_url = base_url
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        # Modelos recomendados
        self.MODELS = {
            "chat_ultra": "nvidia/nemotron-3-ultra-550b-a55b",
            "chat_super": "nvidia/nemotron-3-super-120b-a12b",
            "chat_70b": "nvidia/llama-3.1-nemotron-70b-instruct",
            "chat_49b": "nvidia/llama-3.3-nemotron-super-49b-v1",
            "embed_qa": "nvidia/nv-embedqa-e5-v5",
            "embed_code": "nvidia/nv-embedcode-7b-v1",
            "embed_general": "nvidia/nv-embed-v1",
            "safety": "nvidia/llama-3.1-nemoguard-8b-content-safety",
        }

    def chat(self, 
             messages: List[Dict[str, str]], 
             model: str = None,
             temperature: float = 0.1,
             max_tokens: int = 512,
             **kwargs) -> NIMResponse:
        """Chat completion via NIM"""
        import time
        model = model or self.MODELS["chat_ultra"]
        
        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            **kwargs
        }
        
        start = time.time()
        resp = requests.post(f"{self.base_url}/chat/completions", 
                           headers=self.headers, json=payload, timeout=60)
        latency = (time.time() - start) * 1000
        
        if resp.status_code != 200:
            raise RuntimeError(f"NIM API error {resp.status_code}: {resp.text}")
        
        data = resp.json()
        return NIMResponse(
            content=data['choices'][0]['message']['content'],
            model=model,
            tokens=data.get('usage', {}),
            latency_ms=latency
        )

    def embed(self, 
              texts: List[str], 
              model: str = None,
              input_type: str = "query") -> List[List[float]]:
        """Generate embeddings via NIM"""
        model = model or self.MODELS["embed_qa"]
        
        payload = {
            "model": model,
            "input": texts,
            "input_type": input_type
        }
        
        resp = requests.post(f"{self.base_url}/embeddings", 
                           headers=self.headers, json=payload, timeout=30)
        
        if resp.status_code != 200:
            raise RuntimeError(f"NIM Embedding error {resp.status_code}: {resp.text}")
        
        data = resp.json()
        return [item['embedding'] for item in data['data']]

    def list_models(self) -> List[Dict]:
        """List available models"""
        resp = requests.get(f"{self.base_url}/models", headers=self.headers)
        if resp.status_code == 200:
            return resp.json().get('data', [])
        return []


# Singleton
_nim_client = None
def get_nim_client() -> NVIDIANIMClient:
    global _nim_client
    if _nim_client is None:
        _nim_client = NVIDIANIMClient()
    return _nim_client


# Teste rápido
if __name__ == "__main__":
    client = get_nim_client()
    
    # Chat
    result = client.chat([
        {"role": "system", "content": "Responda em português."},
        {"role": "user", "content": "O que é NVIDIA Skills em 1 frase?"}
    ])
    print(f"✅ Chat ({result.latency_ms:.0f}ms): {result.content[:100]}...")
    print(f"Tokens: {result.tokens}")
    
    # Embedding
    embs = client.embed(["NVIDIA Skills framework", "AI development"])
    print(f"✅ Embeddings: {len(embs)} vetores x {len(embs[0])} dims")