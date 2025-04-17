from scrapy.crawler import CrawlerRunner
from scrapy.utils.project import get_project_settings
from twisted.internet.asyncioreactor import install as install_reactor
from twisted.internet.defer import Deferred
from app.spiders.llm_spider import LLMPlaywrightSpider  # adjust if needed
from app.schemas.context_schema import CrawlSession
from app.schemas.error_schema import WebScraperError, CrawlError, NetworkError
import asyncio
import traceback
from typing import Tuple, List, Optional

_reactor_installed = False

async def run_crawl(start_url: str, user_instruction: str, max_depth: int = 3) -> Tuple[CrawlSession, List[WebScraperError]]:
    global _reactor_installed
    errors = []
    
    if not _reactor_installed:
        try:
            install_reactor()
        except Exception as e:
            pass
        _reactor_installed = True

    try:
        settings = get_project_settings()
        runner = CrawlerRunner(settings)

        session = CrawlSession(
            start_urls= [start_url],
            user_instruction=user_instruction,
            max_depth=max_depth
        )

        # Define a dynamic subclass of your spider to inject `session`
        class CustomLLMPlaywrightSpider(LLMPlaywrightSpider):
            def __init__(self, *args, **kwargs):
                super().__init__(session,*args, **kwargs)

        # Run it as an asyncio-friendly Twisted call
        future_resp = asyncio.Future()
        deferred = runner.crawl(CustomLLMPlaywrightSpider)
        
        def callback(result):
            print("DEBUG: Crawl complete, Callback hit")
            if isinstance(result, Exception):
                error = WebScraperError(
                    error_type="crawl_error",
                    message=f"Crawl failed: {str(result)}",
                    details={"error_type": "callback_error"}
                )
                errors.append(error)
                asyncio.get_event_loop().call_soon_threadsafe(future_resp.set_exception, result)
            else:
                asyncio.get_event_loop().call_soon_threadsafe(future_resp.set_result, None)
                
        deferred.addBoth(callback)

        await future_resp

    except Exception as e:
        error = WebScraperError(
            error_type="crawl_error",
            message=f"Crawl failed: {str(e)}",
            details={"error_type": "general_crawl_error"}
        )
        errors.append(error)
        
    return session, errors

