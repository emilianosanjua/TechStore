# Bitácora de escenarios E01–E15 (TechStore U4)

Generada con `python ejecutar_escenarios.py --md` ejecutando el dominio real; los resultados no están escritos a mano.

| Caso | Precondiciones | Operación | Resultado real | Estado final | Eventos emitidos | Prueba | ¿Cumple? |
| --- | --- | --- | --- | --- | --- | --- | --- |
| E01 | O001, cliente C001 (VIP=sí, activo=sí), promoción=no, 4 unidades, total 2100.00 MXN, estado DRAFT | evaluar_descuento | Descuento 10%; total con descuento 1890.00 MXN | DRAFT | (ninguno) | `test_e01_descuento_vip_10` | Sí |
| E02 | O002, cliente C002 (VIP=no, activo=sí), promoción=no, 2 unidades, total 1050.00 MXN, estado DRAFT | evaluar_descuento | Descuento 0%; total con descuento 1050.00 MXN | DRAFT | (ninguno) | `test_e02_no_vip_sin_descuento` | Sí |
| E03 | O003, cliente C003 (VIP=sí, activo=no), promoción=no, 4 unidades, total 2100.00 MXN, estado DRAFT | confirmar | Rechazado: InvalidOrderData: Requiere artículos y cliente activo | DRAFT | (ninguno) | `test_e03_cliente_inactivo_no_confirma` | Sí |
| E04 | O005, cliente C005 (VIP=sí, activo=sí), promoción=sí, 4 unidades, total 2100.00 MXN, estado DRAFT | evaluar_descuento | Descuento 0%; total con descuento 2100.00 MXN | DRAFT | (ninguno) | `test_e04_promocion_bloquea_descuento` | Sí |
| E05 | O006, cliente C006 (VIP=no, activo=sí), promoción=no, 1 unidades, total 18000.00 MXN, estado DRAFT | evaluar_descuento | Descuento 5%; total con descuento 17100.00 MXN | DRAFT | (ninguno) | `test_e05_descuento_5_por_ciento` | Sí |
| E06 | O007, cliente C007 (VIP=sí, activo=sí), promoción=no, 0 unidades, total 0 MXN, estado DRAFT | confirmar | Rechazado: InvalidOrderData: Requiere artículos y cliente activo | DRAFT | (ninguno) | `test_e06_pedido_vacio_no_confirma` | Sí |
| E07 | O008, cliente C008 (VIP=no, activo=sí), promoción=no, 20 unidades, total 2400.00 MXN, estado DRAFT | confirmar | Éxito | CONFIRMED | OrderConfirmed | `test_e07_veinte_unidades_permitidas` | Sí |
| E08 | O009, cliente C009 (VIP=sí, activo=sí), promoción=no, 19 unidades, total 2280.00 MXN, estado DRAFT | agregar SKU003 x2 | Rechazado: OrderItemLimitExceeded: Máximo 20 unidades; el pedido sigue con 19 unidades | DRAFT | (ninguno) | `test_e08_veintiuna_unidades_rechazadas` | Sí |
| E09 | O010, cliente C010 (VIP=no, activo=sí), promoción=no, 2 unidades, total 500.00 MXN, estado DRAFT | evaluar_descuento | Total 500.00: MinimumAmountSpec(500)=False; descuento 0% | DRAFT | (ninguno) | `test_e09_umbral_estricto_500` | Sí |
| E10 | O011, cliente C011 (VIP=sí, activo=sí), promoción=no, 3 unidades, total 1500.00 MXN, estado DRAFT | evaluar_descuento | Descuento 0%; total con descuento 1500.00 MXN | DRAFT | (ninguno) | `test_e10_tres_unidades_no_alcanzan` | Sí |
| E11 | O012, cliente C012 (VIP=no, activo=sí), promoción=no, 1 unidades, total 850.00 MXN, estado DRAFT | confirmar y enviar sin guía | Confirmar: éxito; enviar sin guía: rechazado (InvalidOrderData: El envío requiere número de guía) | CONFIRMED | OrderConfirmed | `test_e11_envio_sin_guia_rechazado` | Sí |
| E12 | O013, cliente C001 (VIP=sí, activo=sí), promoción=no, 1 unidades, total 600.00 MXN, estado DRAFT | confirmar dos veces | 1.ª: éxito; 2.ª: rechazado (InvalidOrderTransition: Solo DRAFT) | CONFIRMED | OrderConfirmed | `test_e12_confirmacion_doble` | Sí |
| E13 | O014, cliente C002 (VIP=no, activo=sí), promoción=no, 1 unidades, total 600.00 MXN, estado DRAFT | confirmar, enviar y cancelar | Confirmar y enviar: éxito; cancelar: rechazado (InvalidOrderTransition: Solo CONFIRMED puede cancelarse) | SHIPPED | OrderConfirmed, OrderShipped | `test_e13_cancelar_desde_shipped` | Sí |
| E14 | O015, cliente C005 (VIP=sí, activo=sí), promoción=no, 1 unidades, total 450.00 MXN, estado DRAFT | confirmar, enviar y devolver | Éxito; termina en RETURNED | RETURNED | OrderConfirmed, OrderShipped, OrderReturned | `test_e14_devolucion_valida` | Sí |
| E15 | O016, cliente C007 (VIP=sí, activo=sí), promoción=no, 1 unidades, total 2100.00 MXN, estado DRAFT | confirmar, enviar y entregar | Éxito; termina en DELIVERED | DELIVERED | OrderConfirmed, OrderShipped, OrderDelivered | `test_e15_entrega_valida` | Sí |
