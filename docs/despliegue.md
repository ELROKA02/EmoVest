# Despliegue de EmoVest

Guía general para llevar EmoVest a producción en un VPS de Hostinger del plan **"Despliega tu IA"** (que ya trae **Ollama** preinstalado de forma nativa). El objetivo es tener todo el stack corriendo en una única máquina, con `systemd` orquestando cada pieza y `nginx` como puerta de entrada.

> Esta guía cubre el plano general. Para el detalle del sistema de colas y workers, ver [redis-workers.md](redis-workers.md).

---

## 1. Componentes del sistema

EmoVest tiene cinco piezas que conviven en el mismo VPS:

| Pieza | Tecnología | Cómo se sirve |
|---|---|---|
| Frontend | React + Vite (build estático) | Archivos estáticos servidos por `nginx` |
| Backend API | FastAPI sobre `uvicorn` | Proxy inverso desde `nginx` a `127.0.0.1:8000` |
| Base de datos | MySQL | Local en el VPS, escuchando solo en `127.0.0.1` |
| Cola de trabajos | Redis + RQ worker | Ambos en `127.0.0.1`, ver [redis-workers.md](redis-workers.md) |
| Modelo de IA | Ollama (preinstalado) | `127.0.0.1:11434` |

### Diagrama lógico

```
                       Internet
                          │
                          ▼
                   ┌─────────────┐
                   │    nginx    │  443/80
                   └──────┬──────┘
                          │
              ┌───────────┴───────────┐
              ▼                       ▼
        /api/* → uvicorn          / → frontend (dist)
                  :8000              estatico
                    │
        ┌───────────┼─────────────────┐
        ▼           ▼                 ▼
     MySQL      Redis :6379       Ollama :11434
     :3306         │
                   ▼
              RQ Worker
              (python worker.py)
```

Solo `nginx` está expuesto a Internet. Todo lo demás escucha en `localhost`.

---

## 2. Pre-requisitos en el VPS

El plan "Despliega tu IA" de Hostinger ya viene con:

- Ubuntu (LTS reciente) o similar
- Ollama instalado y corriendo en `:11434`
- Al menos un modelo descargado (verificar con `ollama list`)

Lo primero que hay que hacer al entrar por SSH:

```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y python3-venv python3-pip mysql-server redis-server nginx git ufw
```

Configurar firewall (solo dejar entrar SSH y HTTP/HTTPS):

```bash
sudo ufw allow OpenSSH
sudo ufw allow 'Nginx Full'
sudo ufw enable
```

Crear un usuario de servicio dedicado para evitar correr la app como `root`:

```bash
sudo adduser --system --group --home /opt/emovest emovest
```

---

## 3. Verificar Ollama

Antes de tocar el código, comprobar que Ollama responde y tiene el modelo que usa el backend:

```bash
curl http://localhost:11434/api/tags
ollama list
```

El backend espera el modelo `clasificador_emociones_gemma4:latest` (ver [backend/routers/ia.py](../backend/routers/ia.py)). Si no está, descargarlo o crearlo desde el `Modelfile` correspondiente:

```bash
ollama pull <modelo-base>
ollama create clasificador_emociones_gemma4 -f Modelfile
```

Ollama ya viene como servicio `systemd` en estos VPS, no hay que tocar nada.

---

## 4. Base de datos MySQL

```bash
sudo mysql_secure_installation
```

Crear base de datos y usuario:

```sql
sudo mysql
> CREATE DATABASE emovest CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
> CREATE USER 'emovest'@'localhost' IDENTIFIED BY '<password-fuerte>';
> GRANT ALL PRIVILEGES ON emovest.* TO 'emovest'@'localhost';
> FLUSH PRIVILEGES;
> EXIT;
```

Confirmar que MySQL solo escucha en localhost (en `/etc/mysql/mysql.conf.d/mysqld.cnf` debe estar `bind-address = 127.0.0.1`).

Las tablas se crean ejecutando `backend/create_tables.py` desde el venv una vez que el backend esté instalado (ver siguiente sección).

---

## 5. Backend (FastAPI + uvicorn)

### Clonar y preparar entorno

```bash
sudo -u emovest -H bash
cd /opt/emovest
git clone <url-del-repo> .
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Variables de entorno

Crear `/opt/emovest/backend/.env`:

```env
# Base de datos
DATABASE_URL=mysql+pymysql://emovest:<password>@localhost:3306/emovest

# JWT / auth (poner valores reales)
JWT_SECRET_KEY=<cadena-aleatoria-larga>
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=60

# Redis y cola RQ (los valores por defecto son los correctos en local)
REDIS_URL=redis://localhost:6379/0
RQ_QUEUE_NAME=emociones
```

Ajusta los nombres de variable a las que realmente usa `backend/config.py` y los routers de auth — este `.env` es la plantilla recomendada.

### Crear tablas

```bash
python create_tables.py
```

### Servicio `systemd` para uvicorn

Archivo `/etc/systemd/system/emovest-api.service`:

```ini
[Unit]
Description=EmoVest API (FastAPI/uvicorn)
After=network.target mysql.service redis-server.service
Requires=mysql.service redis-server.service

[Service]
Type=simple
User=emovest
WorkingDirectory=/opt/emovest/backend
EnvironmentFile=/opt/emovest/backend/.env
ExecStart=/opt/emovest/backend/venv/bin/uvicorn app:app --host 127.0.0.1 --port 8000 --workers 2
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
```

Activar:

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now emovest-api
sudo systemctl status emovest-api
journalctl -u emovest-api -f
```

> Para el worker de RQ, ver [redis-workers.md §5.1](redis-workers.md#51-linux-producci%C3%B3n-y-referencia-principal). Es otro servicio `systemd` independiente.

---

## 6. Frontend (build estático)

El frontend es React + Vite. En producción se compila a archivos estáticos y se sirven directamente por `nginx`, no se ejecuta `npm run dev`.

### Build

En la máquina de desarrollo, o en el propio VPS si tiene Node:

```bash
sudo apt install -y nodejs npm    # si no lo tienes
cd /opt/emovest/frontend
npm ci
npm run build
```

Esto genera `frontend/dist/` con HTML/JS/CSS optimizados.

### Configurar la URL del backend

Antes del `npm run build`, ajustar la base URL del API en el frontend (suele estar en `frontend/src/utils/` como cliente axios o variable de entorno tipo `VITE_API_URL`). En producción debe apuntar a `/api` (mismo dominio, proxied por nginx) en vez de a `http://localhost:8000`.

---

## 7. nginx como reverse proxy

Archivo `/etc/nginx/sites-available/emovest`:

```nginx
server {
    listen 80;
    server_name tu-dominio.com;

    # Frontend estatico
    root /opt/emovest/frontend/dist;
    index index.html;

    location / {
        try_files $uri $uri/ /index.html;
    }

    # Backend API
    location /api/ {
        proxy_pass         http://127.0.0.1:8000/;
        proxy_http_version 1.1;
        proxy_set_header   Host              $host;
        proxy_set_header   X-Real-IP         $remote_addr;
        proxy_set_header   X-Forwarded-For   $proxy_add_x_forwarded_for;
        proxy_set_header   X-Forwarded-Proto $scheme;
        proxy_read_timeout 300s;
    }
}
```

Activar y recargar:

```bash
sudo ln -s /etc/nginx/sites-available/emovest /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

### HTTPS con Let's Encrypt

```bash
sudo apt install -y certbot python3-certbot-nginx
sudo certbot --nginx -d tu-dominio.com
```

Certbot se encarga de modificar el bloque `server` para añadir `listen 443 ssl` y de renovar los certificados automáticamente.

---

## 8. Resumen de servicios `systemd`

Cinco servicios deben estar habilitados (`enable --now`) para que el sistema esté completo:

| Servicio | Qué es | Origen |
|---|---|---|
| `mysql` | Base de datos | apt |
| `redis-server` | Broker de la cola | apt |
| `ollama` | Modelo de IA | preinstalado por Hostinger |
| `emovest-api` | Backend FastAPI | creado en sección 5 |
| `emovest-worker` | Worker RQ | creado en [redis-workers.md](redis-workers.md) |
| `nginx` | Reverse proxy + frontend | apt |

Comprobar todos de un vistazo:

```bash
systemctl status mysql redis-server ollama emovest-api emovest-worker nginx
```

---

## 9. Checklist de despliegue inicial

- [ ] VPS actualizado (`apt update && apt upgrade`)
- [ ] Firewall (`ufw`) configurado
- [ ] Usuario `emovest` creado
- [ ] Ollama responde y tiene el modelo descargado
- [ ] MySQL configurado, base de datos y usuario creados
- [ ] Redis arrancado y `redis-cli ping` responde
- [ ] Repo clonado en `/opt/emovest`
- [ ] `backend/.env` rellenado con valores reales
- [ ] `venv` creado e `pip install -r requirements.txt` ejecutado
- [ ] `python create_tables.py` ejecutado sin errores
- [ ] `frontend/dist/` generado con `npm run build`
- [ ] Servicios `emovest-api` y `emovest-worker` activos
- [ ] `nginx` con dominio configurado
- [ ] HTTPS activo vía certbot
- [ ] Prueba end-to-end: registrarse, iniciar sesión, crear operación con notas, verificar que aparece su `Registro_emocional`

---

## 10. Operación y mantenimiento básico

### Logs

```bash
journalctl -u emovest-api -f
journalctl -u emovest-worker -f
journalctl -u nginx -f
journalctl -u ollama -f
```

### Actualizar la aplicación

```bash
sudo -u emovest -H bash
cd /opt/emovest
git pull

# Backend
cd backend
source venv/bin/activate
pip install -r requirements.txt
# si hay cambios de modelo:
python create_tables.py
exit

# Frontend
cd /opt/emovest/frontend
npm ci
npm run build

# Reiniciar servicios afectados
sudo systemctl restart emovest-api emovest-worker
sudo systemctl reload nginx
```

### Backups

Como mínimo, programar un dump diario de MySQL:

```bash
mysqldump -u emovest -p emovest | gzip > /var/backups/emovest-$(date +%F).sql.gz
```

Idealmente, copiar esos dumps fuera del VPS (S3, Backblaze B2, otro servidor).

---

## 11. Cuándo replantear esta arquitectura

Esta guía está pensada para un **MVP en una sola máquina**. Funciona mientras todo entre en el mismo VPS sin asfixiarse. Habrá que replantearse la arquitectura cuando aparezcan estos síntomas:

- Ollama es el cuello de botella (tiempos de inferencia altos, RAM al 100%) → mover Ollama a una máquina con GPU dedicada o sustituir por una API externa.
- MySQL compite por recursos con el backend → migrar a un MySQL gestionado (RDS, PlanetScale, etc.).
- Necesitas alta disponibilidad → containerizar con Docker, replicar backend y workers detrás de un balanceador, mover Redis a un servicio gestionado.
- Despliegues frecuentes y rollbacks → introducir CI/CD (GitHub Actions desplegando vía SSH o construyendo imágenes Docker).

Mientras estés validando producto y tengas pocos usuarios, la receta de este documento es suficiente y mucho más barata de operar que cualquier alternativa.
