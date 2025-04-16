from pydantic import BaseModel, HttpUrl
from typing import Optional, List
from app.schemas.response_schema import LLMAction
from app.schemas.error_schema import WebScraperError

class CrawlRequest(BaseModel):
    start_url: HttpUrl
    user_instruction: str
    max_depth: Optional[int] = 3


class PageDetailsPublic(BaseModel):
    url: str 
    title: str
    body_text: str

class PageActionPublic(BaseModel):
    url: str
    action_key: str

class PageContextPublic(BaseModel):
    depth: int
    details: PageDetailsPublic
    prev_page_action: Optional[PageActionPublic] = None
    summary: str
    actions: List[LLMAction]
    visited_keys: List[str]  # convert from set

class CrawlResponse(BaseModel):
    success: bool = True
    history: List[PageContextPublic]
    errors: Optional[List[WebScraperError]] = None
    message: Optional[str] = None
