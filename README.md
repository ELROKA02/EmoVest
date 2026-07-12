<p align="center">
  <img src="docs/Emovest.png" alt="EmoVest" width="720">
</p>

<h1 align="center">EmoVest — entiende a la persona detrás de cada operación</h1>

<p align="center">
  Un diario de trading libre que conecta resultados, contexto y emociones para convertir cada operación en aprendizaje.
</p>

<p align="center">
  <img src="https://img.shields.io/badge/versi%C3%B3n-0.3.1-blue" alt="Versión 0.3.1">
  <img src="https://img.shields.io/badge/licencia-MIT-2ea44f" alt="Licencia MIT">
  <img src="https://img.shields.io/badge/IA-local-6f42c1" alt="IA local">
</p>

> EmoVest no da señales ni asesoramiento financiero. Es un espacio para registrar, revisar y aprender de tu propia operativa.

## 🎬 EmoVest en acción

<video src="docs/Video_presentacion.mp4" controls preload="metadata">
  Tu navegador no puede reproducir este vídeo. Puedes verlo [aquí](docs/Video_presentacion.mp4).
</video>

---

## 🎯 El problema

Un histórico de operaciones explica qué ocurrió con el precio, pero rara vez explica qué ocurrió contigo. El miedo, la duda, la euforia o el exceso de confianza quedan en notas dispersas —cuando quedan registradas— y los mismos errores terminan pareciendo una mala racha más.

EmoVest reúne la operación y su contexto humano en el mismo lugar. Así puedes revisar patrones operativos y emocionales con evidencia, no solo con memoria.

## ⚡ Qué hace EmoVest

EmoVest es un diario de trading autoalojable para quien quiere operar con más reflexión. Registra cada operación, conserva su contexto y transforma las notas personales en indicadores emocionales orientativos mediante IA local.

| En vez de… | Con EmoVest puedes… |
|---|---|
| Revisar hojas de cálculo y notas sueltas | Ver operaciones, métricas y contexto en un mismo diario |
| Atribuir los errores a una sensación imprecisa | Comparar el resultado con la confianza y las emociones registradas |
| Entregar tus notas a servicios de terceros | Ejecutar el análisis con Ollama en tu propio entorno |

## 🧠 Cómo funciona

1. **Crea una cuenta de trading** y define su saldo y moneda.
2. **Registra la operación**: activo, entrada, salida, riesgo, resultado, nivel de confianza, notas y una captura opcional.
3. **Describe el contexto** con tus propias palabras. El análisis se procesa en segundo plano para no interrumpir tu flujo.
4. **Revisa tus patrones** con estadísticas de rendimiento, drawdown, rachas y contexto emocional.

```mermaid
flowchart LR
    A["Operación y nota"] --> B["Diario de EmoVest"]
    B --> C["Análisis emocional local"]
    B --> D["Métricas de trading"]
    C --> E["Revisión de patrones"]
    D --> E
```

El análisis emocional es una interpretación orientativa de tus notas; no sustituye tu criterio ni ofrece recomendaciones de inversión.

## 🚀 Funcionalidades

- Puedes crear y gestionar varias cuentas de trading.
- Puedes registrar operaciones LONG y SHORT con precios, cantidad, stop loss, take profit, resultado, relación riesgo-recompensa y confianza.
- Puedes añadir notas y una captura para conservar el contexto de cada decisión.
- Puedes consultar beneficio neto, win rate, drawdown, rachas y rendimiento por día.
- Puedes revisar cómo aparecen la confianza, duda, euforia, miedo y neutralidad junto a tus resultados.
- Puedes ejecutar el análisis emocional con IA local y mantener el control de tu entorno.
- Puedes consultar y editar la configuración del proveedor de IA desde la aplicación.

## 🛠️ Stack tecnológico

| Capa | Tecnología |
|---|---|
| Interfaz | React, Vite, Tailwind CSS y Recharts |
| API | FastAPI y SQLAlchemy |
| Datos | MySQL |
| Procesamiento asíncrono | Redis y RQ |
| IA emocional | Ollama y modelos locales |
| Autenticación | JWT |
| Entorno local | Docker Compose |

## ⚙️ Empieza en minutos

### Opción recomendada: Docker

Necesitas Docker Desktop o Docker Engine. Para usar el análisis emocional, instala y ejecuta Ollama en tu máquina anfitriona.

```bash
cp .env.local-server.example .env.local-server
docker compose --env-file .env.local-server -f docker-compose.local-server.yml up --build
```

Abre [http://localhost:5173](http://localhost:5173). La API y su documentación interactiva estarán disponibles en [http://localhost:8000](http://localhost:8000) y [http://localhost:8000/docs](http://localhost:8000/docs).

### Tus datos se conservan

MySQL guarda sus datos en el volumen Docker `mysql-data`: puedes detener el entorno y retomarlo después sin perder usuarios, operaciones ni análisis.

```bash
docker compose --env-file .env.local-server -f docker-compose.local-server.yml down
```

No ejecutes `down -v` salvo que quieras reiniciar el proyecto desde cero: ese comando elimina también el volumen y la base de datos local.

### Desarrollo manual

```bash
# Terminal 1: API
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python create_tables.py
uvicorn app:app --reload

# Terminal 2: worker de análisis emocional
cd backend
source venv/bin/activate
python worker.py

# Terminal 3: interfaz
cd frontend
pnpm install
pnpm dev
```

En Windows, activa el entorno con `venv\Scripts\activate`.

Si Ollama o el worker no están disponibles, la operación se guarda igualmente. El análisis emocional quedará pendiente o usará el comportamiento de respaldo configurado.

## 🏗️ Arquitectura

```mermaid
flowchart TB
    UI["React · Interfaz web"] --> API["FastAPI · API"]
    API --> DB[("MySQL")]
    API --> Q["Redis · Cola RQ"]
    Q --> W["Worker emocional"]
    W --> AI["Ollama · IA local"]
    W --> DB
```

El procesamiento emocional es asíncrono: recibir un `201` al crear una operación confirma que se ha guardado, no que el análisis ya haya terminado.

## 📚 Documentación y recursos

| Recurso | Contenido |
|---|---|
| [Guía de entorno local](LOCAL_SERVER.md) | Docker, variables y verificación local |
| [Redis y workers](docs/redis-workers.md) | Cola, worker y resolución de problemas |
| [Vídeo de presentación](docs/Video_presentacion.mp4) | Vista general del proyecto |
| [API interactiva](http://localhost:8000/docs) | OpenAPI/Swagger cuando el backend está en ejecución manual |

## 🤝 Contribuir

EmoVest mejora con personas que quieren hacer el trading más consciente y privado. Antes de abrir un cambio:

1. Revisa las [issues](../../issues) abiertas o plantea la idea en una nueva.
2. Mantén los cambios pequeños, documentados y centrados en un problema.
3. Ejecuta `pnpm lint` y `pnpm build` dentro de `frontend/` si modificas la interfaz.
4. Si tocas el flujo emocional, verifica también el worker y la cola RQ.

Las aportaciones que mejor encajan son mejoras de experiencia, accesibilidad, documentación, pruebas, privacidad y análisis responsable de patrones.

## 👥 Equipo

EmoVest es un proyecto abierto construido por una comunidad que cree que la disciplina también se puede medir. Si compartes esa visión, tus contribuciones son bienvenidas.

---

## ⚠️ Aviso

EMOVEST no proporciona asesoramiento financiero. Es una herramienta de analisis conductual y estadistico.

## 📄 Licencia

EmoVest se publica bajo [licencia MIT](LICENSE).
