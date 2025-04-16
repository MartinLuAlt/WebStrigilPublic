from typing import Optional, Dict, Any, List
from pydantic import BaseModel

class WebScraperError(BaseModel):
    """Base error model for web scraper errors"""
    error_type: str
    message: str
    details: Optional[Dict[str, Any]] = None

class CrawlError(WebScraperError):
    """Error during the crawling process"""
    pass

class LLMError(WebScraperError):
    """Error during LLM processing"""
    pass

class NetworkError(WebScraperError):
    """Error during network requests"""
    pass

class ParsingError(WebScraperError):
    """Error during parsing of web content"""
    pass

class ValidationError(WebScraperError):
    """Error during validation of data"""
    pass

class ErrorResponse(BaseModel):
    """Response model for error cases"""
    success: bool = False
    errors: List[WebScraperError]
    message: str 