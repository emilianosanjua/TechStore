"""Ejecuta los escenarios E01-E15 de datos/escenarios.csv sobre el dominio real.

Uso:
    python ejecutar_escenarios.py            # imprime la bitácora
    python ejecutar_escenarios.py --md       # escribe BITACORA.md
Cada escenario carga los datos de nuevo (load_fixture) para trabajar con
objetos independientes; no se edita ningún CSV.
"""
import sys
from decimal import Decimal

from cargar_csv import load_fixture
from app.domain import (
    DomainException, Money, OrderItem,
)
from app.specifications import (
    discount_rate, discounted_total, MinimumAmountSpec, ten_percent, five_percent,
)


def _pre(order):
    c = order.customer
    return (
        f"{order.id}, cliente {c.id} (VIP={'sí' if c.is_vip else 'no'}, "
        f"activo={'sí' if c.active else 'no'}), promoción={'sí' if order.has_promotion else 'no'}, "
        f"{order.units} unidades, total {order.total.amount} MXN, estado {order.status.value}"
    )


def _try(fn):
    """Ejecuta fn y devuelve el nombre de la excepción de dominio, o None."""
    try:
        fn()
        return None
    except DomainException as exc:
        return f"{type(exc).__name__}: {exc}"


def _row(caso, order, operacion, resultado, esperado_ok, prueba, estado0):
    return {
        "caso": caso,
        "pedido": order.id,
        "precondiciones": estado0,
        "operacion": operacion,
        "resultado": resultado,
        "estado_final": order.status.value,
        "eventos": [e.name for e in order.events] or ["(ninguno)"],
        "cumple": esperado_ok,
        "prueba": prueba,
    }


def _descuento(caso, oid, esperado, prueba):
    order = load_fixture()[oid]
    pre = _pre(order)
    rate = discount_rate(order)
    pct = f"{int(rate * 100)}%"
    res = f"Descuento {pct}; total con descuento {discounted_total(order).amount} MXN"
    return _row(caso, order, "evaluar_descuento", res, pct == esperado, prueba, pre)


def run_all():
    out = []

    out.append(_descuento("E01", "O001", "10%", "test_e01_descuento_vip_10"))
    out.append(_descuento("E02", "O002", "0%", "test_e02_no_vip_sin_descuento"))

    # E03 confirmar con cliente inactivo
    o = load_fixture()["O003"]; pre = _pre(o)
    err = _try(o.confirm)
    out.append(_row("E03", o, "confirmar", f"Rechazado: {err}", err is not None
                    and err.startswith("InvalidOrderData") and not o.events,
                    "test_e03_cliente_inactivo_no_confirma", pre))

    out.append(_descuento("E04", "O005", "0%", "test_e04_promocion_bloquea_descuento"))
    out.append(_descuento("E05", "O006", "5%", "test_e05_descuento_5_por_ciento"))

    # E06 pedido vacío
    o = load_fixture()["O007"]; pre = _pre(o)
    err = _try(o.confirm)
    out.append(_row("E06", o, "confirmar", f"Rechazado: {err}", err is not None
                    and err.startswith("InvalidOrderData") and not o.events,
                    "test_e06_pedido_vacio_no_confirma", pre))

    # E07 20 unidades exactas
    o = load_fixture()["O008"]; pre = _pre(o)
    err = _try(o.confirm)
    out.append(_row("E07", o, "confirmar", "Éxito" if err is None else f"Rechazado: {err}",
                    err is None and o.status.value == "CONFIRMED",
                    "test_e07_veinte_unidades_permitidas", pre))

    # E08 agregar SKU003 x2 sobre 19 unidades
    o = load_fixture()["O009"]; pre = _pre(o)
    antes = (len(o.items), o.units)
    err = _try(lambda: o.add_item(OrderItem("SKU003", 2, Money(Decimal("120.00")))))
    sin_cambios = (len(o.items), o.units) == antes
    out.append(_row("E08", o, "agregar SKU003 x2", f"Rechazado: {err}; el pedido sigue con {o.units} unidades",
                    err is not None and err.startswith("OrderItemLimitExceeded") and sin_cambios,
                    "test_e08_veintiuna_unidades_rechazadas", pre))

    # E09 umbral estricto > 500 (total exacto 500)
    o = load_fixture()["O010"]; pre = _pre(o)
    rate = discount_rate(o)
    umbral = MinimumAmountSpec(500).is_satisfied_by(o)
    out.append(_row("E09", o, "evaluar_descuento",
                    f"Total {o.total.amount}: MinimumAmountSpec(500)={umbral}; descuento {int(rate * 100)}%",
                    (not umbral) and rate == 0, "test_e09_umbral_estricto_500", pre))

    out.append(_descuento("E10", "O011", "0%", "test_e10_tres_unidades_no_alcanzan"))

    # E11 confirmar y enviar sin guía
    o = load_fixture()["O012"]; pre = _pre(o)
    e1 = _try(o.confirm)
    e2 = _try(lambda: o.ship(""))
    out.append(_row("E11", o, "confirmar y enviar sin guía",
                    f"Confirmar: {'éxito' if e1 is None else e1}; enviar sin guía: rechazado ({e2})",
                    e1 is None and e2 is not None and e2.startswith("InvalidOrderData")
                    and o.status.value == "CONFIRMED" and [e.name for e in o.events] == ["OrderConfirmed"],
                    "test_e11_envio_sin_guia_rechazado", pre))

    # E12 confirmar dos veces
    o = load_fixture()["O013"]; pre = _pre(o)
    e1 = _try(o.confirm)
    n = len(o.events)
    e2 = _try(o.confirm)
    out.append(_row("E12", o, "confirmar dos veces",
                    f"1.ª: {'éxito' if e1 is None else e1}; 2.ª: rechazado ({e2})",
                    e1 is None and e2 is not None and e2.startswith("InvalidOrderTransition")
                    and len(o.events) == n == 1, "test_e12_confirmacion_doble", pre))

    # E13 cancelar desde SHIPPED
    o = load_fixture()["O014"]; pre = _pre(o)
    o.confirm(); o.ship("GUIA-001")
    err = _try(lambda: o.cancel("Ya no lo quiero"))
    out.append(_row("E13", o, "confirmar, enviar y cancelar",
                    f"Confirmar y enviar: éxito; cancelar: rechazado ({err})",
                    err is not None and err.startswith("InvalidOrderTransition")
                    and o.status.value == "SHIPPED"
                    and [e.name for e in o.events] == ["OrderConfirmed", "OrderShipped"],
                    "test_e13_cancelar_desde_shipped", pre))

    # E14 devolver
    o = load_fixture()["O015"]; pre = _pre(o)
    o.confirm(); o.ship("GUIA-002"); o.return_order()
    out.append(_row("E14", o, "confirmar, enviar y devolver", "Éxito; termina en RETURNED",
                    o.status.value == "RETURNED", "test_e14_devolucion_valida", pre))

    # E15 entregar
    o = load_fixture()["O016"]; pre = _pre(o)
    o.confirm(); o.ship("GUIA-003"); o.deliver()
    out.append(_row("E15", o, "confirmar, enviar y entregar", "Éxito; termina en DELIVERED",
                    o.status.value == "DELIVERED", "test_e15_entrega_valida", pre))

    return out


def to_markdown(rows):
    lines = [
        "# Bitácora de escenarios E01–E15 (TechStore U4)",
        "",
        "Generada con `python ejecutar_escenarios.py --md` ejecutando el dominio real; "
        "los resultados no están escritos a mano.",
        "",
        "| Caso | Precondiciones | Operación | Resultado real | Estado final | Eventos emitidos | Prueba | ¿Cumple? |",
        "| --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for r in rows:
        lines.append(
            f"| {r['caso']} | {r['precondiciones']} | {r['operacion']} | {r['resultado']} | "
            f"{r['estado_final']} | {', '.join(r['eventos'])} | `{r['prueba']}` | "
            f"{'Sí' if r['cumple'] else 'NO'} |"
        )
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    rows = run_all()
    if "--md" in sys.argv:
        with open("BITACORA.md", "w", encoding="utf-8") as f:
            f.write(to_markdown(rows))
        print("BITACORA.md generada")
    for r in rows:
        print(r["caso"], "OK " if r["cumple"] else "FALLA", "|", r["resultado"], "|", r["estado_final"], "|", r["eventos"])
    sys.exit(0 if all(r["cumple"] for r in rows) else 1)
