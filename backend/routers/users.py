from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional
from sqlalchemy.orm import Session
from database import get_db
from models.user import User
from services.auth_service import require_admin, hash_password

router = APIRouter(prefix="/api/users", tags=["users"])


def _user_out(u: User) -> dict:
    return {
        "id": u.id,
        "email": u.email,
        "username": u.username,
        "full_name": u.full_name,
        "role": u.role,
        "is_active": u.is_active,
        "created_at": u.created_at.isoformat() if u.created_at else None,
        "last_login": u.last_login.isoformat() if u.last_login else None,
    }


class CreateUserRequest(BaseModel):
    email: str
    username: str
    full_name: str = ""
    password: str
    role: str = "developer"


class UpdateUserRequest(BaseModel):
    full_name: Optional[str] = None
    role: Optional[str] = None
    is_active: Optional[bool] = None


class ResetPasswordRequest(BaseModel):
    new_password: str


@router.get("")
def list_users(db: Session = Depends(get_db), _: User = Depends(require_admin)):
    return [_user_out(u) for u in db.query(User).order_by(User.created_at).all()]


@router.post("")
def create_user(
    req: CreateUserRequest,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    if db.query(User).filter(User.email == req.email).first():
        raise HTTPException(400, "Email already registered")
    if db.query(User).filter(User.username == req.username).first():
        raise HTTPException(400, "Username already taken")
    if req.role not in ("admin", "developer"):
        raise HTTPException(400, "Role must be 'admin' or 'developer'")
    user = User(
        email=req.email.lower().strip(),
        username=req.username.strip(),
        full_name=req.full_name.strip(),
        hashed_password=hash_password(req.password),
        role=req.role,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return _user_out(user)


@router.put("/{user_id}")
def update_user(
    user_id: str,
    req: UpdateUserRequest,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(404, "User not found")
    if req.role is not None:
        if req.role not in ("admin", "developer"):
            raise HTTPException(400, "Role must be 'admin' or 'developer'")
        user.role = req.role
    if req.is_active is not None:
        if user.id == admin.id and not req.is_active:
            raise HTTPException(400, "Cannot deactivate your own account")
        user.is_active = req.is_active
    if req.full_name is not None:
        user.full_name = req.full_name
    db.commit()
    db.refresh(user)
    return _user_out(user)


@router.post("/{user_id}/reset-password")
def reset_password(
    user_id: str,
    req: ResetPasswordRequest,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(404, "User not found")
    if len(req.new_password) < 6:
        raise HTTPException(400, "Password must be at least 6 characters")
    user.hashed_password = hash_password(req.new_password)
    db.commit()
    return {"status": "password reset"}


@router.delete("/{user_id}")
def delete_user(
    user_id: str,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(404, "User not found")
    if user.id == admin.id:
        raise HTTPException(400, "Cannot delete your own account")
    db.delete(user)
    db.commit()
    return {"status": "deleted"}
