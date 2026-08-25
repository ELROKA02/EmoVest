import { copyFile, mkdir, stat } from 'node:fs/promises';
import { basename, dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const scriptDir = dirname(fileURLToPath(import.meta.url));
const tauriDir = resolve(scriptDir, '..');
const frontendDir = resolve(tauriDir, '..');
const hostTargetTriple = process.platform === 'darwin'
  ? (process.arch === 'arm64' ? 'aarch64-apple-darwin' : 'x86_64-apple-darwin')
  : 'x86_64-pc-windows-msvc';
const targetTriple = process.env.TAURI_TARGET_TRIPLE || hostTargetTriple;
const defaultName = process.platform === 'win32' ? 'emovest-backend.exe' : 'emovest-backend';
const source = resolve(
  process.env.EMOVEST_SIDECAR_SOURCE
    || resolve(frontendDir, '..', 'backend', 'dist', defaultName),
);
const extension = targetTriple.includes('windows') ? '.exe' : '';
const destination = resolve(
  tauriDir,
  'binaries',
  `emovest-backend-${targetTriple}${extension}`,
);

try {
  const sourceInfo = await stat(source);
  if (!sourceInfo.isFile()) throw new Error('no es un archivo');
} catch (error) {
  console.error(
    `No se encontró el sidecar ${basename(source)}.\n`
    + 'Construye primero el backend empaquetado o define EMOVEST_SIDECAR_SOURCE.\n'
    + `Origen esperado: ${source}\n`
    + `Detalle: ${error.message}`,
  );
  process.exit(1);
}

await mkdir(dirname(destination), { recursive: true });
await copyFile(source, destination);
console.log(`Sidecar preparado: ${destination}`);
