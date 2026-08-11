from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routes.auth_routes import router as auth_router
from routes.repository_routes import router as repository_router
from routes.chat_routes import router as chat_router

app = FastAPI(
    title="IntelliRepo API",
    description="AI-powered GitHub repository analysis platform",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router, prefix="/api")
app.include_router(repository_router, prefix="/api")
app.include_router(chat_router, prefix="/api")


@app.get("/")
async def root():
    return {"message": "IntelliRepo API is running", "docs": "/docs"}


@app.get("/health")
async def health():
    return {"status": "healthy"}
