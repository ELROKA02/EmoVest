## Context

El backend actual expone operaciones bajo `backend/routers/operaciones.py` con rutas anidadas por cuenta (`/cuentas/{cuenta_id_trading}/operaciones`) y valida propiedad mediante `get_current_user` y consultas contra `Cuenta_Trading.id_usuario`. La exportacion debe cruzar una o varias cuentas, asi que encaja mejor como endpoint global de operaciones en vez de otra ruta anidada a una sola cuenta.

La app ya usa FastAPI, SQLAlchemy y JWT. No se requiere migracion de base de datos ni dependencia externa nueva: Python incluye `csv` e `io`, y FastAPI puede devolver `StreamingResponse` o `Response` con `text/csv`.

## Goals / Non-Goals

**Goals:**

- Crear un endpoint autenticado para descargar operaciones en CSV.
- Permitir exportar una cuenta, varias cuentas o todas las cuentas del usuario si no se especifican IDs.
- Permitir filtros opcionales por fecha inicial y fecha final, aplicados sobre `Operacion.fecha_hora`.
- Impedir exportaciones parciales o filtraciones si se solicita una cuenta inexistente o ajena al usuario.
- Devolver un CSV estable, apto para hojas de calculo y procesamiento externo.

**Non-Goals:**

- Crear UI frontend para lanzar la exportacion.
- Exportar capturas como archivos binarios.
- Exportar registros emocionales en esta primera version.
- Cambiar modelos, tablas o flujo asincrono de analisis emocional.

## Decisions

- **Endpoint global:** implementar `GET /operaciones/export.csv`.
  - Razon: el router actual esta anidado bajo una cuenta concreta, pero el caso de uso incluye varias cuentas.
  - Alternativa considerada: `GET /cuentas/{id}/operaciones/export.csv`; se descarta porque no cubre varias cuentas sin multiples requests.

- **Filtro de cuentas:** aceptar `cuenta_ids` como query repetible (`?cuenta_ids=1&cuenta_ids=2`). Si se omite, exportar todas las cuentas del usuario autenticado.
  - Razon: FastAPI soporta listas en query de forma nativa y el fallback a todas las cuentas mejora portabilidad de datos.
  - Alternativa considerada: CSV en un unico parametro (`?cuenta_ids=1,2`); se descarta para evitar parsing manual innecesario.

- **Propiedad estricta:** resolver primero las cuentas solicitadas contra `Cuenta_Trading.id_usuario == current_user.id`. Si falta alguna, responder `404` sin devolver CSV.
  - Razon: mantiene el patron actual del proyecto, que oculta si una cuenta existe pero pertenece a otro usuario.
  - Alternativa considerada: ignorar IDs ajenos y exportar solo los propios; se descarta porque podria ocultar errores del cliente y producir exportaciones incompletas.

- **Filtros de fecha inclusivos:** usar `fecha_desde` y `fecha_hasta` opcionales con tipo `datetime`; aplicar `>= fecha_desde` y `<= fecha_hasta`.
  - Razon: coincide con el campo real `Operacion.fecha_hora` y permite filtrar por fecha exacta o fecha/hora.
  - Alternativa considerada: filtrar por `date` puro; se descarta porque perderia precision en operaciones intradia.

- **CSV estable:** generar cabeceras fijas: `cuenta_id`, `cuenta_nombre`, `operacion_id`, `fecha_hora`, `tipo_operacion`, `activo`, `cantidad`, `precio_entrada`, `precio_salida`, `resultado`, `stop_loss`, `take_profit`, `ratio_rr`, `nivel_confianza`, `notas`, `screenshot`.
  - Razon: incluye contexto de cuenta para exportaciones multi-cuenta y todos los campos principales de `Operacion`.
  - Alternativa considerada: exportar solo columnas visibles en frontend; se descarta porque la API debe ser mas completa y estable.

## Risks / Trade-offs

- Exportaciones muy grandes pueden consumir memoria si se genera todo el CSV de una vez -> usar `StringIO` para la primera version y mantener el codigo aislado para migrar a streaming por chunks si aparece volumen alto.
- Fechas sin zona horaria pueden interpretarse distinto entre clientes -> documentar que se comparan contra `fecha_hora` tal como esta guardado en la base de datos.
- Campos `Decimal` y `datetime` necesitan serializacion consistente -> convertir `None` a cadena vacia, `datetime` a ISO 8601 y decimales a `str`.
- Los IDs repetidos pueden duplicar filtros -> normalizar `cuenta_ids` con un set antes de consultar.
