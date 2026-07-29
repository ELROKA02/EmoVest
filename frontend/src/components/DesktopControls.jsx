import { useCallback, useEffect, useState } from 'react';
import { invoke } from '@tauri-apps/api/core';
import { listen } from '@tauri-apps/api/event';
import { apiFetch, getRuntimeApiInfo, isDesktopRuntime } from '../config';

const idleUpdate = {
  phase: 'idle',
  available: false,
  canDownload: false,
  version: null,
  notes: null,
  progress: null,
  message: '',
};

const aiStateLabels = {
  available: 'Disponible',
  not_installed: 'No instalado',
  service_stopped: 'Servicio detenido',
  model_missing: 'Modelo ausente',
  disabled: 'Desactivada',
  unreachable: 'No accesible',
};

const DesktopControls = () => {
  const [open, setOpen] = useState(false);
  const [diagnostics, setDiagnostics] = useState(null);
  const [diagnosticsError, setDiagnosticsError] = useState('');
  const [backup, setBackup] = useState({ phase: 'idle', message: '' });
  const [update, setUpdate] = useState(idleUpdate);
  const [aiStatus, setAiStatus] = useState({
    phase: 'idle',
    statuses: null,
    message: '',
  });

  const refreshDiagnostics = useCallback(async () => {
    if (!isDesktopRuntime()) return;
    setDiagnosticsError('');
    try {
      setDiagnostics(await invoke('desktop_diagnostics'));
    } catch (error) {
      setDiagnosticsError(String(error));
    }
  }, []);

  const refreshAiStatus = useCallback(async () => {
    const token = sessionStorage.getItem('token');
    if (!token) {
      setAiStatus({
        phase: 'auth-required',
        statuses: null,
        message: 'El estado de la IA estará disponible al iniciar sesión.',
      });
      return;
    }

    setAiStatus((current) => ({ ...current, phase: 'loading', message: '' }));
    try {
      const response = await apiFetch('/ia/status', {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!response.ok) {
        throw new Error(response.status === 401
          ? 'La sesión ha caducado.'
          : `La comprobación respondió HTTP ${response.status}.`);
      }
      const result = await response.json();
      setAiStatus({
        phase: 'ready',
        statuses: result.statuses || {},
        message: '',
      });
    } catch (error) {
      setAiStatus({
        phase: 'error',
        statuses: null,
        message: `No se pudo comprobar la IA: ${String(error)}`,
      });
    }
  }, []);

  const checkForUpdates = useCallback(async ({ silent = false } = {}) => {
    if (!isDesktopRuntime()) return;
    setUpdate((current) => ({
      ...current,
      phase: 'checking',
      message: silent ? '' : 'Buscando actualizaciones…',
    }));
    try {
      const result = await invoke('check_for_update');
      setUpdate({
        ...idleUpdate,
        ...result,
        phase: result.available && result.canDownload
          ? 'available'
          : result.available
            ? 'blocked'
            : 'idle',
        message: result.message || (result.available ? '' : 'EmoVest está actualizado.'),
      });
    } catch (error) {
      setUpdate({
        ...idleUpdate,
        phase: 'error',
        message: `No se pudo comprobar: ${String(error)}`,
      });
    }
  }, []);

  useEffect(() => {
    if (!isDesktopRuntime()) return undefined;
    const timeoutId = window.setTimeout(() => {
      void checkForUpdates({ silent: true });
    }, 2500);
    return () => window.clearTimeout(timeoutId);
  }, [checkForUpdates]);

  useEffect(() => {
    if (!isDesktopRuntime()) return undefined;
    let unlisten = null;
    void listen('desktop-update-progress', ({ payload }) => {
      setUpdate((current) => ({
        ...current,
        progress: payload?.percentage ?? current.progress,
        message: payload?.percentage == null
          ? 'Descargando actualización…'
          : `Descargando… ${payload.percentage}%`,
      }));
    }).then((cleanup) => {
      unlisten = cleanup;
    });
    return () => unlisten?.();
  }, []);

  const createBackup = async () => {
    setBackup({ phase: 'running', message: 'Creando copia de seguridad…' });
    try {
      const path = await invoke('create_desktop_backup');
      setBackup({ phase: 'done', message: `Copia guardada en: ${path}` });
    } catch (error) {
      setBackup({ phase: 'error', message: `No se pudo crear la copia: ${String(error)}` });
    }
  };

  const downloadUpdate = async () => {
    setUpdate((current) => ({ ...current, phase: 'downloading', progress: 0, message: 'Descargando…' }));
    try {
      const result = await invoke('download_update');
      setUpdate((current) => ({
        ...current,
        ...result,
        phase: 'downloaded',
        progress: 100,
        message: 'Actualización lista para instalar.',
      }));
    } catch (error) {
      setUpdate((current) => ({
        ...current,
        phase: 'error',
        message: `La descarga se interrumpió: ${String(error)}`,
      }));
    }
  };

  const installUpdate = async () => {
    setUpdate((current) => ({ ...current, phase: 'installing', message: 'Preparando copia de seguridad…' }));
    try {
      await invoke('install_downloaded_update');
    } catch (error) {
      setUpdate((current) => ({
        ...current,
        phase: 'error',
        message: `No se pudo instalar: ${String(error)}`,
      }));
    }
  };

  if (!isDesktopRuntime()) return null;

  const runtime = getRuntimeApiInfo();

  return (
    <>
      <button
        type="button"
        onClick={() => {
          setOpen(true);
          void refreshDiagnostics();
          void refreshAiStatus();
        }}
        className="fixed bottom-4 right-4 z-[80] rounded-full border border-white/15 bg-[#111827]/95 p-3 text-slate-200 shadow-xl transition hover:border-blue-400/60 hover:text-white"
        aria-label="Abrir diagnóstico de EmoVest"
        title="Diagnóstico y actualizaciones"
      >
        <svg className="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.8" d="M12 15.5A3.5 3.5 0 1 0 12 8a3.5 3.5 0 0 0 0 7.5ZM19.4 15a1.7 1.7 0 0 0 .3 1.9l.1.1-2.8 2.8-.1-.1a1.7 1.7 0 0 0-1.9-.3 1.7 1.7 0 0 0-1 1.6v.2h-4V21a1.7 1.7 0 0 0-1-1.6 1.7 1.7 0 0 0-1.9.3l-.1.1L4.2 17l.1-.1a1.7 1.7 0 0 0 .3-1.9A1.7 1.7 0 0 0 3 14H2.8v-4H3a1.7 1.7 0 0 0 1.6-1 1.7 1.7 0 0 0-.3-1.9L4.2 7 7 4.2l.1.1a1.7 1.7 0 0 0 1.9.3A1.7 1.7 0 0 0 10 3v-.2h4V3a1.7 1.7 0 0 0 1 1.6 1.7 1.7 0 0 0 1.9-.3l.1-.1L19.8 7l-.1.1a1.7 1.7 0 0 0-.3 1.9 1.7 1.7 0 0 0 1.6 1h.2v4H21a1.7 1.7 0 0 0-1.6 1Z" />
        </svg>
      </button>

      {open && (
        <div className="fixed inset-0 z-[100] flex items-center justify-center bg-black/70 p-4 backdrop-blur-sm">
          <section className="max-h-[85vh] w-full max-w-xl overflow-auto rounded-2xl border border-white/10 bg-[#0b1220] p-6 text-white shadow-2xl">
            <div className="flex items-start justify-between gap-4">
              <div>
                <h2 className="text-xl font-semibold">Diagnóstico de escritorio</h2>
                <p className="mt-1 text-xs text-slate-400">Versión {runtime.appVersion || 'desconocida'}</p>
              </div>
              <button type="button" onClick={() => setOpen(false)} className="text-2xl text-slate-400 hover:text-white">×</button>
            </div>

            <div className="mt-6 rounded-xl border border-white/10 bg-white/[0.03] p-4 text-sm">
              <div className="flex items-center justify-between gap-3">
                <span className="font-medium">Servicio local</span>
                <button type="button" onClick={() => void refreshDiagnostics()} className="text-xs text-blue-300 hover:text-blue-200">
                  Actualizar estado
                </button>
              </div>
              {diagnosticsError ? (
                <p className="mt-3 text-red-300">{diagnosticsError}</p>
              ) : (
                <dl className="mt-3 grid grid-cols-[auto_1fr] gap-x-4 gap-y-2 text-xs text-slate-300">
                  <dt>API</dt><dd className="truncate">{runtime.apiBaseUrl}</dd>
                  <dt>Estado</dt><dd>{diagnostics?.healthy ? 'Disponible' : 'Comprobando…'}</dd>
                  <dt>PID</dt><dd>{diagnostics?.sidecarPid || '—'}</dd>
                  <dt>Esquema</dt><dd>{diagnostics?.schemaRevision || '—'}</dd>
                  <dt>Cola</dt>
                  <dd>
                    {diagnostics?.jobs
                      ? `${diagnostics.jobs.pending || 0} pendientes · ${diagnostics.jobs.running || 0} ejecutando · ${diagnostics.jobs.failed || 0} fallidos`
                      : '—'}
                  </dd>
                  <dt>Datos</dt><dd className="break-all">{diagnostics?.dataDir || '—'}</dd>
                  <dt>Logs</dt><dd className="break-all">{diagnostics?.logDir || '—'}</dd>
                </dl>
              )}
            </div>

            <div className="mt-4 rounded-xl border border-white/10 bg-white/[0.03] p-4 text-sm">
              <div className="flex items-center justify-between gap-3">
                <div>
                  <p className="font-medium">IA local opcional</p>
                  <p className="mt-1 text-xs text-slate-400">EmoVest guarda operaciones aunque la IA no esté disponible.</p>
                </div>
                <button
                  type="button"
                  disabled={aiStatus.phase === 'loading'}
                  onClick={() => void refreshAiStatus()}
                  className="text-xs text-blue-300 hover:text-blue-200 disabled:opacity-50"
                >
                  Comprobar
                </button>
              </div>
              {aiStatus.statuses ? (
                <div className="mt-3 space-y-3 text-xs">
                  {[
                    ['emotion', 'Análisis emocional'],
                    ['chat', 'Chat'],
                  ].map(([key, label]) => {
                    const item = aiStatus.statuses[key];
                    const state = item?.status?.state || 'unreachable';
                    return (
                      <div key={key} className="rounded-lg border border-white/10 p-3">
                        <div className="flex items-center justify-between gap-3">
                          <span className="font-medium text-slate-200">{label}</span>
                          <span className="text-slate-300">{aiStateLabels[state] || aiStateLabels.unreachable}</span>
                        </div>
                        <p className="mt-1 text-slate-400">
                          {item?.status?.message || 'No se recibió información del proveedor.'}
                        </p>
                      </div>
                    );
                  })}
                </div>
              ) : (
                <p className="mt-3 text-xs text-slate-300">
                  {aiStatus.phase === 'loading' ? 'Comprobando IA…' : aiStatus.message}
                </p>
              )}
            </div>

            <div className="mt-4 rounded-xl border border-white/10 bg-white/[0.03] p-4 text-sm">
              <div className="flex items-center justify-between gap-3">
                <span className="font-medium">Actualizaciones</span>
                <button
                  type="button"
                  disabled={update.phase === 'checking'}
                  onClick={() => void checkForUpdates()}
                  className="text-xs text-blue-300 hover:text-blue-200 disabled:opacity-50"
                >
                  Buscar actualizaciones
                </button>
              </div>
              {update.available && (
                <div className="mt-3">
                  <p className="text-slate-200">Nueva versión: {update.version}</p>
                  {update.notes && <p className="mt-2 whitespace-pre-wrap text-xs text-slate-400">{update.notes}</p>}
                </div>
              )}
              {update.message && <p className="mt-3 text-xs text-slate-300">{update.message}</p>}
              {update.phase === 'available' && update.canDownload && (
                <button type="button" onClick={() => void downloadUpdate()} className="mt-4 rounded-lg bg-blue-600 px-4 py-2 text-xs font-semibold hover:bg-blue-500">
                  Descargar en segundo plano
                </button>
              )}
              {update.phase === 'downloaded' && (
                <button type="button" onClick={() => void installUpdate()} className="mt-4 rounded-lg bg-emerald-600 px-4 py-2 text-xs font-semibold hover:bg-emerald-500">
                  Reiniciar y actualizar
                </button>
              )}
            </div>

            <div className="mt-4 rounded-xl border border-white/10 bg-white/[0.03] p-4 text-sm">
              <div className="flex items-center justify-between gap-3">
                <div>
                  <p className="font-medium">Copia de seguridad manual</p>
                  <p className="mt-1 text-xs text-slate-400">Incluye datos e imágenes, sin secretos ni logs.</p>
                </div>
                <button
                  type="button"
                  disabled={backup.phase === 'running'}
                  onClick={() => void createBackup()}
                  className="rounded-lg border border-blue-400/30 px-3 py-2 text-xs text-blue-200 hover:bg-blue-400/10 disabled:opacity-50"
                >
                  Crear copia
                </button>
              </div>
              {backup.message && (
                <p className={`mt-3 break-all text-xs ${backup.phase === 'error' ? 'text-red-300' : 'text-slate-300'}`}>
                  {backup.message}
                </p>
              )}
            </div>
          </section>
        </div>
      )}
    </>
  );
};

export default DesktopControls;
