"""Un test por escenario E01-E15 (datos/escenarios.csv). Los nombres coinciden
con la columna 'Prueba' de BITACORA.md."""
from decimal import Decimal

import pytest

from app.domain import (
    InvalidOrderData, InvalidOrderTransition, Money, OrderItem, OrderItemLimitExceeded,
)
from app.specifications import MinimumAmountSpec, discount_rate
from cargar_csv import load_fixture


def _o(order_id):
    return load_fixture()[order_id]


def test_e01_descuento_vip_10():
    assert discount_rate(_o("O001")) == Decimal("0.10")


def test_e02_no_vip_sin_descuento():
    assert discount_rate(_o("O002")) == Decimal("0")


def test_e03_cliente_inactivo_no_confirma():
    o = _o("O003")
    with pytest.raises(InvalidOrderData):
        o.confirm()
    assert o.status.value == "DRAFT" and o.events == []


def test_e04_promocion_bloquea_descuento():
    assert discount_rate(_o("O005")) == Decimal("0")


def test_e05_descuento_5_por_ciento():
    assert discount_rate(_o("O006")) == Decimal("0.05")


def test_e06_pedido_vacio_no_confirma():
    o = _o("O007")
    with pytest.raises(InvalidOrderData):
        o.confirm()
    assert o.events == []


def test_e07_veinte_unidades_permitidas():
    o = _o("O008")
    assert o.units == 20
    o.confirm()
    assert o.status.value == "CONFIRMED"


def test_e08_veintiuna_unidades_rechazadas():
    o = _o("O009")
    with pytest.raises(OrderItemLimitExceeded):
        o.add_item(OrderItem("SKU003", 2, Money(Decimal("120.00"))))
    assert o.units == 19


def test_e09_umbral_estricto_500():
    o = _o("O010")
    assert o.total.amount == Decimal("500.00")
    assert not MinimumAmountSpec(500).is_satisfied_by(o)
    assert discount_rate(o) == Decimal("0")


def test_e10_tres_unidades_no_alcanzan():
    o = _o("O011")
    assert o.customer.is_vip and o.units == 3
    assert discount_rate(o) == Decimal("0")


def test_e11_envio_sin_guia_rechazado():
    o = _o("O012")
    o.confirm()
    with pytest.raises(InvalidOrderData):
        o.ship("")
    assert o.status.value == "CONFIRMED"
    assert [e.name for e in o.events] == ["OrderConfirmed"]


def test_e12_confirmacion_doble():
    o = _o("O013")
    o.confirm()
    with pytest.raises(InvalidOrderTransition):
        o.confirm()
    assert len(o.events) == 1


def test_e13_cancelar_desde_shipped():
    o = _o("O014")
    o.confirm()
    o.ship("GUIA-001")
    with pytest.raises(InvalidOrderTransition):
        o.cancel("Ya no lo quiero")
    assert o.status.value == "SHIPPED"


def test_e14_devolucion_valida():
    o = _o("O015")
    o.confirm()
    o.ship("GUIA-002")
    o.return_order()
    assert o.status.value == "RETURNED"
    assert o.events[-1].name == "OrderReturned"


def test_e15_entrega_valida():
    o = _o("O016")
    o.confirm()
    o.ship("GUIA-003")
    o.deliver()
    assert o.status.value == "DELIVERED"
    assert o.events[-1].name == "OrderDelivered"
