"""FastAPI application for promptdesign."""

from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, Request

# Load environment variables from .env file
load_dotenv()
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles

from backend.routes import analysis, prompts

app = FastAPI(
    title="PromptDesign",
    description="API for evaluating prompts and suggesting improvements",
    version="0.1.0",
)

# Configure CORS for local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],  # Vite default
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(prompts.router, prefix="/api/prompts", tags=["prompts"])
app.include_router(analysis.router, prefix="/api/analysis", tags=["analysis"])


@app.get("/api/health")
async def health_check() -> dict[str, str]:
    """Health check endpoint."""
    return {"status": "healthy"}


# Static file serving for production
FRONTEND_DIR = Path(__file__).parent.parent / "frontend"
DIST_DIR = FRONTEND_DIR / "dist"

# Check if frontend is built
if DIST_DIR.exists():
    # Serve static assets
    app.mount("/assets", StaticFiles(directory=DIST_DIR / "assets"), name="assets")

    @app.get("/favicon.ico")
    async def favicon():
        favicon_path = DIST_DIR / "favicon.ico"
        if favicon_path.exists():
            return FileResponse(favicon_path)
        # Fallback to vite.svg
        svg_path = DIST_DIR / "vite.svg"
        if svg_path.exists():
            return FileResponse(svg_path, media_type="image/svg+xml")
        return HTMLResponse(status_code=204)

    @app.get("/{full_path:path}")
    async def serve_spa(request: Request, full_path: str):
        """Serve the SPA for all non-API routes."""
        # Don't intercept API routes
        if full_path.startswith("api/"):
            return HTMLResponse(status_code=404)

        # Try to serve static file first
        file_path = DIST_DIR / full_path
        if file_path.is_file():
            return FileResponse(file_path)

        # Fallback to index.html for SPA routing
        index_path = DIST_DIR / "index.html"
        if index_path.exists():
            return FileResponse(index_path)

        return HTMLResponse(
            content="<h1>Frontend not built</h1><p>Run: cd frontend && npm run build</p>",
            status_code=200,
        )
else:
    @app.get("/")
    async def root():
        """Show instructions when frontend is not built."""
        return HTMLResponse(
            content="""
            <html>
            <head><title>PromptDesign</title></head>
            <body style="font-family: system-ui; max-width: 600px; margin: 50px auto; padding: 20px;">
                <h1>PromptDesign API</h1>
                <p>The frontend is not built yet.</p>
                <h3>Option 1: Build the frontend</h3>
                <pre style="background: #f5f5f5; padding: 15px; border-radius: 8px;">cd frontend
npm install
npm run build</pre>
                <p>Then restart the server.</p>
                <h3>Option 2: Development mode</h3>
                <p>Run the frontend dev server separately:</p>
                <pre style="background: #f5f5f5; padding: 15px; border-radius: 8px;">cd frontend && npm run dev</pre>
                <p>Then open <a href="http://localhost:5173">http://localhost:5173</a></p>
                <hr>
                <p>API is available at <a href="/api/health">/api/health</a></p>
            </body>
            </html>
            """,
            status_code=200,
        )
