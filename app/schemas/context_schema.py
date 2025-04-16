from pydantic import BaseModel, Field, HttpUrl
from typing import List, Optional, Set, Tuple
from app.schemas.response_schema import LLMAction
from app.schemas.api_schema import PageContextPublic, PageDetailsPublic, PageActionPublic
from app.schemas.error_schema import WebScraperError

class Interactable(BaseModel):
    tag: str
    text: str
    href: Optional[str]
    key: str
    dom_path: Optional[str] = None

    def __init__(self, tag: str, text: str, href: Optional[str], key: str, **kwargs):
        super().__init__(tag=tag, text=text, href=href, key=key, **kwargs)

    def __str__(self):
        return str({"tag": self.tag, 'text': self.text, 'href': self.href, 'key': self.key})

class PageDetails(BaseModel):
    url: HttpUrl
    title: str
    body_text: str
    interactables: List[Interactable]

    def __init__(self, url: str, title: str, body_text: str, interactables: List[Interactable]):
        super().__init__(url=url, title=title, body_text=body_text, interactables=interactables)

    def __str__(self) -> str:
        return str({
            "url": self.url,
            "title": self.title,
            "body_text_length": len(self.body_text),
            "interactables_count": len(self.interactables)
        })
    
    def summarized(self) :
        return {
            "url": str(self.url),
            "title": self.title,
        }

class PageAction(BaseModel):
    url: HttpUrl
    action_key: str
    def __str__(self) -> str:
        return str({
            "url": self.url,
            "action_key": self.action_key,
        })
    
class PageContext(BaseModel):
    depth: int
    details: PageDetails
    prev_page_action: Optional[PageAction] = None
    summary: str
    actions: List[LLMAction]
    visited_keys: Set[str] = Field(exclude = True, default_factory=set)

    def __str__(self) -> str:
        return str({
            "depth": self.depth,
            "details": str(self.details),
            "prev_page_action": str(self.prev_page_action),
            "summary": self.summary,
            "actions": [str(action) for action in self.actions],
            "visited_keys": list(self.visited_keys)
        })
    
    def url(self):
        return self.details.url
    
    def to_public_context(self) -> PageContextPublic:
        # Create the PageActionPublic object if prev_page_action exists
        prev_page_action_public = None
        if self.prev_page_action:
            prev_page_action_public = PageActionPublic(
                url=str(self.prev_page_action.url),
                action_key=self.prev_page_action.action_key
            )
            
        return PageContextPublic(
            depth=self.depth,
            details=PageDetailsPublic(
                url=str(self.details.url),
                title=self.details.title,
                body_text=self.details.body_text,
            ),
            prev_page_action=prev_page_action_public,
            summary=self.summary,
            actions=self.actions,
            visited_keys=list(self.visited_keys),
        )
    def get_action_by_key(self, key: str) -> Optional[LLMAction]:
        try:
            # Use a generator expression (not a list) with next()
            return next(action for action in self.actions if action.target == key)
        except StopIteration:
            # Return None if no matching action is found
            return None
    


class CrawlSession(BaseModel):
    start_urls: List[HttpUrl]
    user_instruction: str
    max_depth: int
    visited_urls: Set[str] = Field(default_factory=set)
    history: List[PageContext] = Field(default_factory=list)
    errors: List[WebScraperError] = Field(default_factory=list)

    def __init__(
        self,
        *,
        start_urls: List[str] = [],
        user_instruction: str = None,
        max_depth: int = None,
        visited_urls: Optional[Set[HttpUrl]] = None,
        history: Optional[List[PageContext]] = None,
        errors: Optional[List[WebScraperError]] = None,
        **kwargs
    ):
        super().__init__(
            start_urls = start_urls,
            user_instruction=user_instruction,
            max_depth=max_depth,
            visited_urls=visited_urls if visited_urls is not None else set(),
            history=history if history is not None else [],
            errors=errors if errors is not None else [],
            **kwargs
        )

    def __str__(self) -> str:
        return str({
            "user_instruction": self.user_instruction,
            "max_depth": self.max_depth,
            "visited_urls_count": len(self.visited_urls),
            "history_count": len(self.history),
            "errors_count": len(self.errors),
            "start_urls": [str(url) for url in self.start_urls]
        })

    def get_page_context_by_url(self, url: HttpUrl) -> Optional[PageContext]:
        try:
            # Use a generator expression (not a list) with next()
            return next(pc for pc in self.history if pc.details.url == url)
        except StopIteration:
            # Return None if no matching page context is found
            return None
    
    def get_by_page_action(self, page_action: PageAction) -> Tuple[Optional[PageContext], Optional[LLMAction]]:
        page_context = self.get_page_context_by_url(page_action.url)
        if page_context == None:
            return None, None
        action = page_context.get_action_by_key(page_action.action_key)
        if action == None: 
            return None, None
        return page_context, action

    def summarize_page_context(self,page_ctx: PageContext):
        summary = {
            "depth": page_ctx.depth,
            "details": page_ctx.details.summarized(),
            "summary": page_ctx.summary,
        }
        if page_ctx.prev_page_action:
            _, action = self.get_by_page_action(page_ctx.prev_page_action)
            summary["previous_url"] =  str(page_ctx.prev_page_action.url)
            summary["previous_action"] = action.summarized()
        return summary
# from pydantic import BaseModel
# from typing import List, Optional, Set
# from response_schema import LLMAction

# # class PageVisit():
# #     url: str
# #     title: Optional[str] = None
# #     clicked_from: Optional[str] = None  # key of the element that led here
# #     user_prompt: Optional[str] = None
# #     summary: Optional[str] = None  # optional LLM-generated summary of the page
# #     chosen_actions: List[str] = []  # list of element keys chosen to interact with on this page

# # class CrawlContext():
# #     depth: int
# #     max_depth: int
# #     history: List[PageVisit]
# #     current_url: str

# class Interactable():
#     tag: str
#     text: str
#     href: Optional[str]
#     key: str
#     dom_path: Optional[str]
#     def __init__(self,tag,text,href,key):
#         self.tag = tag
#         self.text = text
#         self.href = href
#         self.key = key
#     def __str__(self):
#         return str({"tag":self.tag,'text':self.text,'href':self.href,'key':self.key})

# class PageDetails():
#     url: str
#     title: str
#     body_text: str
#     interactables: List[Interactable]
#     def __init__(self, url: str, title: str, body_text: str, interactables: List[Interactable]):
#         self.url = url
#         self.title = title
#         self.body_text = body_text
#         self.interactables = interactables
        
#     def __str__(self) -> str:
#         return str({
#             "url": self.url,
#             "title": self.title,
#             "body_text_length": len(self.body_text),
#             "interactables_count": len(self.interactables)
#         })

# class PageContext():
#     depth: int
#     details: PageDetails
#     summary: str
#     actions: List[LLMAction]
#     visited_keys: Set[str]
#     def __init__(self, depth: int, details: PageDetails, summary: str, actions: List[LLMAction], visited_keys: Set[str]):
#         self.depth = depth
#         self.details = details
#         self.summary = summary
#         self.actions = actions
#         self.visited_keys = visited_keys
        
#     def __str__(self) -> str:
#         return str({
#             "depth": self.depth,
#             "details": str(self.details),
#             "summary": self.summary,
#             "actions": [str(action) for action in self.actions],
#             "visited_keys": list(self.visited_keys)
#         })

# class CrawlSession():
#     user_instruction: str
#     max_depth: int
#     visited_urls: Set[str]
#     history: List[PageContext]
    
#     def __init__(self, *, user_instruction: str = None, max_depth: int = None, visited_urls: Optional[Set[str]] = None, history: Optional[List[PageContext]] = None) -> None:
#         self.user_instruction: str = user_instruction
#         self.max_depth: int = max_depth
#         self.visited_urls: Set[str] = visited_urls if visited_urls is not None else set()
#         self.history: List[PageContext] = history if history is not None else []
    