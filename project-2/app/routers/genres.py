from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, col, select

from app.database import get_session
from app.dependencies import require_roles
from app.dtos.requests import GenreCreateRequest
from app.dtos.responses import GenreResponse
from app.enums import Role
from app.models import Genre, User

router = APIRouter(prefix="/genres", tags=["genres"])

staff_or_admin = require_roles([Role.staff, Role.admin])
admin_only = require_roles([Role.admin])


def get_genre_or_404(session: Session, genre_id: int) -> Genre:
    genre = session.get(Genre, genre_id)
    if genre is None:
        raise HTTPException(status_code=404, detail="Genre not found")
    return genre


@router.get("", response_model=list[GenreResponse])
def list_genres(session: Session = Depends(get_session)):
    return session.exec(select(Genre).order_by(col(Genre.id))).all()


@router.post("", response_model=GenreResponse, status_code=201)
def create_genre(
    new_genre: GenreCreateRequest,
    session: Session = Depends(get_session),
    current_user: User = Depends(staff_or_admin),
):
    existing = session.exec(select(Genre).where(Genre.name == new_genre.name)).first()
    if existing is not None:
        raise HTTPException(status_code=409, detail="Genre already exists")

    genre = Genre.model_validate(new_genre.model_dump())
    session.add(genre)
    session.commit()
    session.refresh(genre)
    return genre


@router.delete("/{genre_id}", status_code=204)
def delete_genre(
    genre_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(admin_only),
):
    genre = get_genre_or_404(session, genre_id)
    if genre.books:
        raise HTTPException(
            status_code=409,
            detail="This genre still has books. Remove it from those books first.",
        )
    session.delete(genre)
    session.commit()
