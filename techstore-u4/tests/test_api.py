import pytest
from fastapi.testclient import TestClient

from app import api
from cargar_csv import load_fixture

client = TestClient(api.app)


@pytest.fixture(autouse=True)
def datos_limpios():
    """Cada prueba empieza con los 16 pedidos en DRAFT (repositorio en memoria)."""
    api.orders.clear()
    api.orders.update(load_fixture())


def test_get_pedido_existente():
    r = client.get("/orders/O001")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "DRAFT" and body["units"] == 4
    assert body["total"] == "2100.00" and body["discount_rate"] == "0.10"
    assert body["total_with_discount"] == "1890.00"


def test_lista_16_pedidos():
    assert len(client.get("/orders").json()) == 16


def test_pedido_inexistente_404():
    assert client.get("/orders/NOEXISTE").status_code == 404
    assert client.post("/orders/NOEXISTE/confirm").status_code == 404


def test_confirmar_exitoso_200():
    r = client.post("/orders/O013/confirm")
    assert r.status_code == 200
    assert r.json()["status"] == "CONFIRMED" and r.json()["events"] == ["OrderConfirmed"]


def test_confirmar_dos_veces_409():
    assert client.post("/orders/O013/confirm").status_code == 200
    r = client.post("/orders/O013/confirm")
    assert r.status_code == 409
    assert client.get("/orders/O013").json()["events"] == ["OrderConfirmed"]


def test_confirmar_pedido_vacio_422():
    assert client.post("/orders/O007/confirm").status_code == 422


def test_confirmar_cliente_inactivo_422():
    assert client.post("/orders/O003/confirm").status_code == 422


def test_enviar_sin_guia_422_y_con_guia_200():
    client.post("/orders/O012/confirm")
    assert client.post("/orders/O012/ship", json={"tracking_number": ""}).status_code == 422
    r = client.post("/orders/O012/ship", json={"tracking_number": "GUIA-9"})
    assert r.status_code == 200 and r.json()["status"] == "SHIPPED"


def test_cancelar_desde_shipped_409():
    client.post("/orders/O014/confirm")
    client.post("/orders/O014/ship", json={"tracking_number": "G1"})
    r = client.post("/orders/O014/cancel", json={"reason": "tarde"})
    assert r.status_code == 409


def test_cancelar_desde_confirmed_200():
    client.post("/orders/O014/confirm")
    r = client.post("/orders/O014/cancel", json={"reason": "cliente cambió de opinión"})
    assert r.status_code == 200 and r.json()["status"] == "CANCELLED"


def test_flujo_entrega_y_devolucion():
    for oid, final, path in (("O016", "DELIVERED", "deliver"), ("O015", "RETURNED", "return")):
        client.post(f"/orders/{oid}/confirm")
        client.post(f"/orders/{oid}/ship", json={"tracking_number": "G"})
        r = client.post(f"/orders/{oid}/{path}")
        assert r.status_code == 200 and r.json()["status"] == final


def test_agregar_items_respeta_limite_de_20_unidades():
    assert client.post("/orders/O009/items", json={"sku": "SKU003", "quantity": 1}).status_code == 200
    assert client.post("/orders/O009/items", json={"sku": "SKU003", "quantity": 1}).status_code == 409
    assert client.get("/orders/O009").json()["units"] == 20


def test_agregar_sku_inexistente_404():
    assert client.post("/orders/O001/items", json={"sku": "SKU999", "quantity": 1}).status_code == 404


def test_agregar_cantidad_invalida_422():
    assert client.post("/orders/O001/items", json={"sku": "SKU001", "quantity": 0}).status_code == 422
