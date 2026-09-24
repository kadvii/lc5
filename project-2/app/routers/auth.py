from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from sqlmodel import Session, select

from app.database import get_session
from app.dependencies import get_current_user
from app.dtos.requests import UserCreateRequest
from app.dtos.responses import TokenResponse, UserResponse
from app.enums import Role
from app.models import User
from app.security import DUMMY_HASH, create_access_token, hash_password, verify_password

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=UserResponse, status_code=201)
def register(new_user: UserCreateRequest, session: Session = Depends(get_session)):
    if session.exec(select(User).where(User.username == new_user.username)).first():
        raise HTTPException(status_code=409, detail="Username is already taken")
    if session.exec(select(User).where(User.email == new_user.email)).first():
        raise HTTPException(status_code=409, detail="Email is already registered")

    user = User(
        username=new_user.username,
        email=new_user.email,
        hashed_password=hash_password(new_user.password),
        role=Role.customer,  # never taken from the request
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


@router.post("/login", response_model=TokenResponse)
def login(
    form: OAuth2PasswordRequestForm = Depends(),
    session: Session = Depends(get_session),
):
    wrong_credentials = HTTPException(
        status_code=401,
        detail="Incorrect username or password",
        headers={"WWW-Authenticate": "Bearer"},
    )

    user = session.exec(select(User).where(User.username == form.username.lower())).first()
    if user is None:
        verify_password(form.password, DUMMY_HASH)  # same work as a real check
        raise wrong_credentials
    if not verify_password(form.password, user.hashed_password):
        raise wrong_credentials
    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account is disabled")

    return TokenResponse(access_token=create_access_token(user.id))


@router.get("/me", response_model=UserResponse)
def read_me(current_user: User = Depends(get_current_user)):
    return current_user
