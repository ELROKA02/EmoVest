## 1. Backend Endpoint

- [x] 1.1 Crear un router backend para `GET /operaciones/export.csv` con autenticacion mediante `get_current_user`.
- [x] 1.2 Definir query params `cuenta_ids: list[int] | None`, `fecha_desde: datetime | None` y `fecha_hasta: datetime | None`.
- [x] 1.3 Registrar el nuevo router en `backend/app.py` con tag OpenAPI adecuado.

## 2. Account Ownership And Querying

- [x] 2.1 Consultar cuentas del usuario autenticado desde `Cuenta_Trading`.
- [x] 2.2 Normalizar IDs repetidos en `cuenta_ids` antes de consultar.
- [x] 2.3 Si `cuenta_ids` se envio y algun ID no pertenece al usuario o no existe, devolver `404` sin CSV parcial.
- [x] 2.4 Consultar operaciones por cuentas propias y aplicar filtros inclusivos `fecha_hora >= fecha_desde` y `fecha_hora <= fecha_hasta`.
- [x] 2.5 Ordenar resultados por `fecha_hora` ascendente y luego `id` ascendente para salida estable.

## 3. CSV Generation

- [x] 3.1 Crear cabeceras fijas: `cuenta_id`, `cuenta_nombre`, `operacion_id`, `fecha_hora`, `tipo_operacion`, `activo`, `cantidad`, `precio_entrada`, `precio_salida`, `resultado`, `stop_loss`, `take_profit`, `ratio_rr`, `nivel_confianza`, `notas`, `screenshot`.
- [x] 3.2 Serializar `None` como celda vacia, `datetime` como ISO 8601 y valores numericos/Decimal como `str`.
- [x] 3.3 Incluir nombre de cuenta en cada fila para que exportaciones multi-cuenta sean legibles.
- [x] 3.4 Devolver `200 OK` con `text/csv` y `Content-Disposition` de descarga aunque no haya operaciones.

## 4. Verification

- [x] 4.1 Verificar que una request sin token a `/operaciones/export.csv` no devuelve datos.
- [x] 4.2 Verificar exportacion de todas las cuentas propias cuando no se envia `cuenta_ids`.
- [x] 4.3 Verificar exportacion de una y varias cuentas propias con `cuenta_ids` repetido.
- [x] 4.4 Verificar que una cuenta inexistente o ajena devuelve `404` y no exporta parcial.
- [x] 4.5 Verificar filtros `fecha_desde`, `fecha_hasta` y ambos combinados.
- [x] 4.6 Ejecutar comprobacion backend disponible (`uvicorn app:app --reload` o import equivalente) y validar que OpenAPI incluye el endpoint.
