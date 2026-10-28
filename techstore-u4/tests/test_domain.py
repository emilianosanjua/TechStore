from decimal import Decimal

import pytest

from app.domain import (
    Customer, DomainEvent, InvalidOrderData, InvalidOrderTransition, Money, Order,
    OrderItem, OrderItemLimitExceeded, OrderStatus,
)
from cargar_csv import load_fixture


def _item(sku="SKU001", qty=1, price="100.00"):
    return OrderItem(sku, qty, Money(Decimal(price)))


def _order(active=True, vip=False, promo=False):
    return Order(customer=Customer("C", vip, active), id="T1", has_promotion=promo)


# ---------- Money ----------
def test_money_negativo():
    with pytest.raises(InvalidOrderData):
        Money(Decimal("-1"))


def test_money_no_finito():
    with pytest.raises(InvalidOrderData):
        Money(Decimal("NaN"))


def test_money_rechaza_float():
    with pytest.raises(InvalidOrderData):
        Money(600.0)


def test_money_es_inmutable():
    m = Money(Decimal("10"))
    with pytest.raises(Exception):
        m.amount = Decimal("20")


def test_money_add_devuelve_objeto_nuevo():
    a, b = Money(Decimal("10.50")), Money(Decimal("2.25"))
    c = a.add(b)
    assert c.amount == Decimal("12.75") and a.amount == Decimal("10.50")


def test_money_add_monedas_distintas():
    with pytest.raises(InvalidOrderData):
        Money(Decimal("1"), "MXN").add(Money(Decimal("1"), "USD"))


# ---------- OrderItem ----------
def test_item_cantidad_cero_o_negativa():
    for q in (0, -3):
        with pytest.raises(InvalidOrderData):
            _item(qty=q)


def test_item_sku_vacio():
    with pytest.raises(InvalidOrderData):
        _item(sku="  ")


def test_item_subtotal_calculado():
    assert _item(qty=2, price="600.00").subtotal.amount == Decimal("1200.00")


# ---------- Order ----------
def test_pedido_o001_inicia_draft():
    orders = load_fixture()
    assert orders["O001"].status.value == "DRAFT"
    assert orders["O001"].units == 4
    assert orders["O001"].total.amount == Decimal("2100.00")


def test_carga_16_pedidos_todos_draft():
    orders = load_fixture()
    assert len(orders) == 16
    assert all(o.status == OrderStatus.DRAFT for o in orders.values())


def test_total_vale_decimal_exacto():
    o = _order()
    o.add_item(_item(qty=3, price="0.10"))
    assert o.total.amount == Decimal("0.30")  # con float daría 0.30000000000000004


def test_unidades_no_son_renglones():
    o = _order()
    o.add_item(_item("SKU001", 10))
    o.add_item(_item("SKU002", 10))
    assert len(o.items) == 2 and o.units == 20


def test_veintiuna_unidades_se_rechazan_sin_modificar_items():
    o = _order()
    o.add_item(_item(qty=19))
    with pytest.raises(OrderItemLimitExceeded):
        o.add_item(_item("SKU002", 2))
    assert len(o.items) == 1 and o.units == 19


def test_no_se_agregan_items_fuera_de_draft():
    o = _order()
    o.add_item(_item())
    o.confirm()
    with pytest.raises(InvalidOrderTransition):
        o.add_item(_item("SKU002"))


def test_item_en_moneda_distinta_se_rechaza():
    o = _order()
    with pytest.raises(InvalidOrderData):
        o.add_item(OrderItem("SKU001", 1, Money(Decimal("5"), "USD")))


def test_pedido_vacio_no_confirma():
    o = _order()
    with pytest.raises(InvalidOrderData):
        o.confirm()
    assert o.status == OrderStatus.DRAFT and o.events == []


def test_cliente_inactivo_no_confirma():
    o = _order(active=False)
    o.add_item(_item())
    with pytest.raises(InvalidOrderData):
        o.confirm()
    assert o.status == OrderStatus.DRAFT and o.events == []


# ---------- Máquina de estados y eventos ----------
def _confirmada():
    o = _order()
    o.add_item(_item())
    o.confirm()
    return o


def test_confirmacion_doble_no_agrega_evento():
    o = _order()
    o.add_item(_item())
    o.confirm()
    assert o.status == OrderStatus.CONFIRMED and len(o.events) == 1
    with pytest.raises(InvalidOrderTransition):
        o.confirm()
    assert len(o.events) == 1


def test_envio_sin_guia_falla_y_no_cambia_estado():
    o = _confirmada()
    for guia in ("", "   ", None):
        with pytest.raises(InvalidOrderData):
            o.ship(guia)
    assert o.status == OrderStatus.CONFIRMED
    assert [e.name for e in o.events] == ["OrderConfirmed"]


def test_envio_desde_draft_prohibido():
    o = _order()
    o.add_item(_item())
    with pytest.raises(InvalidOrderTransition):
        o.ship("G1")


def test_cancelar_requiere_motivo():
    o = _confirmada()
    with pytest.raises(InvalidOrderData):
        o.cancel("  ")
    assert o.status == OrderStatus.CONFIRMED


def test_cancelar_desde_confirmed():
    o = _confirmada()
    o.cancel("Cliente se arrepintió")
    assert o.status == OrderStatus.CANCELLED
    assert o.events[-1].name == "OrderCancelled"


def test_cancelacion_desde_shipped_rechazada():
    o = _confirmada()
    o.ship("G1")
    with pytest.raises(InvalidOrderTransition):
        o.cancel("tarde")
    assert o.status == OrderStatus.SHIPPED
    assert [e.name for e in o.events] == ["OrderConfirmed", "OrderShipped"]


def test_entrega_y_devolucion_solo_desde_shipped():
    o = _confirmada()
    with pytest.raises(InvalidOrderTransition):
        o.deliver()
    with pytest.raises(InvalidOrderTransition):
        o.return_order()


def test_camino_feliz_entregado_con_todos_los_eventos():
    o = _confirmada()
    o.ship("G1")
    o.deliver()
    assert o.status == OrderStatus.DELIVERED
    assert [e.name for e in o.events] == ["OrderConfirmed", "OrderShipped", "OrderDelivered"]


def test_estados_finales_no_admiten_mas_transiciones():
    o = _confirmada()
    o.ship("G1")
    o.return_order()
    assert o.status == OrderStatus.RETURNED
    for op in (o.confirm, o.deliver, o.return_order, lambda: o.cancel("x"), lambda: o.ship("G2")):
        with pytest.raises(InvalidOrderTransition):
            op()


def test_eventos_son_inmutables_y_llevan_pedido():
    o = _confirmada()
    e = o.events[0]
    assert isinstance(e, DomainEvent) and e.order_id == "T1"
    with pytest.raises(Exception):
        e.name = "otro"
