# Instalación y avisos de seguridad

Esta guía explica los avisos que pueden aparecer al abrir EmoVest descargado desde las [releases de GitHub](https://github.com/ELROKA02/EmoVest/releases). Descarga siempre la aplicación desde esa página oficial.

## macOS: abrir EmoVest cuando Gatekeeper lo bloquea

Actualmente EmoVest se distribuye fuera de la Mac App Store y la versión publicada no está firmada ni notarizada por Apple. Por eso macOS puede bloquear la aplicación la primera vez que intentas abrirla mediante Gatekeeper.

Este aviso no significa por sí solo que EmoVest contenga malware: indica que macOS no puede confirmar la identidad de un desarrollador mediante el programa de firma de Apple. EmoVest es open source y su código se puede revisar en este repositorio antes de ejecutarlo.

### Método recomendado

1. Descarga EmoVest desde la sección [Releases de GitHub](https://github.com/ELROKA02/EmoVest/releases).
2. Abre el archivo descargado y mueve `EmoVest.app` a la carpeta **Aplicaciones** si la descarga lo requiere.
3. Intenta abrir EmoVest normalmente.
4. Si macOS lo bloquea, abre **Ajustes del Sistema**.
5. Entra en **Privacidad y seguridad**.
6. Busca el aviso que indica que EmoVest fue bloqueado.
7. Pulsa **Abrir igualmente**.
8. Confirma la acción si macOS solicita tu contraseña o Touch ID.
9. Vuelve a abrir EmoVest.

Normalmente solo tendrás que hacer esto la primera vez que abras esa copia de la aplicación.

### Solución avanzada: Terminal

Usa esta alternativa únicamente si el método anterior no funciona. Antes de ejecutar el comando, comprueba que EmoVest está en la carpeta **Aplicaciones** y que procede de la release oficial de GitHub.

En Terminal, ejecuta:

```bash
xattr -dr com.apple.quarantine /Applications/EmoVest.app
```

Este comando elimina de forma recursiva el atributo `com.apple.quarantine` **únicamente** de `/Applications/EmoVest.app`. Ese atributo es el que macOS añade a muchos archivos descargados de Internet para que Gatekeeper pueda pedir una confirmación antes de abrirlos. No desactiva Gatekeeper ni modifica la protección de otras aplicaciones o del sistema.

Después, abre EmoVest con:

```bash
open /Applications/EmoVest.app
```

No recomendamos desactivar globalmente las protecciones de seguridad de macOS.

## Windows: aviso de SmartScreen o "editor desconocido"

En Windows, al ejecutar el instalador descargado desde GitHub, SmartScreen puede mostrar un aviso como "Windows protegió su PC" o identificar al editor como desconocido. Al igual que en macOS, el aviso no es por sí mismo una detección de malware: Windows no puede vincular el archivo a una identidad verificada cuando el instalador no incluye una firma Authenticode reconocida o todavía no ha acumulado reputación en SmartScreen.

Las firmas de Windows (Authenticode) y macOS (Apple Developer ID y notarización) requieren certificados, verificación de identidad y procesos específicos de cada plataforma. EmoVest todavía no usa esas credenciales para la distribución pública actual. Por ese motivo el sistema puede parecer desconfiar de la aplicación aunque el código sea público y revisable.

Para reducir riesgos:

- Descarga EmoVest solo desde las [Releases oficiales de GitHub](https://github.com/ELROKA02/EmoVest/releases).
- Revisa el código fuente en el repositorio antes de ejecutar la aplicación si quieres verificar cómo funciona.
- No desactives de forma global las protecciones de macOS o Windows para instalar EmoVest.

La ausencia actual de firma/notarización explica estos avisos; no constituye por sí misma una conclusión sobre la seguridad del código. Si el sistema muestra una alerta distinta o sospechas que el archivo no procede de la release oficial, no lo ejecutes y abre una incidencia en el repositorio.
