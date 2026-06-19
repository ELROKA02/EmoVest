## Why

Los usuarios necesitan recuperar o migrar operaciones hacia EmoVest desde hojas de calculo, backups y otras herramientas. Tras añadir exportacion CSV y orientar el proyecto a self-host open source, la importacion CSV completa la portabilidad basica de datos.

## What Changes

- Añadir un endpoint autenticado para importar operaciones desde un archivo CSV.
- Asociar las operaciones importadas a una cuenta de trading propiedad del usuario autenticado.
- Validar formato, columnas requeridas y tipos antes de insertar datos.
- Permitir importar el CSV generado por `GET /operaciones/export.csv`, ignorando columnas informativas como `cuenta_nombre` cuando no sean necesarias.
- Devolver un resumen de importacion con filas creadas y errores de validacion.
- Evitar importaciones parciales si el CSV contiene errores de validacion.

## Capabilities

### New Capabilities

- `operations-csv-import`: Importacion CSV autenticada de operaciones hacia una cuenta de trading propia.

### Modified Capabilities

- Ninguna.

## Impact

- Backend FastAPI: nuevo endpoint de importacion en el area de operaciones/exportaciones.
- Base de datos: inserciones en `Operacion`; no se requieren migraciones.
- Autenticacion: reutiliza JWT y `get_current_user`.
- Validacion: uso de `csv`, `io` y conversiones de tipos nativas de Python.
- Frontend: no requerido para esta propuesta inicial, aunque el endpoint quedara listo para una UI posterior.
- Worker/Redis: opcionalmente se podran encolar analisis emocionales para filas importadas con notas, respetando el comportamiento actual de creacion de operaciones.
