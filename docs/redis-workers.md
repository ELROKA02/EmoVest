# Sistema de colas: Redis + RQ + Workers

Documento técnico que explica cómo funciona el procesamiento en segundo plano del análisis emocional en EmoVest, qué procesos hace falta tener vivos y cómo arrancarlos en Linux y macOS.

---

## 1. Qué problema resuelve

Cuando un usuario crea una operación con notas, el backend tiene que pedirle a Ollama que clasifique el texto en cinco emociones (`confianza`, `duda`, `euforia`, `miedo`, `neutral`). Esa llamada al modelo puede tardar varios segundos.

Si el endpoint hiciera esa clasificación de forma síncrona, el usuario se quedaría con la pantalla bloqueada esperando a Ollama. La solución es **encolar el análisis** y devolver al usuario el `201 Created` inmediatamente. Otro proceso (el *worker*) consume la cola y ejecuta el análisis en su tiempo.

---

## 2. Arquitectura

Tres procesos cooperando vía Redis:

```
┌──────────────────┐       enqueue        ┌──────────────────┐
│  Backend FastAPI │  ─────────────────▶  │      Redis       │
│  (uvicorn)       │                      │   (cola RQ)      │
└──────────────────┘                      └──────────────────┘
                                                    │
                                                    │ pop
                                                    ▼
                                          ┌──────────────────┐
                                          │   Worker (RQ)    │
                                          │   worker.py      │
                                          └────────┬─────────┘
                                                   │
                                                   │ chat()
                                                   ▼
                                          ┌──────────────────┐
                                          │     Ollama       │
                                          │  :11434          │
                                          └──────────────────┘
                                                   │
                                                   │ guardar
                                                   ▼
                                          ┌──────────────────┐
                                          │   MySQL          │
                                          │ Registro_emoc... │
                                          └──────────────────┘
```

Mientras los **tres procesos del medio** (backend, redis, worker) y **Ollama** estén vivos, el sistema funciona.

---

## 3. Componentes en el código

| Archivo | Rol |
|---|---|
| `backend/config.py` | Lee `REDIS_URL`, nombre de cola, timeouts y políticas de reintento desde `.env`. |
| `backend/rq_queue.py` | Construye la conexión a Redis y la cola `emociones`. Expone `enqueue_emociones_job()`. |
| `backend/jobs/emociones.py` | Función que ejecuta el worker para cada job: abre sesión de BD, llama a Ollama, guarda el `Registro_emocional`. |
| `backend/worker.py` | Proceso del worker. Usa `SimpleWorker` (sin `fork()`). |
| `backend/routers/operaciones.py` | El endpoint `POST /cuentas/{id}/operaciones` llama a `enqueue_emociones_job()` después de guardar la operación si hay `notas`. |
| `backend/routers/ia.py` | Lógica de clasificación con Ollama y persistencia del `Registro_emocional`. |

### Por qué `SimpleWorker` y no `Worker`

RQ por defecto usa `Worker`, que hace `fork()` por cada job para aislarlo en un *work-horse*. En **macOS** esto provoca un crash del runtime de Objective-C cuando el proceso padre ya ha cargado librerías nativas (Ollama, `requests`/SSL, etc.):

```
+[NSNumber initialize] may have been in progress in another thread when fork() was called.
```

`SimpleWorker` ejecuta los jobs **en el mismo proceso**, sin `fork()`, así que el problema desaparece. La contrapartida es que pierdes el aislamiento entre jobs y los timeouts duros: si Ollama se cuelga, el worker queda bloqueado en ese job hasta que lo reinicies.

Para producción en **Linux**, donde `fork()` funciona bien, podríamos volver a `Worker` para tener aislamiento real. Hoy mantenemos `SimpleWorker` en ambos entornos por simplicidad.

---

## 4. Configuración

Variables que lee `backend/config.py` (con sus valores por defecto):

| Variable | Por defecto | Descripción |
|---|---|---|
| `REDIS_URL` | `redis://localhost:6379/0` | URL de conexión a Redis. |
| `RQ_QUEUE_NAME` | `emociones` | Nombre de la cola. |
| `RQ_DEFAULT_TIMEOUT` | `180` | Segundos máximos por job. |
| `RQ_RESULT_TTL` | `3600` | Segundos que se conservan resultados de jobs OK. |
| `RQ_FAILURE_TTL` | `86400` | Segundos que se conservan jobs fallidos para inspección. |
| `RQ_RETRY_MAX` | `3` | Reintentos antes de marcar el job como fallido. |
| `RQ_RETRY_INTERVALS` | `[2, 4, 8]` | Espera entre reintentos en segundos. |

En desarrollo local con Redis en la misma máquina no hace falta tocar nada. En producción se sobreescriben en `backend/.env`.

---

## 5. Cómo arrancar el sistema

### 5.1 Linux (producción y referencia principal)

#### Instalación de Redis

```bash
sudo apt update
sudo apt install -y redis-server
sudo systemctl enable --now redis-server
redis-cli ping        # debe responder PONG
```

Por defecto escucha en `127.0.0.1:6379`, que es justo lo que queremos (sin exponer a Internet).

#### Worker como servicio `systemd`

Crear `/etc/systemd/system/emovest-worker.service`:

```ini
[Unit]
Description=EmoVest RQ worker (analisis emocional)
After=network.target redis-server.service
Requires=redis-server.service

[Service]
Type=simple
User=emovest
WorkingDirectory=/opt/emovest/backend
EnvironmentFile=/opt/emovest/backend/.env
ExecStart=/opt/emovest/backend/venv/bin/python worker.py
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
```

Activar:

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now emovest-worker
sudo systemctl status emovest-worker
journalctl -u emovest-worker -f       # ver logs en vivo
```

Con esto, el worker arranca al iniciar el servidor, se reinicia solo si cae y queda integrado en los logs del sistema.

#### Verificación

```bash
# 1. Redis vivo
redis-cli ping

# 2. Worker escuchando
sudo systemctl status emovest-worker
# debe verse: "Worker escuchando cola: emociones"

# 3. Crear una operacion con notas desde el frontend o curl
# 4. Comprobar la BD
mysql -u emovest -p emovest -e "SELECT id, id_operacion, fecha_hora FROM Registro_emocional ORDER BY id DESC LIMIT 5;"
```

### 5.2 macOS (desarrollo local)

#### Instalación de Redis

```bash
brew install redis
brew services start redis     # arranca al login
redis-cli ping                # debe responder PONG
```

Para parar: `brew services stop redis`.

#### Arrancar el worker manualmente

En una terminal aparte del backend:

```bash
cd backend
source venv/bin/activate
python worker.py
```

Salida esperada:

```
Worker escuchando cola: emociones
```

Déjala abierta. Cada job ejecutado imprime su id y resultado en esa terminal.

#### Resumen de procesos en local

| Terminal | Proceso |
|---|---|
| 1 | `brew services start redis` (servicio en background) |
| 2 | `python worker.py` |
| 3 | `uvicorn app:app --reload` |
| 4 | `npm run dev` (frontend) |

---

## 6. Cómo se comporta ante fallos

El sistema está pensado para **no romper el endpoint** aunque la cola falle.

| Escenario | Qué pasa |
|---|---|
| Redis caído al crear operación | `enqueue_emociones_job` lanza excepción → el `try/except` de [operaciones.py](../backend/routers/operaciones.py) la captura y solo imprime un *warning*. La operación se guarda igualmente. **No se crea `Registro_emocional`.** |
| Worker caído | El job se queda en cola. Cuando vuelva el worker, lo procesa. |
| Ollama caído | El job entra reintentos (`RQ_RETRY_MAX=3`, esperas `2s, 4s, 8s`). Si todos fallan, `guardar_registro_emocional` cae al fallback de valores en `0` y guarda el registro con ceros (ver [routers/ia.py](../backend/routers/ia.py)). |
| Job tarda > 180 s | RQ lo marca como timeout. Como usamos `SimpleWorker`, el timeout es *soft*: si Ollama no responde nunca, el worker queda bloqueado hasta reiniciarlo. |

---

## 7. Troubleshooting

### "La operación se guarda pero no aparece análisis emocional"

Es el síntoma más común. Comprueba en este orden:

```bash
# 1. ¿Redis está arriba?
redis-cli ping
# si no responde PONG: arrancar redis (ver seccion 5)

# 2. ¿El worker está corriendo?
# Linux:
sudo systemctl status emovest-worker
# macOS:
ps aux | grep worker.py | grep -v grep

# 3. ¿Hay jobs encolados o fallidos?
redis-cli LLEN rq:queue:emociones
redis-cli LLEN rq:queue:failed
```

### Worker crashea en macOS con `objc[xxx]: ... fork() ... Crashing instead`

Estás usando `Worker` en vez de `SimpleWorker`. Verifica que [backend/worker.py](../backend/worker.py) importa `SimpleWorker`. Como atajo temporal:

```bash
export OBJC_DISABLE_INITIALIZE_FORK_SAFETY=YES
python worker.py
```

### El worker arranca pero no procesa jobs

Confirma que está escuchando la cola correcta:

```
Worker escuchando cola: emociones
```

Si dice otro nombre, revisa `RQ_QUEUE_NAME` en `.env` (debe coincidir con el que usa el productor).

### Job atascado, no termina

Mata el worker y reinícialo. Si pasa repetidamente, suele ser Ollama colgado:

```bash
curl http://localhost:11434/api/tags     # debe responder JSON con la lista de modelos
```

Si no responde, reinicia Ollama.

### Inspeccionar jobs fallidos

RQ guarda los fallos durante `RQ_FAILURE_TTL` segundos. Para verlos:

```bash
pip install rq-dashboard
rq-dashboard -u redis://localhost:6379/0
# abrir http://localhost:9181
```

O directamente desde una shell de Python con `rq.registry.FailedJobRegistry`.

---

## 8. Escalado

Cuando un solo worker no llegue, lanzar más workers consumiendo la **misma cola** es trivial: cada uno es un proceso `python worker.py` independiente, y RQ se encarga de que un job lo coja solo uno.

En `systemd` se puede usar una unidad parametrizada (`emovest-worker@.service`) y arrancar `emovest-worker@1`, `emovest-worker@2`, etc.

El cuello de botella real cuando escales no será RQ, será **Ollama**: un único proceso, modelos cargados en RAM, sin paralelismo nativo. Antes de añadir más workers conviene medir si Ollama puede atender más concurrencia o si toca moverlo a una máquina con GPU dedicada.
