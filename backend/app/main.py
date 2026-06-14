from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.database import init_db
from app.api import health, settings, jobs

# Initialize FastAPI application
app = FastAPI(
    title="Repo Blueprint Studio API",
    description="Backend API for managing GitHub repository specifications and rebuilding blueprints",
    version="1.0.0"
)

# CORS Policy configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Suitable for local development
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize Database on app startup
@app.on_event("startup")
def startup_db():
    init_db()

# Mount API Routers
app.include_router(health.router, prefix="/api", tags=["Health"])
app.include_router(settings.router, prefix="/api", tags=["Settings"])
app.include_router(jobs.router, prefix="/api", tags=["Jobs"])

@app.get("/")
def read_root():
    return {"message": "Welcome to Repo Blueprint Studio API. Go to /docs for Swagger docs."}
