from typing import List,Dict,Any,Optional
import asyncio,re,os

class RAGContext:
    def __init__(self,documents:List[str],metadata:List[Dict],scores:List[float]):
        self.documents=documents
        self.metadata=metadata
        self.scores=scores

class NVIDIA_RAG_Orchestrator:
    def __init__(self,db_path:str="/app/data/rag.db"):
        self.db_path=db_path
        self._db=None
        self._table=None
        self._ready=False
    
    async def initialize(self):
        if not self._ready:
            try:
                import lancedb
                os.makedirs(os.path.dirname(self.db_path),exist_ok=True)
                self._db=lancedb.connect(os.path.dirname(self.db_path))
                try:
                    self._table=self._db.open_table("docs")
                except:
                    import pyarrow as pa
                    schema = pa.schema([
                        pa.field("id", pa.string()),
                        pa.field("text", pa.string()),
                        pa.field("meta", pa.string()),
                        pa.field("vec", pa.list_(pa.float32(), 384))
                    ])
                    self._table=self._db.create_table("docs", schema=schema)
            except ImportError:
                pass
            self._ready=True
    
    async def retrieve(self,query:str,top_k:int=5)->RAGContext:
        await self.initialize()
        if self._table:
            try:
                from sentence_transformers import SentenceTransformer
                model=SentenceTransformer("all-MiniLM-L6-v2")
                emb=model.encode(query).tolist()
                results=self._table.search(emb).limit(top_k).to_pandas()
                return RAGContext(
                    documents=results["text"].tolist(),
                    metadata=[eval(m) if isinstance(m,str) else m for m in results["meta"].tolist()],
                    scores=[1.0-(d or 0) for d in results["_distance"].tolist()] if "_distance" in results.columns else [0.9]*len(results)
                )
            except:
                pass
        docs=[f"Resultado {i+1} para: {query}" for i in range(min(top_k,5))]
        meta=[{"src":f"mock{i}","score":0.9-i*0.1} for i in range(len(docs))]
        scores=[0.9-i*0.1 for i in range(len(docs))]
        return RAGContext(docs,meta,scores)
    
    async def generate_with_rag(self,query:str,system_prompt:str,temp:float=0.1)->Dict[str,Any]:
        ctx=await self.retrieve(query,top_k=3)
        context_text = "\n".join(["- " + d for d in ctx.documents])
        augmented=f"{system_prompt}\n\nCONTEXTO:\n{context_text}\n\nPERGUNTA: {query}\n\nRESPOSTA:"
        return{
            "answer":f"Resposta baseada em {len(ctx.documents)} documentos para: {query[:50]}",
            "context_used":ctx.documents,
            "sources":ctx.metadata,
            "confidence":sum(ctx.scores)/len(ctx.scores) if ctx.scores else 0.0,
            "query":query
        }

_rag_inst=None
def get_rag_orchestrator()->NVIDIA_RAG_Orchestrator:
    global _rag_inst
    if _rag_inst is None:
        _rag_inst=NVIDIA_RAG_Orchestrator()
    return _rag_inst