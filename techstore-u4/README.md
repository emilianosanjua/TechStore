# TechStore U4 — Núcleo de negocio (Actividad 4)

Componentes de Lógica de Negocio · Unidad 4 · FIME UANL.
Programa que lee clientes, productos y pedidos de CSV, los convierte en objetos de dominio,
aplica reglas de descuento con Specifications, controla el estado de cada pedido y expone
operaciones por API REST (FastAPI). Todo en memoria: al cerrar el programa los cambios se pierden.

## Instalación y ejecución
```bash
python --version                      # 3.11 o superior
python -m venv .venv
# Windows PowerShell: .venv\Scripts\Activate.ps1   |  macOS/Linux: source .venv/bin/activate
python -m pip install -r requirements.txt
python cargar_csv.py                  # debe listar los 16 pedidos en DRAFT
python ejecutar_escenarios.py --md    # ejecuta E01-E15 y regenera BITACORA.md
python -m pytest -q                   # pruebas automáticas
uvicorn app.api:app --reload          # API; documentación en http://127.0.0.1:8000/docs
```

## Estructura
```
datos/                 5 CSV del paquete
cargar_csv.py          cargador recibido (sin modificar)
ejecutar_escenarios.py ejecuta E01-E15 y genera BITACORA.md
app/domain.py          Money, Customer, OrderItem, Order, eventos y excepciones
app/specifications.py  Specification (& | ~), reglas de 10 % y 5 %
app/api.py             API FastAPI (sin reglas de negocio)
tests/                 test_domain, test_specifications, test_escenarios, test_api
```

## Reglas implementadas
- `Money`: Decimal, moneda MXN, sin importes negativos ni no finitos; inmutable.
- Máximo **20 unidades** por pedido (suma de cantidades, no de renglones).
- **10 %**: VIP, total **> 500**, **>= 4** unidades, sin promoción.
- **5 %**: total **> 5000**, sin promoción. Si aplican ambas, gana el 10 %.
- Estados: `DRAFT → CONFIRMED → SHIPPED → DELIVERED`; `CONFIRMED → CANCELLED`; `SHIPPED → RETURNED`.
- Una operación inválida no cambia el estado ni agrega eventos.
- No se controla inventario (`existencia` es solo información de catálogo).

## Endpoints
| Método | Ruta | Éxito | Errores |
| --- | --- | --- | --- |
| GET | `/orders` | 200 | — |
| GET | `/orders/{id}` | 200 | 404 |
| POST | `/orders/{id}/items` `{sku, quantity}` | 200 | 404, 409 (límite 20), 422 |
| POST | `/orders/{id}/confirm` | 200 | 404, 409, 422 |
| POST | `/orders/{id}/ship` `{tracking_number}` | 200 | 404, 409, 422 (sin guía) |
| POST | `/orders/{id}/cancel` `{reason}` | 200 | 404, 409, 422 (sin motivo) |
| POST | `/orders/{id}/deliver` | 200 | 404, 409 |
| POST | `/orders/{id}/return` | 200 | 404, 409 |

Mapeo: `InvalidOrderTransition` y `OrderItemLimitExceeded` → 409; `InvalidOrderData` → 422;
pedido o SKU inexistente → 404.

Evidencias: ver `BITACORA.md` (escenarios) y `REPORTE.md` (diagrama de estados y preguntas).
