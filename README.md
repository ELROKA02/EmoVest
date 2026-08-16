<p align="center">
  <img src="docs/Emovest.png" alt="EmoVest" width="720">
</p>

<h1 align="center">Opera con datos. Aprende de tus decisiones.</h1>

<p align="center">
  <strong>EmoVest</strong> es el diario de trading para entender no solo qué hiciste en una operación, sino también qué pensabas y sentías al tomarla.
</p>

<p align="center">
  <a href="https://github.com/ELROKA02/EmoVest/releases/latest/download/EmoVest-Setup.exe"><img src="https://img.shields.io/badge/Descargar-para%20Windows-5b21b6?style=for-the-badge&logo=windows&logoColor=white" alt="Descargar EmoVest para Windows"></a>
  <a href="https://github.com/ELROKA02/EmoVest/releases/latest"><img src="https://img.shields.io/badge/Ver%20la%20release-0.4.2-2563eb?style=for-the-badge" alt="Ver la última release"></a>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Windows-10%2F11-0078D4" alt="Windows 10 y 11">
  <img src="https://img.shields.io/badge/Escritorio-local-6f42c1" alt="Aplicación local de escritorio">
  <img src="https://img.shields.io/badge/Licencia-MIT-2ea44f" alt="Licencia MIT">
</p>

> EmoVest no da señales ni asesoramiento financiero. Te ayuda a registrar, revisar y mejorar tu propio proceso de trading.

## El gráfico no cuenta toda la historia

Un historial tradicional muestra el precio de entrada y salida. No explica si cerraste por miedo, aumentaste el riesgo por euforia o seguiste tu plan con confianza.

EmoVest une cada operación con su contexto. Convierte tus notas, resultados y hábitos en una vista clara para que detectes patrones y tomes decisiones más conscientes en la siguiente sesión.

## Todo lo que necesitas para revisar tu operativa

| | Con EmoVest puedes |
| --- | --- |
| 📒 | Registrar operaciones LONG y SHORT, riesgo, confianza, notas y capturas en un solo diario. |
| 💸 | Calcular automáticamente el resultado neto con comisiones fijas o porcentuales por cuenta. |
| 📊 | Ver beneficio neto, win rate, drawdown, rachas y rendimiento sin depender de hojas de cálculo. |
| 🧠 | Analizar el contexto emocional de tus notas para revisar miedo, duda, euforia, confianza y neutralidad junto a cada resultado. |
| 🤖 | Elegir IA local con Ollama o modelos remotos mediante OpenRouter, de forma independiente para el análisis emocional y el chat EVA. |
| 🔄 | Importar y exportar operaciones en CSV para no perder tu histórico ni quedarte atado a una herramienta. |

## Tu trading, con tu contexto

EmoVest está hecho para quienes quieren dejar de revisar operaciones aisladas y empezar a revisar su proceso completo.

- Crea varias cuentas y configura la moneda y las comisiones de cada una.
- Guarda la imagen y las notas que explican por qué tomaste una decisión.
- Revisa el resultado bruto, la comisión aplicada y el beneficio neto de forma transparente.
- Usa EVA para conversar sobre tu diario y tus patrones de forma más natural.
- Mantén el análisis en tu equipo con Ollama o conecta OpenRouter cuando prefieras un modelo remoto.

La IA es opcional: el diario, las cuentas y las estadísticas siguen funcionando aunque no configures ningún proveedor. Si eliges IA local, el análisis se ejecuta en tu entorno; si eliges un proveedor remoto, la solicitud se procesa según la configuración y las políticas de ese proveedor.

## Empieza hoy en tres pasos

1. [Descarga EmoVest para Windows](https://github.com/ELROKA02/EmoVest/releases/latest/download/EmoVest-Setup.exe).
2. Ejecuta `EmoVest-Setup.exe` y completa el instalador.
3. Crea tu primera cuenta y registra la próxima operación con el contexto que normalmente se queda fuera de tu bróker.

No necesitas instalar Python, Docker, MySQL, Redis ni Node.js. Ollama solo es necesario si quieres utilizar modelos locales. Tus datos se guardan fuera de la carpeta de instalación y se conservan al actualizar la aplicación.

## EmoVest en acción

<video src="docs/Video_presentacion.mp4" controls preload="metadata">
  Tu navegador no puede reproducir este vídeo. Puedes verlo <a href="docs/Video_presentacion.mp4">aquí</a>.
</video>

## ¿Cómo está construido?

EmoVest es una aplicación de escritorio para Windows: Tauri integra la interfaz de React con una API local de FastAPI, SQLite guarda el diario y una cola persistente procesa las tareas de IA sin bloquearte. El instalador se actualiza de forma firmada y protege tus datos mediante copias de seguridad antes de aplicar cambios de esquema.

Si quieres conocer la arquitectura, la privacidad de la API local, las copias de seguridad, las actualizaciones o preparar un entorno de desarrollo, consulta la [guía técnica de la edición de escritorio](docs/escritorio-windows.md).

### Desarrollo local

```powershell
cd backend
python -m venv venv
.\venv\Scripts\python.exe -m pip install -r requirements.txt

cd ..
.\scripts\build-windows-sidecar.ps1

cd frontend
pnpm install
pnpm desktop:dev
```

La guía técnica incluye los requisitos completos, la creación del instalador y las comprobaciones de calidad.

## Construyamos un trading más consciente

EmoVest es open source y las contribuciones son bienvenidas. Puedes proponer una mejora, informar de un problema o colaborar en experiencia de usuario, accesibilidad, privacidad, documentación y análisis responsable.

Antes de abrir un cambio de interfaz, ejecuta `pnpm lint` y `pnpm build` desde `frontend/`.

## Licencia

EmoVest se publica bajo la [licencia MIT](LICENSE).
