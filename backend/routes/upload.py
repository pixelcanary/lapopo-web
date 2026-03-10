from fastapi import APIRouter, HTTPException, Depends, UploadFile, File
from database import db
from auth import get_current_user
import cloudinary
import cloudinary.uploader

router = APIRouter(prefix="/api")


@router.post("/upload")
async def upload_image(file: UploadFile = File(...), user=Depends(get_current_user)):
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(400, "Solo se permiten imagenes")
    contents = await file.read()
    if len(contents) > 10 * 1024 * 1024:
        raise HTTPException(400, "Imagen demasiado grande (max 10MB)")
    result = cloudinary.uploader.upload(contents, folder="lapopo", resource_type="image")
    return {"url": result["secure_url"], "public_id": result["public_id"]}


@router.post("/upload/base64")
async def upload_base64(data: dict, user=Depends(get_current_user)):
    img = data.get("image", "")
    if not img:
        raise HTTPException(400, "Imagen requerida")
    result = cloudinary.uploader.upload(img, folder="lapopo", resource_type="image")
    return {"url": result["secure_url"], "public_id": result["public_id"]}
