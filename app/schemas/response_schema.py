from pydantic import BaseModel, RootModel, ValidationError, Field
from typing import List, Literal, Optional

class LLMAction(BaseModel):
    action: Literal["click", "stop"]
    target: Optional[str] = None
    reason: str
    goal: Optional[str] = None

    #Quick summary of the action for use in populating session page context history with context for llm
    def summarized(self):
        return {
            "action": self.action,
            "target": self.target,
        }
        
    def __str__(self) -> str:
        return str({
            "action": self.action,
            "target": self.target,
            "reason": self.reason,
            "goal": self.goal
        })

class LLMResponse(BaseModel):
    summary: str
    actions: List[LLMAction] 
    
    def __str__(self) -> str:
        return str({
            "summary": self.summary,
            "actions": [str(action) for action in self.actions]
        })
