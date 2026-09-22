
from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from app.database import get_session
from app.dependencies import require_roles
from app.dtos.requests import ActiveUpdateRequest, RoleUpdateRequest
from app.dtos.responses import UserResponse
from app.enums import Role
from app.models import User

router = APIRouter(prefix="/users", tags=["users"])

admin_only = require_roles([Role.admin])


def get_user_or_404(session, user_id):
    user = session.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@router.get("", response_model=list[UserResponse])
def list_users(
    role: Role | None = None,
    session: Session = Depends(get_session),
    current_user: User = Depends(admin_only),
):
    query = select(User)
    if role is not None:
        query = query.where(User.role == role)
    return session.exec(query).all()


@router.patch("/{user_id}/role", response_model=UserResponse)
def change_role(
    user_id: int,
    update: RoleUpdateRequest,
    session: Session = Depends(get_session),
    current_user: User = Depends(admin_only),
):
    user = get_user_or_404(session, user_id)
    if user.id == current_user.id:
        raise HTTPException(status_code=400, detail="You cannot change your own role")
    user.role = update.role
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


@router.patch("/{user_id}/active", response_model=UserResponse)
def set_active(
    user_id: int,
    update: ActiveUpdateRequest,
    session: Session = Depends(get_session),
    current_user: User = Depends(admin_only),
):
    user = get_user_or_404(session, user_id)
    if user.id == current_user.id:
        raise HTTPException(status_code=400, detail="You cannot disable your own account")
    user.is_active = update.is_active
    session.add(user)
    session.commit()
    session.refresh(user)
    return user