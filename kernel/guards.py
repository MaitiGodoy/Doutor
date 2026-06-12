from typing import Dict,Any,List,Optional
import asyncio,re
from enum import Enum
from dataclasses import dataclass

class GuardrailResult(Enum):
    PASS="pass"
    FAIL="fail"

@dataclass
class GuardrailCheck:
    guardrail_name:str
    result:GuardrailResult
    confidence:float
    details:str
    action_taken:Optional[str]=None

class NVIDIA_Guardrails:
    def __init__(self):
        self.violation_log=[]
    
    async def validate_input(self,text:str,ctx:Dict=None)->List[GuardrailCheck]:
        checks=[]
        pii=re.findall(r'[\w.]+@[\w.]+|\d{3}-\d{2}-\d{4}',text)
        checks.append(GuardrailCheck("pii",GuardrailResult.FAIL if pii else GuardrailResult.PASS,0.95 if pii else 1.0,"PII detected"if pii else"OK","blocked"if pii else None))
        
        toxic=len(re.findall(r'\b(hate|kill|stupid|idiot)\b',text.lower()))
        score=toxic/max(1,len(text.split()))
        checks.append(GuardrailCheck("toxic",GuardrailResult.FAIL if score>0.05 else GuardrailResult.PASS,score,f"toxic:{score:.0%}"if score>0.05 else"OK","flagged"if score>0.05 else None))
        
        inj=any(p in text.lower() for p in["ignore previous","system prompt","forget all rules"])
        checks.append(GuardrailCheck("injection",GuardrailResult.FAIL if inj else GuardrailResult.PASS,0.9 if inj else 1.0,"injection"if inj else"OK","blocked"if inj else None))
        
        return checks
    
    def stats(self)->Dict:
        return{"total_violations":len(self.violation_log)}

_g=None
def get_guardrails()->NVIDIA_Guardrails:
    global _g
    if _g is None:
        _g=NVIDIA_Guardrails()
    return _g
