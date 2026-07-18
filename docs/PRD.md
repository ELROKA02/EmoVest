# PRD EmoVest Open Source

## Resumen

EmoVest es una aplicacion open source y gratuita para autohospedar un diario de trading con analisis emocional local. El producto se ejecuta en el entorno del usuario y no depende de una instancia central operada por el equipo.

## Objetivos

- Permitir que cualquier persona instale EmoVest sin pagar licencias.
- Mantener los datos de trading y notas emocionales en infraestructura propia.
- Registrar operaciones, cuentas de trading, capturas y estadisticas mensuales.
- Procesar el analisis emocional de forma asincrona con Redis/RQ y Ollama local.
- Evitar dependencias de correo transaccional en la version inicial open source.

## Usuarios

- Traders que quieren revisar su proceso con datos propios.
- Estudiantes o equipos pequenos que prefieren una herramienta local.
- Desarrolladores que quieran adaptar el producto a su flujo.

## Funcionalidad principal

- Registro e inicio de sesion local con email como identificador.
- CRUD de cuentas de trading.
- CRUD de operaciones con LONG/SHORT, precios, resultado, notas, confianza y captura opcional.
- Estadisticas mensuales de rendimiento.
- Analisis emocional asincrono cuando una operacion incluye notas.
- Configuracion por variables de entorno para base de datos, Redis, CORS, Ollama e imagenes.

## Fuera de alcance inicial

- Correo transaccional.
- Recuperacion de contrasena por email.
- Pasarela de pagos.
- Restricciones por plan.
- Instancia SaaS oficial.

## Requisitos tecnicos

- Frontend React + Vite gestionado con `pnpm`.
- Backend FastAPI + SQLAlchemy.
- MySQL como base de datos.
- Redis + RQ para jobs.
- Ollama local para clasificacion emocional.
- Licencia MIT.

## Criterios de aceptacion

- Una persona puede clonar el repo, copiar plantillas `.env` y levantar la app local.
- Signup y login funcionan sin correo transaccional ni caducidad de suscripcion.
- Crear una operacion no depende de que Ollama responda inmediatamente.
- La documentacion principal no presenta EmoVest como prueba temporal ni producto de pago.
