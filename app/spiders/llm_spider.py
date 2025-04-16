'''LLM Spider'''

import json
import traceback
from scrapy import Spider, Request, signals
from scrapy.utils.reactor import install_reactor
from app.schemas.context_schema import CrawlSession, PageAction
from app.services.llm import ask_llm
from app.config.strigil_config import config
from app.schemas.response_schema import LLMResponse
from app.services.crawl_controller import CrawlController, extract_json_from_response
from app.schemas.error_schema import WebScraperError, NetworkError, LLMError, ParsingError
     
class LLMPlaywrightSpider(Spider):
    name = "llm_playwright"
    custom_settings = {
        "DOWNLOAD_HANDLERS": {
            "http": "scrapy_playwright.handler.ScrapyPlaywrightDownloadHandler",
            "https": "scrapy_playwright.handler.ScrapyPlaywrightDownloadHandler",
        },
        "PLAYWRIGHT_BROWSER_TYPE": "chromium",
        "PLAYWRIGHT_DEFAULT_NAVIGATION_TIMEOUT": 30 * 1000,
    }
    install_reactor("twisted.internet.asyncioreactor.AsyncioSelectorReactor")

    def __init__(self, session: CrawlSession, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.session = session
        print("Constructing llm spider", self.session)
        self.controller = CrawlController(self.session)
        self.controller.spider = self  # backref to yield requests
        self.errors = []

    def start_requests(self):
        print("Starting requests", self.session.start_urls)
        for url in self.session.start_urls:
            print("Requesting fetch:",url)
            yield Request(
                str(url),
                meta={
                    "playwright": True,
                    "playwright_include_page": True, 
                    "playwright_page_methods": [
                        {"method": "wait_for_load_state", "args": ["networkidle"]}
                    ],
                    "download_timeout": 20,
                    "depth": 0,
                    "prev_url": None,
                    "prev_action_key": None,
                },
                callback=self.parse,
                errback=self.errback,
            )

    async def parse(self, response):
        try:
            page = response.meta["playwright_page"]
            url = response.url
            depth = response.meta.get("depth", 0)
            prev_url = response.meta.get("prev_url", None)
            prev_action_key = response.meta.get("prev_action_key", None)
            prev_page_action = None
            if prev_url != None and prev_action_key != None:
                prev_page_action = PageAction(url = prev_url, action_key = prev_action_key)
            next_requests = await self.controller.handle_page(url, depth, page, prev_page_action)
            for req in next_requests:
                yield req
        except Exception as e:
            error = ParsingError(
                error_type="parsing_error",
                message=f"Error parsing page {response.url}: {str(e)}",
                details={"url": response.url, "traceback": traceback.format_exc()}
            )
            self.errors.append(error)
            self.logger.error(f"Error parsing page {response.url}: {str(e)}")

    def errback(self, failure):
        self.logger.error(f"Request failed: {failure.request.url}")
        self.logger.error(f"Failure type: {type(failure)}")
        self.logger.error(repr(failure))

        error = NetworkError(
            error_type="network_error",
            message=f"Request failed: {failure.request.url}",
            details={
                "url": failure.request.url,
                "error": str(failure.value),
                "depth": failure.request.meta.get("depth", -1)
            }
        )
        self.errors.append(error)

    async def _ask_llm(self, details, instruction, prev_page_action) -> LLMResponse | None:
        try:
            system_prompt = config['system_prompt']
            decision_text, error = await ask_llm(self.session, system_prompt, instruction, details, prev_page_action)
            
            # If there was an error from the LLM call, add it to our errors list
            if error:
                print("DEBUG: LLM API error:", error)
                self.errors.append(error)
                return None
                
            if not decision_text:
                error = LLMError(
                    error_type="llm_error",
                    message="LLM returned no response",
                    details={"url": details.url}
                )
                print("DEBUG: LLM returned no response:", error)
                self.errors.append(error)
                return None
            
            print("DEBUG: LLM raw response:", decision_text)
            result, validation_error = extract_json_from_response(decision_text)
            
            # If there was a validation error, add it to our errors list
            if validation_error:
                print("DEBUG: JSON validation error:", validation_error)
                self.errors.append(validation_error)
                return None
                
            if not result:
                error = LLMError(
                    error_type="llm_error",
                    message="Failed to parse LLM response",
                    details={"url": details.url, "response": decision_text}
                )
                print("DEBUG: Failed to parse LLM response:", error)
                self.errors.append(error)
                return None
            
            print("DEBUG: Successfully parsed LLM response:", result)
            return result
        except Exception as e:
            error = LLMError(
                error_type="llm_error",
                message=f"Error in LLM processing: {str(e)}",
                details={"url": details.url, "traceback": traceback.format_exc()}
            )
            print("DEBUG: Unexpected error in LLM processing:", error)
            self.errors.append(error)
            return None
    
    @classmethod
    def from_crawler(cls, crawler, *args, **kwargs):
        spider = super().from_crawler(crawler, *args, **kwargs)
        crawler.signals.connect(spider.spider_closed, signal=signals.spider_closed)
        return spider

    def spider_closed(self, spider):
        # Serialize session history
        # serialized = [page_context.model_dump() for page_context in self.session.history]
        # log = json.dumps(serialized, indent=2)
        # print("Crawl logs:", log)
        # f = open("results.json", "a")
        # f.write(log)
        # print("Saved crawl session history to results.json", f.name)
        # f.close()
        
        # Store errors in the session
        print("DEBUG: Total error count -", len(self.errors))
        self.session.errors = self.errors
