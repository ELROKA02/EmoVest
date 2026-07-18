## 1. Backend Endpoint

- [x] 1.1 Añadir `POST /operaciones/import.csv` al router CSV existente o a un router backend equivalente con autenticacion mediante `get_current_user`.
- [x] 1.2 Definir entrada `multipart/form-data` con `file: UploadFile` y `cuenta_id` requerido.
- [x] 1.3 Documentar respuestas OpenAPI para `200`, `401`, `404` y `422`.

## 2. Account Ownership

- [x] 2.1 Consultar `Cuenta_Trading` por `cuenta_id` y `current_user.id`.
- [x] 2.2 Si la cuenta no existe o no pertenece al usuario, devolver `404` antes de procesar el CSV.
- [x] 2.3 Ignorar columnas `cuenta_id` y `cuenta_nombre` del CSV para asignacion de propiedad.

## 3. CSV Parsing And Validation

- [x] 3.1 Leer el archivo subido como texto UTF-8 y parsearlo con `csv.DictReader`.
- [x] 3.2 Requerir cabeceras `fecha_hora`, `tipo_operacion`, `activo`, `cantidad` y `precio_entrada`.
- [x] 3.3 Aceptar columnas opcionales `precio_salida`, `resultado`, `stop_loss`, `take_profit`, `ratio_rr`, `nivel_confianza` y `notas`.
- [x] 3.4 Ignorar columnas no insertables de exportacion: `operacion_id`, `cuenta_id`, `cuenta_nombre` y `screenshot`.
- [x] 3.5 Convertir `fecha_hora` desde ISO 8601, decimales con `Decimal`, `nivel_confianza` con `int` y celdas opcionales vacias como `None`.
- [x] 3.6 Validar `tipo_operacion` como `LONG` o `SHORT` y campos requeridos no vacios.
- [x] 3.7 Acumular errores por fila y devolver `422` sin insertar nada si existe cualquier error.

## 4. Atomic Insert And Side Effects

- [x] 4.1 Crear instancias `Operacion` usando siempre la cuenta destino validada.
- [x] 4.2 Insertar todas las operaciones en una transaccion y hacer rollback si falla el commit.
- [x] 4.3 Devolver JSON con `created_count`, `cuenta_id` y `warnings`.
- [x] 4.4 Encolar analisis emocional para operaciones importadas con `notas` tras commit exitoso.
- [x] 4.5 Si Redis/RQ falla al encolar, mantener la importacion creada y añadir warning no bloqueante.

## 5. Verification

- [x] 5.1 Verificar que una request sin token a `/operaciones/import.csv` no crea datos.
- [x] 5.2 Verificar importacion correcta en una cuenta propia con CSV compatible con la exportacion.
- [x] 5.3 Verificar que una cuenta inexistente o ajena devuelve `404` y no lee/importa datos.
- [x] 5.4 Verificar que faltan cabeceras requeridas devuelve `422` y no crea datos.
- [x] 5.5 Verificar que valores invalidos por fila devuelven `422` con detalle y no crean datos.
- [x] 5.6 Verificar que columnas de cuenta del CSV no sobreescriben la cuenta destino.
- [x] 5.7 Ejecutar comprobacion backend disponible (`uvicorn app:app --reload` o import equivalente) y validar que OpenAPI incluye el endpoint.
