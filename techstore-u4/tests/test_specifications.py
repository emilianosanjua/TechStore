from decimal import Decimal

from app.domain import Customer, Money, Order, OrderItem
from app.specifications import (
    ActivePromotionSpec, MinimumAmountSpec, MinimumUnitsSpec, VIPCustomerSpec,
    discount_rate, discounted_total, five_percent, ten_percent, any_discount,
)
from cargar_csv import load_fixture


def _pedido(total_unit="150.00", qty=4, vip=True, promo=False):
    o = Order(customer=Customer("C", vip, True), id="S1", has_promotion=promo)
    o.add_item(OrderItem("SKU001", qty, Money(Decimal(total_unit))))
    return o


def test_monto_minimo_es_estricto():
    assert not MinimumAmountSpec(500).is_satisfied_by(_pedido("125.00", 4))   # exactamente 500
    assert MinimumAmountSpec(500).is_satisfied_by(_pedido("125.01", 4))


def test_unidades_minimas_incluye_el_limite():
    assert MinimumUnitsSpec(4).is_satisfied_by(_pedido(qty=4))
    assert not MinimumUnitsSpec(4).is_satisfied_by(_pedido(qty=3))


def test_vip_y_promocion():
    assert VIPCustomerSpec().is_satisfied_by(_pedido(vip=True))
    assert not VIPCustomerSpec().is_satisfied_by(_pedido(vip=False))
    assert ActivePromotionSpec().is_satisfied_by(_pedido(promo=True))


def test_operadores_and_or_not():
    vip, promo = VIPCustomerSpec(), ActivePromotionSpec()
    o = _pedido(vip=True, promo=False)
    assert (vip & ~promo).is_satisfied_by(o)
    assert (vip | promo).is_satisfied_by(o)
    assert not (vip & promo).is_satisfied_by(o)
    assert not (~vip).is_satisfied_by(o)


def test_specification_no_modifica_el_pedido():
    o = _pedido()
    antes = (o.status, o.units, o.total, list(o.events))
    ten_percent.is_satisfied_by(o)
    assert (o.status, o.units, o.total, list(o.events)) == antes


def test_prioridad_10_sobre_5_cuando_cumple_ambas():
    o = _pedido("1500.00", 4, vip=True)          # total 6000: cumple 10 % y 5 %
    assert ten_percent.is_satisfied_by(o) and five_percent.is_satisfied_by(o)
    assert discount_rate(o) == Decimal("0.10")
    assert discounted_total(o).amount == Decimal("5400.00")


def test_cinco_por_ciento_no_requiere_vip():
    o = _pedido("6000.00", 1, vip=False)
    assert discount_rate(o) == Decimal("0.05")


def test_cinco_por_ciento_es_estricto_en_5000():
    assert discount_rate(_pedido("5000.00", 1, vip=False)) == Decimal("0")


def test_promocion_bloquea_ambos_descuentos():
    assert discount_rate(_pedido("6000.00", 4, vip=True, promo=True)) == Decimal("0")


def test_composicion_or_de_ambas_reglas():
    assert any_discount.is_satisfied_by(load_fixture()["O001"])
    assert any_discount.is_satisfied_by(load_fixture()["O006"])
    assert not any_discount.is_satisfied_by(load_fixture()["O005"])
