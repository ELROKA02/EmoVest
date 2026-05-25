# Despliegue real en el VPS (estado actual)

Documento que recoge lo que se ha desplegado el **2026-05-23** en el VPS de OVH `164.132.42.86`. Cubre qué cambios se hicieron y por qué, cómo está montado ahora mismo, cómo operar el sistema en el día a día, y qué queda pendiente para considerarlo producción "completa".

> Este documento complementa al `despliegue.md` original (que describía el plan teórico con nginx). El despliegue real terminó usando **Caddy** en vez de nginx por simplicidad.

---

## 1. Estado actual del servidor

### URL pública

```
http://164.132.42.86
```

Sin puerto, sin paths extra. El antiguo `http://164.132.42.86:5173` (Vite dev server) ya no se usa y el puerto 5173 está cerrado en el firewall.

### Procesos corriendo (todos como servicios systemd)

| Servicio | Puerto | Visibilidad | Función |
|---|---|---|---|
| `caddy` | 80 | Pública | Sirve `dist/` y reverse-proxy a `/api/*` |
| `emovest-api` | 8000 | Solo `127.0.0.1` | FastAPI + uvicorn |
| `emovest-worker` | — | — | Worker RQ que llama a Ollama |
| `redis-server` | 6379 | Solo `127.0.0.1` | Broker de la cola |
| `ollama` | 11434 | Solo `127.0.0.1` | API local del modelo `clasificador_emociones_gemma4:latest` |

### Firewall (UFW)

Abierto al exterior: solo `22 (OpenSSH)` y `80/tcp`. El resto bloqueado.

### Arquitectura

```
Internet
   │
   ▼
┌────────────┐  puerto 80
│   Caddy    │  (sirve dist/ y proxy /api/* → uvicorn)
└─────┬──────┘
      │
      │  127.0.0.1:8000
      ▼
┌────────────┐        ┌──────────────┐
│  uvicorn   │ encola │   Redis      │
│  (FastAPI) │───────►│  (RQ broker) │
└────────────┘        └──────┬───────┘
                             │
                             ▼
                      ┌─────────────┐         ┌──────────────────┐
                      │   Worker    │────────►│  Ollama          │
                      │  (worker.py)│         │  (127.0.0.1:     │
                      └─────────────┘         │   11434)         │
                                              └──────────────────┘
```

Todo pasa por Caddy. Frontend y backend comparten el mismo origen (`http://164.132.42.86`), por lo que **no hay problema de CORS** en producción.

### Rutas en disco (servidor)

| Qué | Ruta |
|---|---|
| Repo | `/home/ubuntu/Emovest/EmoVest` |
| Build estático del frontend | `/home/ubuntu/Emovest/EmoVest/frontend/dist` |
| Variables de build del front | `/home/ubuntu/Emovest/EmoVest/frontend/.env.production` |
| Venv del backend | `/home/ubuntu/Emovest/EmoVest/backend/venv` |
| Caddyfile | `/etc/caddy/Caddyfile` |
| Unit file API | `/etc/systemd/system/emovest-api.service` |
| Unit file worker | `/etc/systemd/system/emovest-worker.service` |

---

## 2. Cambios realizados y por qué

### 2.1. Bug de CORS por barra final (`/`)

**Síntoma:** desde el navegador todos los `fetch` daban "blocked by CORS policy".

**Causa 1:** la lista `allow_origins` de FastAPI ([backend/app.py](../backend/app.py)) incluía `"http://164.132.42.86:5173/"` con barra al final. La spec de CORS exige que los orígenes **no** lleven `/` final; el navegador manda `Origin: http://164.132.42.86:5173` (sin barra) y por tanto no matcheaba.

**Causa 2:** [frontend/src/config.js](../frontend/src/config.js) tenía `API_BASE_URL = 'http://164.132.42.86:8000/'` con barra final, y todos los `fetch` hacían `` `${API_BASE_URL}/signup` `` → resultado: `http://164.132.42.86:8000//signup` (doble barra). FastAPI respondía con un 307, y los redirects 307 sobre `fetch` con `credentials` provocan que el navegador descarte cabeceras, abortando la petición.

**Fix:** quitar la barra final en ambos sitios.

### 2.2. Firewall bloqueando el puerto 8000

**Síntoma:** `curl http://164.132.42.86:8000/` desde fuera del VPS daba `Connection refused`, aunque uvicorn estaba bindeado a `0.0.0.0:8000` y `ss -tlnp` lo confirmaba.

**Causa:** UFW tenía abiertos `OpenSSH` y `5173` pero no `8000`. Desde dentro del VPS sí respondía porque UFW no aplica a tráfico local.

**Fix:** abrir 8000 mientras se diagnosticaba; posteriormente se ha cerrado al exterior porque ya no hace falta (Caddy es el único punto de entrada).

### 2.3. Frontend cacheado pedía a `localhost:8000`

**Síntoma:** tras corregir CORS, el navegador seguía haciendo `POST http://localhost:8000/signup` y Chrome lo bloqueaba con "more-private address space loopback" (Private Network Access).

**Causa:** el bundle JS de Vite que el navegador estaba cargando se generó antes del cambio de IP. Vite dev server no había recargado, o el navegador tenía caché del archivo viejo.

**Fix:** reiniciar Vite tras `git pull`, borrar `node_modules/.vite` y forzar "Empty Cache and Hard Reload" en el navegador.

### 2.4. Faltaba Redis y el worker no arrancaba

**Síntoma:** crear una operación devolvía 200, pero los registros emocionales se guardaban con todos los porcentajes a 0.

**Causa raíz:** Redis no estaba instalado en el VPS (`Connection refused` en puerto 6379), por lo que el worker no podía arrancar. Aunque hubiera arrancado, el código de `routers/ia.py:97-104` se traga silenciosamente las excepciones de Ollama y guarda ceros, así que el problema era invisible desde la web.

**Fix:**
1. `sudo apt install -y redis-server` y `systemctl enable --now redis-server`.
2. Arrancar el worker (luego automatizado como servicio systemd).

### 2.5. Migración de dev a producción real

**Estado anterior:**
- Frontend: `pnpm dev` (Vite dev server) expuesto en `:5173`.
- Backend: `uvicorn --host 0.0.0.0 --port 8000` lanzado a mano.
- Worker: `python worker.py` lanzado a mano.

**Problemas:**
- Vite dev server **no es para producción** (sin minificación, HMR, source maps, hot reload, gran consumo de RAM).
- Procesos sin gestor: si el VPS se reinicia o algo cae, no se vuelven a levantar.
- Backend expuesto directamente al exterior (mayor superficie de ataque).
- Dos puertos públicos diferentes (`5173` y `8000`) → CORS forzoso entre orígenes distintos.

**Fix aplicado:**
1. `pnpm build` → genera `frontend/dist/` con assets estáticos optimizados.
2. **Caddy** instalado y configurado como reverse proxy:
   - `/` → sirve `dist/` (frontend).
   - `/api/*` → strip prefix y reverse_proxy a `127.0.0.1:8000` (backend).
3. **systemd** para `emovest-api` y `emovest-worker` (arranque automático, restart on failure).
4. Uvicorn ahora bindea solo a `127.0.0.1`, no al exterior.
5. UFW: cierre de `5173` y `8000`, apertura solo de `80`.

### 2.6. Variable de build del frontend

Para que el bundle de producción apunte al endpoint correcto se creó `frontend/.env.production`:
```
VITE_API_URL=http://164.132.42.86/api
```
Vite la lee durante `pnpm build` y la sustituye en `import.meta.env.VITE_API_URL`. Esa variable se usa en [frontend/src/config.js](../frontend/src/config.js) como `API_BASE_URL`. En modo dev se sigue usando el fallback hardcoded.

---

## 3. Operaciones comunes (cheat sheet)

### Ver logs en vivo

```bash
sudo journalctl -u emovest-api -f
sudo journalctl -u emovest-worker -f
sudo journalctl -u caddy -f
```

### Reiniciar servicios tras cambios

```bash
sudo systemctl restart emovest-api
sudo systemctl restart emovest-worker
sudo systemctl reload caddy        # reload, no restart, es suficiente para cambios en Caddyfile
```

### Desplegar una nueva versión

Backend (cambios en código Python):
```bash
cd ~/Emovest/EmoVest
git pull
sudo systemctl restart emovest-api emovest-worker
```

Frontend (cambios en React):
```bash
cd ~/Emovest/EmoVest/frontend
git pull   # si aún no hiciste pull
pnpm install --frozen-lockfile
pnpm build
```
Caddy sirve los nuevos archivos al instante, no hace falta reload.

Si se añaden dependencias Python al backend:
```bash
cd ~/Emovest/EmoVest/backend
source venv/bin/activate
pip install -r requirements.txt
sudo systemctl restart emovest-api emovest-worker
```

### Verificar que todo funciona

```bash
# Desde el propio servidor o desde fuera:
curl -i http://164.132.42.86/         # debe devolver el HTML del frontend
curl -i http://164.132.42.86/api/     # debe devolver {"mensaje":"API funcionando"}

# Estado de servicios:
sudo systemctl status emovest-api emovest-worker caddy redis-server ollama
```

### "Gotcha" frecuente: URLs raras

La aplicación es una SPA (React Router). Cualquier URL que no exista como archivo en `dist/` cae a `index.html` y React Router intenta resolverla en el cliente. Si escribes `http://164.132.42.86/5173` (por costumbre del setup viejo), verás **solo el header** porque no hay ruta `/5173` definida en React. Usa `http://164.132.42.86` sin path para llegar al home.

---

## 4. Lo que falta para considerarlo "producción completa"

### 4.1. CRÍTICO — HTTPS con dominio propio

**Por qué:** los navegadores marcan los formularios de login en HTTP plano como "no seguro" y en algún momento bloquearán cosas (cookies SameSite, password autofill, etc.). Además, sin TLS las credenciales viajan en claro.

**Prerrequisito:** dominio comprado (DonDominio, ya pagado) y un registro DNS tipo **A** apuntando a `164.132.42.86`. Let's Encrypt **no emite certs para IPs raw**.

**Pasos resumidos:**

1. **DNS en DonDominio:** panel → zona DNS de tu dominio → añadir registro `A` con nombre `@` (o `www`) y valor `164.132.42.86`. TTL 3600. Esperar a que propague (`dig +short tudominio.com` debe devolver la IP).

2. **Caddyfile:** sustituir el bloque actual por:
   ```caddyfile
   tudominio.com {
       encode gzip

       handle_path /api/* {
           reverse_proxy 127.0.0.1:8000
       }

       handle {
           root * /home/ubuntu/Emovest/EmoVest/frontend/dist
           try_files {path} /index.html
           file_server
       }
   }

   # redirige HTTP a HTTPS
   http://tudominio.com {
       redir https://tudominio.com{uri} permanent
   }
   ```
   Caddy detecta el dominio, solicita el cert a Let's Encrypt vía ACME y lo renueva solo.

3. **Abrir el puerto 443:**
   ```bash
   sudo ufw allow 443/tcp
   ```

4. **Recargar Caddy:**
   ```bash
   sudo systemctl reload caddy
   sudo journalctl -u caddy -f    # ver cómo obtiene el certificado
   ```

5. **Actualizar el frontend** para que use el dominio:
   ```bash
   cd ~/Emovest/EmoVest/frontend
   echo "VITE_API_URL=https://tudominio.com/api" > .env.production
   pnpm build
   ```

6. **Actualizar `FRONTEND_URL` en `.env` del backend** (ver punto 4.3) para que los emails de reset password lleven al dominio correcto.

7. **Actualizar `allow_origins` en `backend/app.py`** para añadir `https://tudominio.com` (estrictamente no es necesario por ser mismo origen, pero conviene como red de seguridad).

### 4.2. IMPORTANTE — Backups de la base de datos

El motor de BD se configura vía variable de entorno `dataBase_url` (ver `backend/database.py`). Hay que confirmar qué motor se está usando en el servidor (probablemente MySQL según `despliegue.md`).

**Si es MySQL:**
```bash
sudo apt install -y mysql-client       # si no está
mkdir -p ~/backups
mysqldump -u <usuario> -p<pass> <db> | gzip > ~/backups/emovest-$(date +%F).sql.gz
```
Programar con cron (`crontab -e`):
```
0 3 * * * mysqldump -u USER -pPASS DB | gzip > ~/backups/emovest-$(date +\%F).sql.gz && find ~/backups -name "emovest-*.sql.gz" -mtime +30 -delete
```
Esto deja un backup diario a las 3 AM y borra los de más de 30 días.

**Mejor todavía:** copiar el backup fuera del propio VPS (rsync a otro servidor, subir a S3/Backblaze, etc.) para no perderlo si el VPS muere.

### 4.3. IMPORTANTE — `.env` del backend

Verificar que existe `/home/ubuntu/Emovest/EmoVest/backend/.env` con al menos:

```env
dataBase_url=mysql+pymysql://usuario:pass@127.0.0.1/emovest
SECRET_KEY=<una-cadena-aleatoria-larga-y-secreta>
FRONTEND_URL=http://164.132.42.86

# Opcional (para emails de reset password):
EMAIL_SMTP_SERVER=smtp.gmail.com
EMAIL_SMTP_PORT=465
EMAIL_USERNAME=tu-email@gmail.com
EMAIL_PASSWORD=<app-password-de-google>
EMAIL_FROM=tu-email@gmail.com
EMAIL_FROM_NAME=EmoVest
```

Permisos restrictivos:
```bash
chmod 600 ~/Emovest/EmoVest/backend/.env
```

Tras cualquier cambio:
```bash
sudo systemctl restart emovest-api emovest-worker
```

> **`SECRET_KEY` debe ser único por entorno y nunca commitearse al repo.** Si actualmente está hardcoded o reutilizado, generar uno nuevo:
> ```bash
> python -c "import secrets; print(secrets.token_urlsafe(64))"
> ```
> Cambiar `SECRET_KEY` invalida los JWT existentes (todos los usuarios tendrán que volver a iniciar sesión).

### 4.4. RECOMENDABLE — Configurar SMTP para reset password

El endpoint de "olvidé mi contraseña" ([backend/routers/auth.py:88](../backend/routers/auth.py)) requiere `EMAIL_SMTP_SERVER`, `EMAIL_USERNAME`, `EMAIL_PASSWORD` y `EMAIL_FROM`. Si faltan, el endpoint lanza error y los emails no se envían.

Para Gmail: hay que crear una **App Password** en la cuenta de Google (Settings → Security → 2-Step Verification → App passwords) — no funciona la contraseña normal. Configurar como en 4.3.

### 4.5. RECOMENDABLE — Limitar tamaño de logs de systemd

Por defecto journald acumula logs sin límite y puede llenar el disco con el tiempo. Editar `/etc/systemd/journald.conf`:
```
SystemMaxUse=500M
```
Y `sudo systemctl restart systemd-journald`.

### 4.6. RECOMENDABLE — Ruta catch-all en React Router

Cuando alguien visita una URL inexistente (ej: `http://164.132.42.86/cualquier-cosa`), Caddy sirve `index.html` (correcto para SPA) pero React Router no encuentra ruta y se ve la página solo con el header. Añadir una ruta `path="*"` que muestre un "404 - Página no encontrada" o redirija a `/`.

### 4.7. OPCIONAL — Reboot del VPS para aplicar kernel pendiente

Durante `apt install` aparecía:
```
Pending kernel upgrade!
Running kernel version: 6.8.0-106-generic
Diagnostics: ... not the expected kernel version 6.8.0-117-generic.
```
No bloquea nada, pero conviene reiniciar el VPS en algún momento para aplicar los parches de seguridad del kernel:
```bash
sudo reboot
```
Todos los servicios systemd se levantarán solos tras el reboot. Verificar con `systemctl status emovest-api emovest-worker caddy` que están `active (running)`.

---

## 5. Checklist de salud rápido

Si algo va mal, en este orden:

```bash
# 1. ¿Servicios vivos?
sudo systemctl status emovest-api emovest-worker caddy redis-server ollama

# 2. ¿Hay errores recientes?
sudo journalctl -u emovest-api -n 50 --no-pager
sudo journalctl -u emovest-worker -n 50 --no-pager
sudo journalctl -u caddy -n 50 --no-pager

# 3. ¿Puertos correctos?
sudo ss -tlnp | grep -E ":80|:8000|:6379|:11434"

# 4. ¿Firewall sensato?
sudo ufw status

# 5. ¿Conectividad end-to-end?
curl -s http://127.0.0.1/api/ | head -1
curl -s http://164.132.42.86/api/ | head -1   # desde fuera

# 6. ¿Cola de RQ procesando?
redis-cli -h 127.0.0.1 llen rq:queue:emociones   # debería tender a 0
```
