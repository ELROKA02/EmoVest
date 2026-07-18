## Context

El backend ya expone operaciones bajo `backend/routers/operaciones.py` y acaba de incorporar `GET /operaciones/export.csv` en `backend/routers/exportaciones.py`. Ese CSV contiene columnas estables, incluyendo datos informativos de cuenta y campos principales de `Operacion`.

La importacion debe ser segura: un archivo subido por el usuario no puede decidir por si mismo a que cuentas escribir datos. Por eso el endpoint debe validar que la cuenta destino pertenece al usuario autenticado antes de leer o insertar filas.

La app ya usa FastAPI, SQLAlchemy y JWT. No se requiere migracion ni dependencia externa: Python incluye `csv`, `io`, `datetime` y `Decimal`, y FastAPI ya soporta `UploadFile` con `multipart/form-data`.

## Goals / Non-Goals

**Goals:**

- Crear un endpoint autenticado para importar operaciones desde CSV.
- Importar todas las filas validas a una cuenta de trading propia indicada por el usuario.
- Aceptar CSV compatible con la exportacion existente, ignorando columnas informativas o no insertables.
- Validar todo el archivo antes de insertar para evitar importaciones parciales.
- Devolver un resumen claro con numero de filas creadas.
- Encolar analisis emocional para operaciones importadas que incluyan `notas`, sin romper la importacion si Redis/RQ falla.

**Non-Goals:**

- Crear UI frontend para subir CSV.
- Importar operaciones repartidas en varias cuentas desde una sola llamada.
- Importar capturas binarios desde la columna `screenshot`.
- Reutilizar `operacion_id` del CSV como ID de base de datos.
- Actualizar operaciones existentes o deduplicar automaticamente.
- Importar registros emocionales historicos.

## Decisions

- **Endpoint global:** implementar `POST /operaciones/import.csv`.
  - Razon: es simetrico a `GET /operaciones/export.csv` y no queda atado a una URL anidada con formulario mixto complejo.
  - Alternativa considerada: `POST /cuentas/{id}/operaciones/import.csv`; se descarta para mantener juntas las capacidades CSV globales.

- **Cuenta destino explicita:** aceptar `cuenta_id` como campo de formulario o query requerido y verificar `Cuenta_Trading.id_usuario == current_user.id`.
  - Razon: evita confiar en `cuenta_id` del CSV y simplifica la propiedad de datos.
  - Alternativa considerada: usar `cuenta_id` de cada fila; se descarta porque permitiria CSV multi-cuenta y aumentaria riesgo de errores o filtraciones.

- **Archivo multipart:** aceptar `file: UploadFile` en `multipart/form-data`.
  - Razon: es el patron natural para subir archivos en FastAPI y encaja con clientes web.
  - Alternativa considerada: enviar CSV como texto JSON; se descarta porque empeora compatibilidad con formularios y archivos reales.

- **Formato compatible con exportacion:** requerir columnas insertables `fecha_hora`, `tipo_operacion`, `activo`, `cantidad` y `precio_entrada`; aceptar opcionales `precio_salida`, `resultado`, `stop_loss`, `take_profit`, `ratio_rr`, `nivel_confianza`, `notas`.
  - Razon: esas columnas bastan para construir `Operacion` y coinciden con los campos principales del modelo.
  - Alternativa considerada: requerir exactamente todas las cabeceras exportadas; se descarta porque `cuenta_nombre`, `operacion_id` y `screenshot` no son necesarias para crear operaciones nuevas.

- **Validacion atomica:** parsear y validar todas las filas antes de hacer `db.add_all()` y `commit()`. Si hay errores, devolver `422` con detalle por fila y no insertar nada.
  - Razon: evita estados intermedios y facilita corregir el CSV.
  - Alternativa considerada: importar filas validas y reportar fallos; se descarta porque produciria imports parciales dificiles de reconciliar.

- **Serializacion de respuesta:** devolver JSON con `created_count`, `cuenta_id` y `warnings`.
  - Razon: el cliente necesita una confirmacion simple y futuros avisos no bloqueantes, por ejemplo si falla Redis.

## Risks / Trade-offs

- CSV grandes pueden consumir memoria al validar todo el archivo -> mantener limite razonable de lectura y aislar el parser para poder pasar a streaming si aparece volumen alto.
- Fechas de hojas de calculo pueden venir en formatos variados -> aceptar ISO 8601 como formato oficial inicial y devolver errores claros por fila.
- Importar filas duplicadas puede crear duplicados reales -> dejar deduplicacion fuera de alcance y documentar que el endpoint crea nuevas operaciones.
- Redis/RQ puede fallar al encolar notas -> capturar errores, confirmar la importacion y devolver warning no bloqueante.
