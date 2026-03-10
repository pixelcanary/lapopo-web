from fastapi import APIRouter, HTTPException, Depends, Request
from database import db
from models import UserRegister, UserLogin, ChangePassword, ForgotPassword, ResetPassword
from auth import create_token, pwd_context, get_current_user
from helpers import send_recovery_email
from datetime import datetime, timezone, timedelta
import uuid
import secrets

router = APIRouter(prefix="/api")


@router.post("/auth/register")
async def register(data: UserRegister):
    if await db.users.find_one({"email": data.email}):
        raise HTTPException(400, "Email ya registrado")
    uid = str(uuid.uuid4())
    doc = {
        "id": uid,
        "name": data.name,
        "email": data.email,
        "password_hash": pwd_context.hash(data.password),
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    await db.users.insert_one(doc)
    token = create_token(uid, data.name, data.email, False)
    return {"token": token, "user": {"id": uid, "name": data.name, "email": data.email, "is_admin": False}}


@router.post("/auth/login")
async def login(data: UserLogin):
    user = await db.users.find_one({"email": data.email}, {"_id": 0})
    if not user or not pwd_context.verify(data.password, user["password_hash"]):
        raise HTTPException(401, "Credenciales incorrectas")
    is_admin = user.get("is_admin", False)
    token = create_token(user["id"], user["name"], user["email"], is_admin)
    return {"token": token, "user": {"id": user["id"], "name": user["name"], "email": user["email"], "is_admin": is_admin}}


@router.put("/auth/cambiar-password")
async def change_password(data: ChangePassword, user=Depends(get_current_user)):
    if len(data.new_password) < 8:
        raise HTTPException(400, "La contrasena debe tener al menos 8 caracteres")
    u = await db.users.find_one({"id": user["user_id"]})
    if not u or not pwd_context.verify(data.current_password, u["password_hash"]):
        raise HTTPException(400, "Contrasena actual incorrecta")
    new_hash = pwd_context.hash(data.new_password)
    await db.users.update_one({"id": user["user_id"]}, {"$set": {"password_hash": new_hash}})
    return {"message": "Contrasena actualizada correctamente"}


@router.post("/auth/recuperar-password")
async def forgot_password(data: ForgotPassword, request: Request):
    token = secrets.token_urlsafe(32)
    expires = datetime.now(timezone.utc) + timedelta(hours=1)
    u = await db.users.find_one({"email": data.email})
    if u:
        await db.password_resets.insert_one({"email": data.email, "token": token, "expires_at": expires.isoformat(), "used": False})
        frontend_url = request.headers.get("origin", request.headers.get("referer", "https://lapopo.es")).rstrip("/")
        await send_recovery_email(data.email, token, frontend_url)
    return {"message": "Si ese email esta registrado, recibiras un enlace de recuperacion"}


@router.post("/auth/resetear-password")
async def reset_password(data: ResetPassword):
    if len(data.new_password) < 8:
        raise HTTPException(400, "La contrasena debe tener al menos 8 caracteres")
    reset = await db.password_resets.find_one({"token": data.token, "used": False})
    if not reset:
        raise HTTPException(400, "Enlace invalido o expirado")
    if datetime.fromisoformat(reset["expires_at"]) < datetime.now(timezone.utc):
        raise HTTPException(400, "El enlace ha expirado")
    u = await db.users.find_one({"email": reset["email"]})
    if not u:
        raise HTTPException(400, "Usuario no encontrado")
    new_hash = pwd_context.hash(data.new_password)
    await db.users.update_one({"id": u["id"]}, {"$set": {"password_hash": new_hash}})
    await db.password_resets.update_one({"token": data.token}, {"$set": {"used": True}})
    return {"message": "Contrasena restablecida correctamente"}
