import json
from pydantic import BaseModel, Field
from typing import Dict, Any, Optional

class LLMTimeoutConfig(BaseModel):
    """Timeout configuration for LLM API calls"""
    request_timeout: float = Field(default=30.0, description="Overall timeout for LLM API requests in seconds")
    connect_timeout: float = Field(default=5.0, description="Connection timeout for LLM API in seconds")

class ScrapyTimeoutConfig(BaseModel):
    """Timeout configuration for Scrapy crawler"""
    page_load_timeout: int = Field(default=30, description="Timeout for page loading in seconds")
    download_timeout: int = Field(default=20, description="Timeout for content downloading in seconds")

class PlaywrightTimeoutConfig(BaseModel):
    """Timeout configuration for Playwright browser automation"""
    navigation_timeout: int = Field(default=30000, description="Navigation timeout in milliseconds")

class TimeoutConfig(BaseModel):
    """Container for all timeout configurations"""
    llm: LLMTimeoutConfig = Field(default_factory=LLMTimeoutConfig)
    scrapy: ScrapyTimeoutConfig = Field(default_factory=ScrapyTimeoutConfig)
    playwright: PlaywrightTimeoutConfig = Field(default_factory=PlaywrightTimeoutConfig)

class StrigilConfig(BaseModel):
    """Main configuration for the WebStrigil application"""
    system_prompt: str = Field(
        default="",
        description="System prompt for the LLM to guide web crawling decisions"
    )
    timeouts: TimeoutConfig = Field(default_factory=TimeoutConfig)
    llm_model: str = Field(
        default="deepseek/deepseek-chat-v3-0324:free",
        description="Model used by the crawl guiding LLM"
    )
    
    # Add additional configuration sections as needed
    # For example:
    # crawler_settings: CrawlerSettings = Field(default_factory=CrawlerSettings)
    # api_settings: APISettings = Field(default_factory=APISettings)

def load_config(config_path: str = 'app/config/strigil_config.json') -> StrigilConfig:
    """
    Load configuration from JSON file and validate with Pydantic
    
    Args:
        config_path: Path to the configuration JSON file
        
    Returns:
        Validated StrigilConfig object
    """
    try:
        with open(config_path) as f:
            config_data = json.load(f)
            return StrigilConfig(**config_data)
    except Exception as e:
        print(f"Error loading configuration from {config_path}: {str(e)}")
        # Return default configuration if file can't be loaded
        return StrigilConfig(
            system_prompt="""
            You are a smart web crawling assistant. Based on the page content and available elements, decide which ones are most relevant to the user's instructions.

            Your job is to choose which elements on a webpage to interact with to retrieve more relevant content, based on a user prompt.

            You will be given:
            - A prompt from the user
            - The text of the page
            - A list of DOM elements that can be clicked (links, buttons)
            - Crawling context (depth, history, current goal, etc.)

            First think step by step about which are the most relevant, then return JSON containing:
            1) A short 1 or 2 sentence long summary of the page, for keeping track of history, in the `"summary`" field
            2) A list ofa actions to perform. Each action should include:
            - `"action"`: either `"click"`, or `"stop"`
            - `"target"`: the `key` of the element
            - `"reason"`: a short sentence explaining why
            - `"goal:`: the new goal you would like to achieve after performing the action

            Only include clickable elements that seem promising. If nothing looks useful, return only a single 'stop' action.
            """
        )

# Load the configuration
config = load_config()

