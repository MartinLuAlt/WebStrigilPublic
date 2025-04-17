from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from app.schemas.api_schema import CrawlRequest, CrawlResponse
from app.schemas.error_schema import ErrorResponse, WebScraperError
from app.services.crawler import run_crawl
import traceback

app = FastAPI(
    title="WebStrigil API",
    description="API for recursive web scraping with LLM integration",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

@app.post("/crawl", response_model=CrawlResponse)
async def crawl_endpoint(request: CrawlRequest):
    try:
        session, errors = await run_crawl(request.start_url, request.user_instruction, request.max_depth)
        
        # Convert session history to public format
        public_history = []
        for ctx in session.history:
            if hasattr(ctx, 'to_public_context'):
                public_history.append(ctx.to_public_context())
        errors = [*session.errors,*errors]
        
        # Prepare response
        response_data = {
            "success": len(errors) == 0,
            "history": [ctx.model_dump() for ctx in public_history],
            "errors": [error.model_dump() for error in errors] if errors else None,
            "message": "Crawl completed successfully" if not errors else "Crawl completed with errors"
        }
        
        return JSONResponse(content=response_data)
        
    except Exception as e:
        # Handle unexpected errors
        error = WebScraperError(
            error_type="unexpected_error",
            message=f"Unexpected error during crawl: {str(e)}",
            details={"error_type": "api_endpoint_error"}
        )
        
        error_response = ErrorResponse(
            success=False,
            errors=[error],
            message="An unexpected error occurred during the crawl"
        )
        
        return JSONResponse(
            status_code=500,
            content=error_response.model_dump()
        )

@app.get("/health")
async def health_check():
    return {"status": "healthy"} 