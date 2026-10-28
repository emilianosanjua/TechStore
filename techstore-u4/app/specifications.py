"""Specification Pattern: reglas de descuento combinables con & | ~.

Una Specification solo responde True/False; nunca modifica el pedido.
"""
from decimal import Decimal, ROUND_HALF_UP

from app.domain import Money


class Specification:
    def is_satisfied_by(self, order):
        raise NotImplementedError

    def __and__(self, other):
        return AndSpec(self, other)

    def __or__(self, other):
        return OrSpec(self, other)

    def __invert__(self):
        return NotSpec(self)


class AndSpec(Specification):
    def __init__(self, left, right):
        self.left, self.right = left, right

    def is_satisfied_by(self, order):
        return self.left.is_satisfied_by(order) and self.right.is_satisfied_by(order)


class OrSpec(Specification):
    def __init__(self, left, right):
        self.left, self.right = left, right

    def is_satisfied_by(self, order):
        return self.left.is_satisfied_by(order) or self.right.is_satisfied_by(order)


class NotSpec(Specification):
    def __init__(self, inner):
        self.inner = inner

    def is_satisfied_by(self, order):
        return not self.inner.is_satisfied_by(order)


class MinimumAmountSpec(Specification):
    """Total ESTRICTAMENTE mayor al umbral (>, no >=)."""

    def __init__(self, threshold):
        self.threshold = Decimal(str(threshold))

    def is_satisfied_by(self, order):
        return order.total.amount > self.threshold


class VIPCustomerSpec(Specification):
    def is_satisfied_by(self, order):
        return order.customer.is_vip


class MinimumUnitsSpec(Specification):
    """Al menos N unidades (>=)."""

    def __init__(self, minimum):
        self.minimum = minimum

    def is_satisfied_by(self, order):
        return order.units >= self.minimum


class ActivePromotionSpec(Specification):
    def is_satisfied_by(self, order):
        return order.has_promotion


# ---------- Reglas de descuento de la Actividad 4 ----------
ten_percent = (
    MinimumAmountSpec(Decimal("500"))
    & VIPCustomerSpec()
    & MinimumUnitsSpec(4)
    & ~ActivePromotionSpec()
)
five_percent = MinimumAmountSpec(Decimal("5000")) & ~ActivePromotionSpec()
any_discount = ten_percent | five_percent


def discount_rate(order):
    """Devuelve la tasa de descuento. Si aplican ambas, gana el 10 %."""
    if ten_percent.is_satisfied_by(order):
        return Decimal("0.10")
    if five_percent.is_satisfied_by(order):
        return Decimal("0.05")
    return Decimal("0")


def discounted_total(order):
    rate = discount_rate(order)
    amount = (order.total.amount * (Decimal("1") - rate)).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )
    return Money(amount)
