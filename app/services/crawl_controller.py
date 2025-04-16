from scrapy import Spider, Request
from scrapy.utils.reactor import install_reactor
from urllib.parse import urljoin
from app.services.llm import ask_llm
from pprint import pprint
import json
import re
from typing import List, Tuple, Optional
from pydantic import BaseModel, ValidationError
from app.config.strigil_config import config
from app.schemas.context_schema import Interactable, PageDetails, PageContext, PageAction, CrawlSession
from playwright.async_api import Page
from app.schemas.response_schema import LLMResponse, LLMAction
from app.schemas.error_schema import ValidationError as SchemaValidationError
import traceback

class CrawlController:
    def __init__(self, session: CrawlSession):
        self.session = session

    async def handle_page(self, url: str, depth: int, page:Page, prev_page_action: Optional[PageAction]) -> List[Request]:
        if url in self.session.visited_urls or depth > self.session.max_depth:
            return []
        self.session.visited_urls.add(url)

        details = await extract_details(page)
        print("Parsing page: ",details, prev_page_action)
        llm_response = await self.spider._ask_llm(details, self.session.user_instruction, prev_page_action)
        print("LLM response:")
        pprint(not llm_response)
        if not llm_response:
            return []

        context = PageContext(
            depth = depth,
            details = details,
            prev_page_action = prev_page_action,
            summary = llm_response.summary,
            actions = llm_response.actions,
            visited_keys =  set()
        )
        print("page context:",context)
        self.session.history.append(context)

        next_requests = []
        for action in llm_response.actions:
            if action.action == "click":
                match = next((el for el in details.interactables if el.key == action.target), None)
                if match and match.href and match.key not in context.visited_keys:
                    next_url = urljoin(url, match.href)
                    context.visited_keys.add(match.key)
                    next_requests.append(Request(
                        next_url,
                        meta={
                            "playwright": True,
                            "playwright_include_page": True,
                            "playwright_page_methods": [
                                {"method": "wait_for_load_state", "args": ["networkidle"]}
                            ],
                            "download_timeout": 20,
                            "depth": depth + 1,
                            "prev_url": url,
                            "prev_action_key": action.target,
                        },
                        callback=self.spider.parse
                    ))
            elif action.action == "stop":
                break

        return next_requests


async def extract_details(page):
    title = await page.title()
    body_text = await page.inner_text("body")
    elements = []
    seen = {}
    for role in ["link", "button"]:
        locators = await page.get_by_role(role).all()
        # print("Locators:", role, ", ", locators)
        for el in locators:
            try:
                text = (await el.inner_text()).strip()
                if not text:
                    continue
                key = text if text not in seen else f"{text} ({seen[text]})"
                seen[text] = seen.get(text, 0) + 1
                href = await el.get_attribute("href")
                tag = await el.evaluate("el => el.tagName.toLowerCase()")
                elements.append(Interactable(tag,text,href,key))
            except:
                continue
    return PageDetails(
        page.url,
        title,
        body_text,
        elements
    )

def extract_json_from_response(response_text: str) -> Tuple[Optional[LLMResponse], Optional[SchemaValidationError]]:
    """
    Extract and validate JSON from the LLM response text.
    
    Args:
        response_text: The text response from the LLM
        
    Returns:
        Tuple containing:
        - The parsed and validated LLMResponse object (or None if there was an error)
        - A validation error object (or None if there was no error)
    """
    try:
        print("DEBUG: Extracting JSON from response...")
        
        # Try to find JSON in code blocks first - more permissive pattern
        match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", response_text, re.DOTALL)
        if match:
            json_str = match.group(1).strip()
            print(f"DEBUG: Found JSON in code block: {json_str[:100]}...")
        else:
            # If no code block, try to find a JSON object anywhere in the response
            print("DEBUG: No code block found, trying to extract JSON directly")
            # Try to find a JSON object or array in the text
            match = re.search(r"(\{[\s\S]*\}|\[[\s\S]*\])", response_text, re.DOTALL)
            if match:
                json_str = match.group(1).strip()
                print(f"DEBUG: Found raw JSON: {json_str[:100]}...")
            else:
                # If no JSON structure is found, use the entire response as a last resort
                json_str = response_text.strip()
                print(f"DEBUG: Using entire response as JSON: {json_str[:100]}...")
            
        try:
            # Try to parse the JSON
            print("DEBUG: Parsing JSON...")
            parsed = json.loads(json_str)
            print(f"DEBUG: Successfully parsed JSON: {parsed}")
            
            # Try to validate against the LLMResponse model
            print("DEBUG: Validating against LLMResponse model...")
            validated = LLMResponse.model_validate(parsed)
            print(f"DEBUG: Successfully validated LLMResponse: {validated}")
            return validated, None
            
        except json.JSONDecodeError as e:
            print(f"DEBUG: JSON decode error: {str(e)}")
            error = SchemaValidationError(
                error_type="json_decode_error",
                message=f"Failed to parse JSON: {str(e)}",
                details={
                    "json_str": json_str,
                    "error_position": e.pos,
                    "error_message": e.msg
                }
            )
            return None, error
            
        except SchemaValidationError as e:
            print(f"DEBUG: Schema validation error: {str(e)}")
            error = SchemaValidationError(
                error_type="schema_validation_error",
                message=f"Failed to validate JSON against LLMResponse schema: {str(e)}",
                details={"parsed_json": parsed, "error": str(e)}
            )
            return None, error
            
    except Exception as e:
        print(f"DEBUG: Unexpected error in JSON extraction: {str(e)}")
        error = SchemaValidationError(
            error_type="extraction_error",
            message=f"Error extracting JSON from response: {str(e)}",
            details={"response": response_text, "traceback": traceback.format_exc()}
        )
        return None, error
