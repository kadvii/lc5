
from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from sqlmodel import Session

from app.database import get_session
from app.models import User
from app.security import read_user_id_from_token

# tokenUrl tells the /docs page where to send the login form.
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


def get_current_user(
    token: str = Depends(oauth2_scheme),
    session: Session = Depends(get_session),
):
    not_authenticated = HTTPException(
        status_code=401,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    user_id = read_user_id_from_token(token)
    if user_id is None:
        raise not_authenticated

    # Look the user up on EVERY request instead of trusting a role written
    # into the token. A demoted or disabled user loses access immediately.
    user = session.get(User, user_id)
    if user is None:
        raise not_authenticated
    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account is disabled")
    return user

    
def require_roles(allowed_roles):
    """Build a dependency that only lets the given roles through."""

    def check_role(current_user: User = Depends(get_current_user)):
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=403, detail="You do not have permission to do this"
            )
        return current_user

    return check_role