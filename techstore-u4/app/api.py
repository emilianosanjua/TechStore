"""API REST de TechStore. Los endpoints NO contienen reglas de negocio:
buscan el pedido, llaman al método de Order y traducen la excepción a HTTP.

  InvalidOrderTransition  -> 409 (el estado actual no permite la operación)
  OrderItemLimitExceeded  -> 409 (conflicto con el contenido actual del pedido)
  InvalidOrderData        -> 422 (datos que no cumplen las reglas)
  pedido / SKU inexistente -> 404
"""
from decimal import Decimal

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from cargar_csv import load_fixture, rows
from app.domain import (
    InvalidOrderData, InvalidOrderTransition, Money, OrderItem, OrderItemLimitExceeded,
)
from app.specifications import discount_rate, discounted_total

app = FastAPI(title="TechStore U4")
orders = load_fixture()  # repositorio en memoria: se pierde al cerrar el programa
PRICES = {x["sku"]: Decimal(x["precio_mxn"]) for x in rows("productos.csv")}


class ShipBody(BaseModel):
    tracking_number: str


class CancelBody(BaseModel):
    reason: str


class ItemBody(BaseModel):
    sku: str
    quantity: int


def _get(order_id: str):
    order = orders.get(order_id)
    if order is None:
        raise HTTPException(status_code=404, detail="No existe")
    return order


def _view(order):
    return {
        "id": order.id,
        "customer_id": order.customer.id,
        "status": order.status.value,
        "units": order.units,
        "total": str(order.total.amount),
        "discount_rate": str(discount_rate(order)),
        "total_with_discount": str(discounted_total(order).amount),
        "tracking_number": order.tracking_number,
        "events": [e.name for e in order.events],
    }


def _apply(order, action):
    try:
        action()
    except (InvalidOrderTransition, OrderItemLimitExceeded) as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    except InvalidOrderData as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    return _view(order)


@app.get("/orders")
def list_orders():
    return [_view(o) for o in orders.values()]


@app.get("/orders/{order_id}")
def get_order(order_id: str):
    return _view(_get(order_id))


@app.post("/orders/{order_id}/items")
def add_item(order_id: str, body: ItemBody):
    order = _get(order_id)
    if body.sku not in PRICES:
        raise HTTPException(status_code=404, detail="SKU no existe")
    return _apply(order, lambda: order.add_item(
        OrderItem(body.sku, body.quantity, Money(PRICES[body.sku]))))


@app.post("/orders/{order_id}/confirm")
def confirm_order(order_id: str):
    order = _get(order_id)
    return _apply(order, order.confirm)


@app.post("/orders/{order_id}/ship")
def ship_order(order_id: str, body: ShipBody):
    order = _get(order_id)
    return _apply(order, lambda: order.ship(body.tracking_number))


@app.post("/orders/{order_id}/cancel")
def cancel_order(order_id: str, body: CancelBody):
    order = _get(order_id)
    return _apply(order, lambda: order.cancel(body.reason))


@app.post("/orders/{order_id}/deliver")
def deliver_order(order_id: str):
    order = _get(order_id)
    return _apply(order, order.deliver)


@app.post("/orders/{order_id}/return")
def return_order(order_id: str):
    order = _get(order_id)
    return _apply(order, order.return_order)
