from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import selectinload
from sqlmodel import Session, col, select

from app.database import get_session
from app.dependencies import require_roles
from app.dtos.requests import BookCreateRequest, BookUpdateRequest
from app.dtos.responses import BookResponse
from app.enums import Role
from app.models import Book, Genre, Order, User
from app.routers.authors import get_author_or_404

router = APIRouter(prefix="/books", tags=["books"])

staff_or_admin = require_roles([Role.staff, Role.admin])
admin_only = require_roles([Role.admin])


def get_book_or_404(session, book_id):
    book = session.get(Book, book_id)
    if book is None:
        raise HTTPException(status_code=404, detail="Book not found")
    return book


def get_genres_or_404(session, genre_ids):
    genres = session.exec(select(Genre).where(Genre.id.in_(genre_ids))).all()
    missing = set(genre_ids) - {genre.id for genre in genres}
    if missing:
        raise HTTPException(status_code=404, detail=f"Genres not found: {sorted(missing)}")
    return genres


# ---- anyone, no login needed ------------------------------------------


@router.get("", response_model=list[BookResponse])
def list_books(
    genre: str | None = None,
    author_id: int | None = None,
    in_stock: bool = False,
    session: Session = Depends(get_session),
):
    # Load every book's author and genres in two extra queries in total,
    # instead of two extra queries per book.
    query = select(Book).options(
        selectinload(Book.author),  # type: ignore[arg-type]
        selectinload(Book.genres),  # type: ignore[arg-type]
    )

    if genre is not None:
        query = query.join(Book.genres).where(Genre.name == genre.lower())  # type: ignore[arg-type]
    if author_id is not None:
        query = query.where(Book.author_id == author_id)
    if in_stock:
        query = query.where(Book.stock > 0)

    return session.exec(query.order_by(col(Book.id))).all()


@router.get("/{book_id}", response_model=BookResponse)
def get_book(book_id: int, session: Session = Depends(get_session)):
    return get_book_or_404(session, book_id)


# ---- staff and admins -------------------------------------------------


@router.post("", response_model=BookResponse, status_code=201)
def create_book(
    new_book: BookCreateRequest,
    session: Session = Depends(get_session),
    current_user: User = Depends(staff_or_admin),
):
    get_author_or_404(session, new_book.author_id)
    genres = get_genres_or_404(session, new_book.genre_ids)

    book = Book.model_validate(new_book.model_dump(exclude={"genre_ids"}))  # book.id is None here
    book.genres = genres  # SQLModel writes the book_genre rows for us
    session.add(book)
    session.commit()  # the database assigns the next id
    session.refresh(book)  # reload the saved row, new id included
    return book


@router.patch("/{book_id}", response_model=BookResponse)
def update_book(
    book_id: int,
    update: BookUpdateRequest,
    session: Session = Depends(get_session),
    current_user: User = Depends(staff_or_admin),
):
    book = get_book_or_404(session, book_id)
    changes = update.model_dump(exclude_unset=True, exclude_none=True)

    if "author_id" in changes:
        get_author_or_404(session, changes["author_id"])
    if "genre_ids" in changes:
        book.genres = get_genres_or_404(session, changes.pop("genre_ids"))

    for field, value in changes.items():
        setattr(book, field, value)
    session.add(book)
    session.commit()
    session.refresh(book)
    return book


# ---- admins only ------------------------------------------------------


@router.delete("/{book_id}", status_code=204)
def delete_book(
    book_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(admin_only),
):
    book = get_book_or_404(session, book_id)
    if session.exec(select(Order).where(Order.book_id == book_id)).first():
        raise HTTPException(
            status_code=409,
            detail="This book has orders. Set its stock to 0 instead of deleting it.",
        )
    session.delete(book)  # its rows in book_genre are removed with it
    session.commit()
