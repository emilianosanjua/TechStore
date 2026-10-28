"""Núcleo de negocio de TechStore (Actividad 4, Unidad 4).

Contiene Value Objects (Money, OrderItem), la entidad Customer, el
Aggregate Root Order con su máquina de estados y los Domain Events.
No depende de FastAPI ni de archivos CSV.
"""
from dataclasses import dataclass, field
from decimal import Decimal
from enum import Enum
from datetime import datetime, timezone

MAX_UNITS_PER_ORDER = 20


# ---------- Excepciones de dominio ----------
class DomainException(Exception):
    pass


class InvalidOrderData(DomainException):
    pass


class InvalidOrderTransition(DomainException):
    pass


class OrderItemLimitExceeded(DomainException):
    pass


# ---------- Value Objects ----------
@dataclass(frozen=True)
class Money:
    amount: Decimal
    currency: str = "MXN"

    def __post_init__(self):
        if not isinstance(self.amount, Decimal):
            raise InvalidOrderData("El monto debe ser Decimal, no float ni int")
        if not self.amount.is_finite() or self.amount < 0:
            raise InvalidOrderData("Monto inválido")

    def add(self, other):
        if self.currency != other.currency:
            raise InvalidOrderData("Monedas distintas")
        return Money(self.amount + other.amount, self.currency)


@dataclass(frozen=True)
class Customer:
    id: str
    is_vip: bool = False
    active: bool = True


@dataclass(frozen=True)
class OrderItem:
    sku: str
    quantity: int
    unit_price: Money

    def __post_init__(self):
        if not self.sku.strip() or self.quantity <= 0:
            raise InvalidOrderData("Artículo inválido")

    @property
    def subtotal(self):
        return Money(self.unit_price.amount * self.quantity)


# ---------- Eventos ----------
@dataclass(frozen=True)
class DomainEvent:
    name: str
    order_id: str
    occurred_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    detail: str = ""


class OrderStatus(str, Enum):
    DRAFT = "DRAFT"
    CONFIRMED = "CONFIRMED"
    SHIPPED = "SHIPPED"
    DELIVERED = "DELIVERED"
    CANCELLED = "CANCELLED"
    RETURNED = "RETURNED"


# ---------- Aggregate Root ----------
@dataclass
class Order:
    customer: Customer
    id: str
    has_promotion: bool = False
    status: OrderStatus = OrderStatus.DRAFT
    items: list[OrderItem] = field(default_factory=list)
    events: list = field(default_factory=list)
    tracking_number: str | None = None
    cancel_reason: str | None = None

    @property
    def units(self):
        return sum(item.quantity for item in self.items)

    @property
    def total(self):
        amount = sum((x.subtotal.amount for x in self.items), Decimal("0"))
        return Money(amount)

    def add_item(self, item):
        if self.status != OrderStatus.DRAFT:
            raise InvalidOrderTransition("Solo DRAFT admite artículos")
        if self.units + item.quantity > MAX_UNITS_PER_ORDER:
            raise OrderItemLimitExceeded("Máximo 20 unidades")
        if item.unit_price.currency != "MXN":
            raise InvalidOrderData("Solo MXN")
        self.items.append(item)

    # Regla común: validar primero, cambiar status después, evento al final.
    def _record(self, name, detail=""):
        self.events.append(DomainEvent(name, self.id, detail=detail))

    def confirm(self):
        if self.status != OrderStatus.DRAFT:
            raise InvalidOrderTransition("Solo DRAFT")
        if not self.items or not self.customer.active:
            raise InvalidOrderData("Requiere artículos y cliente activo")
        self.status = OrderStatus.CONFIRMED
        self._record("OrderConfirmed")

    def ship(self, tracking_number):
        if self.status != OrderStatus.CONFIRMED:
            raise InvalidOrderTransition("Solo CONFIRMED puede enviarse")
        if not tracking_number or not tracking_number.strip():
            raise InvalidOrderData("El envío requiere número de guía")
        self.status = OrderStatus.SHIPPED
        self.tracking_number = tracking_number.strip()
        self._record("OrderShipped", self.tracking_number)

    def cancel(self, reason):
        if self.status != OrderStatus.CONFIRMED:
            raise InvalidOrderTransition("Solo CONFIRMED puede cancelarse")
        if not reason or not reason.strip():
            raise InvalidOrderData("La cancelación requiere motivo")
        self.status = OrderStatus.CANCELLED
        self.cancel_reason = reason.strip()
        self._record("OrderCancelled", self.cancel_reason)

    def deliver(self):
        if self.status != OrderStatus.SHIPPED:
            raise InvalidOrderTransition("Solo SHIPPED puede entregarse")
        self.status = OrderStatus.DELIVERED
        self._record("OrderDelivered")

    def return_order(self):
        if self.status != OrderStatus.SHIPPED:
            raise InvalidOrderTransition("Solo SHIPPED puede devolverse")
        self.status = OrderStatus.RETURNED
        self._record("OrderReturned")
