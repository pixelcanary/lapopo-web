from fastapi import FastAPI
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from pathlib import Path
import os
import logging
import cloudinary

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

cloudinary.config(
    cloud_name=os.environ.get("CLOUDINARY_CLOUD_NAME"),
    api_key=os.environ.get("CLOUDINARY_API_KEY"),
    api_secret=os.environ.get("CLOUDINARY_API_SECRET"),
)

from database import client
from seed import seed_data
from routes.auth import router as auth_router
from routes.auctions import router as auctions_router
from routes.users import router as users_router
from routes.social import router as social_router
from routes.ratings import router as ratings_router
from routes.payments import router as payments_router
from routes.disputes import router as disputes_router
from routes.admin import router as admin_router
from routes.upload import router as upload_router
from routes.badges import router as badges_router

app = FastAPI()

app.include_router(auth_router)
app.include_router(auctions_router)
app.include_router(users_router)
app.include_router(social_router)
app.include_router(ratings_router)
app.include_router(payments_router)
app.include_router(disputes_router)
app.include_router(admin_router)
app.include_router(upload_router)
app.include_router(badges_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


@app.on_event("startup")
async def on_startup():
    await seed_data()


@app.on_event("shutdown")
async def shutdown():
    client.close()
