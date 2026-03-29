from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .api import disasters, prediction

# Create FastAPI app
app = FastAPI(
    title="Florida Disaster Risk API",
    description="AI-powered disaster risk prediction for Florida",
    version="1.0.0"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(disasters.router, prefix="/api/disasters", tags=["disasters"])
app.include_router(prediction.router, prefix="/api/prediction", tags=["prediction"])

@app.get("/")
def root():
    return {"message": "Florida Disaster Risk API", "status": "running"}

@app.get("/health")
def health_check():
    return {"status": "healthy"}
