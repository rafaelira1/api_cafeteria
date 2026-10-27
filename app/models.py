from datetime import datetime, timezone
from enum import Enum

from sqlalchemy import Boolean, DateTime, Enum as SQLEnum, Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class UserRole(str, Enum):
    ADMIN = "admin"
    STAFF = "staff"
    CUSTOMER = "customer"


class User(Base):
    __tablename__ = "users"
    # Deleted identities must never be reassigned while an old JWT may exist.
    __table_args__ = {"sqlite_autoincrement": True}

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    email: Mapped[str] = mapped_column(
        String(254, collation="NOCASE"), nullable=False, unique=True, index=True
    )
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[UserRole] = mapped_column(
        SQLEnum(
            UserRole,
            values_callable=lambda roles: [role.value for role in roles],
            native_enum=False,
            create_constraint=True,
            name="user_role",
        ),
        nullable=False,
        default=UserRole.CUSTOMER,
    )
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )


class Product(Base):
    __tablename__ = "products"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    category: Mapped[str] = mapped_column(String(50), nullable=False)
    price: Mapped[float] = mapped_column(Float, nullable=False)
    size: Mapped[str] = mapped_column(String(30), nullable=False)
    is_available: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    calories: Mapped[int] = mapped_column(Integer, nullable=False)

    orders: Mapped[list["Order"]] = relationship(
        back_populates="product", passive_deletes=True
    )


class Order(Base):
    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    customer_name: Mapped[str] = mapped_column(String(100), nullable=False)
    table_number: Mapped[int] = mapped_column(Integer, nullable=False)
    payment_method: Mapped[str] = mapped_column(String(30), nullable=False)
    total_amount: Mapped[float] = mapped_column(Float, nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="pending"
    )
    is_takeaway: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    product_id: Mapped[int] = mapped_column(
        ForeignKey("products.id", ondelete="RESTRICT"), nullable=False, index=True
    )

    product: Mapped[Product] = relationship(back_populates="orders")
