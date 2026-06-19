## Why

Los usuarios necesitan sacar sus operaciones de EmoVest para analizarlas fuera de la app, compartirlas con herramientas propias o conservar copias locales. Ahora que el proyecto se orienta a self-host open source, la portabilidad de datos por cuenta es una capacidad base.

## What Changes

- Añadir un endpoint autenticado para exportar operaciones en CSV.
- Permitir filtrar la exportacion por una o varias cuentas de trading del usuario autenticado.
- Permitir filtrar la exportacion por rango de fechas.
- Garantizar que solo se exportan operaciones pertenecientes a cuentas del usuario autenticado.
- Devolver un archivo CSV descargable con cabeceras estables y datos de operaciones.

## Capabilities

### New Capabilities

- `operations-csv-export`: Exportacion CSV autenticada de operaciones por cuenta y rango de fechas.

### Modified Capabilities

- Ninguna.

## Impact

- Backend FastAPI: nuevo endpoint en el area de operaciones o un router de exportaciones.
- Base de datos: consultas de `Cuenta_Trading` y `Operacion`; no se requieren migraciones.
- Autenticacion: reutiliza JWT y `get_current_user`.
- Frontend: no requerido para esta propuesta inicial, aunque el endpoint quedara listo para una UI posterior.
- Tests/verificacion: cubrir propiedad de datos, filtros por cuentas, filtros por fechas y formato CSV.
