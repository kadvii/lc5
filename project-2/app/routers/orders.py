
from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from app.database import get_session
from app.dependencies import get_current_user, require_roles
from app.dtos.requests import OrderCreateRequest, OrderStatusUpdateRequest
from app.dtos.responses import OrderResponse
from app.enums import OrderStatus, Role
from app.models import Book, Order, User

router = APIRouter(prefix="/orders", tags=["orders"])

STAFF_ROLES = [Role.staff, Role.admin]
staff_or_admin = require_roles(STAFF_ROLES)


@router.post("", response_model=OrderResponse, status_code=201)
def place_order(
    new_order: OrderCreateRequest,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    book = session.get(Book, new_order.book_id)
    if book is None:
        raise HTTPException(status_code=404, detail="Book not found")
    if book.stock < new_order.quantity:
        raise HTTPException(status_code=409, detail=f"Only {book.stock} left in stock")

    book.stock -= new_order.quantity
    order = Order(
        user_id=current_user.id,  # from the token -- never from the request
        book_id=book.id,
        quantity=new_order.quantity,
        total_price=round(book.price * new_order.quantity, 2),
    )
    session.add(book)
    session.add(order)
    session.commit()
    session.refresh(order)
    return order


@router.get("", response_model=list[OrderResponse])
def list_orders(
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    query = select(Order)
    if current_user.role not in STAFF_ROLES:
        query = query.where(Order.user_id == current_user.id)
    return session.exec(query).all()


@router.get("/{order_id}", response_model=OrderResponse)
def get_order(
    order_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    order = session.get(Order, order_id)
    if order is None:
        raise HTTPException(status_code=404, detail="Order not found")
    if order.user_id != current_user.id and current_user.role not in STAFF_ROLES:
        # 404, not 403: don't confirm to a stranger that this order exists.
        raise HTTPException(status_code=404, detail="Order not found")
    return order


@router.patch("/{order_id}/status", response_model=OrderResponse)
def update_order_status(
    order_id: int,
    update: OrderStatusUpdateRequest,
    session: Session = Depends(get_session),
    current_user: User = Depends(staff_or_admin),
):
    order = session.get(Order, order_id)
    if order is None:
        raise HTTPException(status_code=404, detail="Order not found")
    if order.status == OrderStatus.cancelled:
        raise HTTPException(status_code=400, detail="A cancelled order cannot be changed")

    if update.status == OrderStatus.cancelled:
        book = session.get(Book, order.book_id)
        if book is not None:
            book.stock += order.quantity  # put the books back on the shelf
            session.add(book)

    order.status = update.status
    session.add(order)
    session.commit()
    session.refresh(order)
    return order