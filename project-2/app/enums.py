from enum import Enum


class Role(str, Enum):
    customer = "customer"
    staff = "staff"
    admin = "admin"


class OrderStatus(str, Enum):
    pending = "pending"
    shipped = "shipped"
    cancelled = "cancelled"
