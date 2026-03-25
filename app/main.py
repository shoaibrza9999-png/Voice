import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from dotenv import load_dotenv

# Load env before importing routers/services
load_dotenv()

from app.database import engine, Base
from app.routers import whatsapp
from app.scheduler import setup_scheduler, shutdown_scheduler

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Create DB tables
Base.metadata.create_all(bind=engine)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Starting up application...")
    setup_scheduler()
    yield
    # Shutdown
    logger.info("Shutting down application...")
    shutdown_scheduler()

app = FastAPI(
    title="WhatsApp Finance Tracker Bot API",
    description="Backend for the WhatsApp AI Finance Tracker",
    version="1.0.0",
    lifespan=lifespan
)

app.include_router(whatsapp.router)

@app.get("/")
def read_root():
    return {"message": "Welcome to the WhatsApp Finance Tracker API. Use /docs for Swagger UI."}
