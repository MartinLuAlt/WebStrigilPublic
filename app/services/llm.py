import asyncio
import os
from pprint import pprint
from openai import AsyncOpenAI
from playwright.async_api import async_playwright, Playwright
import json
import re
import httpx
import traceback
from typing import Tuple, Optional
from app.schemas.error_schema import WebScraperError, LLMError
from app.schemas.context_schema import CrawlSession, PageDetails, PageAction
from pydantic import HttpUrl

openai_api_key = os.getenv("OPEN_ROUTER_KEY")
client = AsyncOpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=openai_api_key,
    timeout=httpx.Timeout(1.0, connect=1.0),
)

async def ask_llm(session: CrawlSession, system_prompt: str, user_instructions: str, page_details: PageDetails,prev_page_action : Optional[PageAction]= None) -> Tuple[Optional[str], Optional[WebScraperError]]:
    """
    Ask the LLM for guidance on how to interact with a webpage.
    
    Args:
        session: The current crawl session
        system_prompt: The system prompt to guide the LLM's behavior
        user_instructions: The user's instructions for the crawl
        page_details: Details of the current page
        prev_page_action: Optional reference to the previous page action
        
    Returns:
        Tuple containing:
        - The LLM's response text (or None if there was an error)
        - An error object (or None if there was no error)
    """
    page_text = page_details.body_text
    interactables = page_details.interactables

    history_summary = ""
    if prev_page_action is not None:
        try:
            prev_result = session.get_by_page_action(prev_page_action)
            if prev_result[0] is not None and prev_result[1] is not None:
                prev_page_ctx, prev_action = prev_result
                history_summary = f"""
                Here is the history of previous pages you have searched: 
                {[session.summarize_page_context(page_ctx) for page_ctx in session.history if page_ctx.url() != prev_page_ctx.url()]}

                Previous page explored: 
                {session.summarize_page_context(prev_page_ctx)}

                Action taken with a suggested goal for this page:
                {prev_action}
                """
            else:
                print(f"DEBUG: Could not find previous page context or action for {prev_page_action}")
        except Exception as e:
            print(f"DEBUG: Error getting previous page context: {str(e)}")
            # Continue without the history summary rather than failing
    
    message = [
        {
            "role": "system",
            "content": system_prompt
        },
        {
            "role": "user",
            "content": f"""
            The user is requesting assistance in exploring a webpage to fulfill their prompt:
            {user_instructions}

            {history_summary}

            Details of the page:
            {page_details}
            
            Here is the text of the page:
            {page_text[:2000]}

            Here are the interactive elements (links, buttons, inputs):
            {[str(i) for i in interactables]}

            Which ones should we interact with next, and why?
"""
        }
    ]

    print("LLM Request Message:")
    pprint(message)
    
    try:
        print("DEBUG: Sending request to LLM API...")
        # Set timeout directly on the API call
        completion = await asyncio.wait_for(
            client.chat.completions.create(
                model="deepseek/deepseek-chat-v3-0324:free",  # or claude-3-haiku
                messages=message
            ), 
            timeout=1.0  # 1 second timeout for debugging
        )
        print("DEBUG: LLM API response received")
        print("LLM completion:")
        pprint(completion)
        
        # Check if completion and its attributes exist before accessing them
        if completion and hasattr(completion, 'choices') and completion.choices:
            print(f"DEBUG: Found {len(completion.choices)} choices in response")
            if hasattr(completion.choices[0], 'message') and completion.choices[0].message:
                print("DEBUG: Message found in first choice")
                if hasattr(completion.choices[0].message, 'content') and completion.choices[0].message.content is not None:
                    content = completion.choices[0].message.content
                    print(f"DEBUG: Content extracted, length: {len(content)}")
                    print("LLM response content:", content[:100] + "..." if len(content) > 100 else content)
                    return content, None
                else:
                    print("DEBUG: No content found in message")
            else:
                print("DEBUG: No message found in first choice")
        else:
            print("DEBUG: No choices found in completion")
            
        # If we couldn't extract the content, return a fallback message
        print("WARNING: Could not extract response content from API response.")
        print(f"DEBUG: API response structure: {type(completion)}")
       
        error = LLMError(
            error_type="llm_response_error",
            message="Could not extract response content from API response",
            details={"error": "Response parsing error"}
        )
        return None, error
    
    except httpx.TimeoutException as e:
        print(f"ERROR: LLM API request timed out: {str(e)}")
        error = LLMError(
            error_type="llm_timeout_error",
            message="LLM API request timed out",
            details={"error_type": "httpx_timeout"}
        )
        return None, error
        
    except asyncio.TimeoutError:
        print("ERROR: LLM API request timed out (asyncio timeout)")
        error = LLMError(
            error_type="llm_timeout_error",
            message="LLM API request timed out after 1 second",
            details={"error_type": "asyncio_timeout"}
        )
        return None, error
        
    except Exception as e:
        print(f"ERROR: Error calling LLM API: {str(e)}")
        error = LLMError(
            error_type="llm_api_error",
            message="Error calling LLM API",
            details={"error_type": "general_api_error"}
        )
        return None, error