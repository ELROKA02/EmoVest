import { useCallback, useEffect, useMemo, useState } from 'react';
import { apiFetch, isDesktopRuntime } from '../config';

const ENDPOINT_STORAGE_KEY = 'emovestMcpPublicEndpoint';
const ENV_ENDPOINT = String(import.meta.env.VITE_MCP_PUBLIC_URL || '').trim().replace(/\/+$/, '');
const LOCAL_ENDPOINT = 'http://localhost:8000/mcp';

const TOOLS = [
  { name: 'list_accounts', description: 'Lee las cuentas de trading disponibles.' },
  { name: 'list_operations', description: 'Lee las operaciones de una cuenta.' },
  { name: 'create_operation', description: 'Crea una operación en una cuenta.' },
  { name: 'update_operation', description: 'Edita los campos de una operación.' },
  { name: 'delete_operation', description: 'Elimina una operación.' },
  { name: 'update_account', description: 'Edita una cuenta de trading.' },
  { name: 'delete_account', description: 'Elimina una cuenta de trading.' },
  { name: 'get_confirmation_status', description: 'Consulta el estado de solicitudes antiguas que esperaban confirmación.' },
];

const normalizeEndpoint = (value) => String(value || '').trim().replace(/\/+$/, '');

const initialEndpoint = () => {
  if (ENV_ENDPOINT) return ENV_ENDPOINT;
  if (typeof window === 'undefined') return '';
  return normalizeEndpoint(window.localStorage.getItem(ENDPOINT_STORAGE_KEY)) || LOCAL_ENDPOINT;
};

const isSupportedEndpoint = (value) => /^(https:\/\/[^\s]+|http:\/\/(localhost|127\.0\.0\.1)(?::\d+)?(?:\/[^\s]*)?)$/i.test(value);
const isManagedLocalEndpoint = (value) => normalizeEndpoint(value) === LOCAL_ENDPOINT;

const McpConnectionSettings = () => {
  const [endpoint, setEndpoint] = useState(initialEndpoint);
  const [saved, setSaved] = useState(false);
  const [copied, setCopied] = useState('');
  const [mcpRuntime, setMcpRuntime] = useState({ running: false, last_error: null });
  const [mcpLoading, setMcpLoading] = useState(false);
  const [toolBusy, setToolBusy] = useState('');

  const hasValidEndpoint = useMemo(() => isSupportedEndpoint(endpoint), [endpoint]);
  const endpointForExamples = hasValidEndpoint ? endpoint : LOCAL_ENDPOINT;
  const canManageLocalServer = isDesktopRuntime() && isManagedLocalEndpoint(endpoint);

  const refreshMcpStatus = useCallback(async () => {
    if (!canManageLocalServer) return;
    try {
      const statusResponse = await apiFetch('/desktop/mcp/status');
      if (!statusResponse.ok) throw new Error('No se pudo consultar el estado de MCP.');
      setMcpRuntime(await statusResponse.json());
    } catch (error) {
      setMcpRuntime({ running: false, last_error: error.message || 'No se pudo consultar el servidor MCP.' });
    }
  }, [canManageLocalServer]);

  useEffect(() => {
    void refreshMcpStatus();
    if (!canManageLocalServer) return undefined;
    const interval = window.setInterval(() => void refreshMcpStatus(), 2500);
    return () => window.clearInterval(interval);
  }, [canManageLocalServer, refreshMcpStatus]);

  const toggleLocalMcp = async () => {
    setMcpLoading(true);
    try {
      const response = await apiFetch(`/desktop/mcp/${mcpRuntime.running ? 'stop' : 'start'}`, { method: 'POST' });
      const body = await response.json();
      if (!response.ok) throw new Error(body.detail || 'No se pudo actualizar el servidor MCP.');
      setMcpRuntime(body);
    } catch (error) {
      setMcpRuntime((current) => ({ ...current, last_error: error.message || 'No se pudo actualizar el servidor MCP.' }));
    } finally {
      setMcpLoading(false);
    }
  };

  const toggleTool = async (toolName, enabled) => {
    setToolBusy(toolName);
    try {
      const response = await apiFetch(`/desktop/mcp/tools/${toolName}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ enabled }),
      });
      const body = await response.json();
      if (!response.ok) throw new Error(body.detail || 'No se pudo actualizar la herramienta MCP.');
      setMcpRuntime((current) => ({ ...current, tool_states: body.tools }));
    } catch (error) {
      setMcpRuntime((current) => ({ ...current, last_error: error.message || 'No se pudo actualizar la herramienta MCP.' }));
    } finally {
      setToolBusy('');
    }
  };

  const copy = async (value, label) => {
    try {
      await navigator.clipboard.writeText(value);
      setCopied(label);
      window.setTimeout(() => setCopied(''), 1800);
    } catch {
      setCopied('No se pudo copiar');
    }
  };

  const saveEndpoint = () => {
    const normalized = normalizeEndpoint(endpoint);
    setEndpoint(normalized);
    window.localStorage.setItem(ENDPOINT_STORAGE_KEY, normalized);
    setSaved(true);
    window.setTimeout(() => setSaved(false), 2200);
  };

  const codexCommand = `codex mcp add emovest --url ${endpointForExamples}`;

  return (
    <section className="mt-8 border-t border-white/10 pt-6" aria-labelledby="mcp-settings-title">
      <div>
        <div>
          <h4 id="mcp-settings-title" className="text-lg font-semibold text-white">Conexión MCP con IA</h4>
          <p className="mt-1 text-sm text-gray-400">
            Controla el servidor local y decide qué herramientas puede usar Codex, ChatGPT o Claude con tus cuentas y operaciones.
          </p>
        </div>
      </div>

      <div className="mt-5 rounded-xl border border-cyan-400/20 bg-cyan-400/[0.04] p-4">
        <label className="block text-sm font-medium text-white" htmlFor="mcp-public-endpoint">Endpoint MCP</label>
        <p className="mt-1 text-xs text-cyan-100/70">Por defecto usa la ruta local de este equipo. Puedes sustituirla por una URL HTTPS pública con transporte Streamable HTTP.</p>
        <div className="mt-3 flex flex-col gap-2 sm:flex-row">
          <input
            id="mcp-public-endpoint"
            type="url"
            value={endpoint}
            onChange={(event) => setEndpoint(event.target.value)}
            placeholder={LOCAL_ENDPOINT}
            className="min-w-0 flex-1 rounded-lg border border-white/10 bg-black/20 px-3 py-2 text-sm text-white outline-none transition focus:border-cyan-400"
          />
          <button type="button" onClick={saveEndpoint} className="rounded-lg bg-cyan-600 px-4 py-2 text-sm font-semibold text-white transition hover:bg-cyan-500">
            Guardar URL
          </button>
          {hasValidEndpoint && <button type="button" onClick={() => void copy(endpoint, 'URL')} className="rounded-lg border border-cyan-400/30 px-4 py-2 text-sm font-semibold text-cyan-100 transition hover:bg-cyan-400/10">Copiar</button>}
        </div>
        {saved && <p className="mt-2 text-xs text-emerald-300">URL guardada en este dispositivo.</p>}
        {copied && <p className="mt-2 text-xs text-emerald-300">{copied === 'URL' ? 'URL copiada.' : copied}</p>}
      </div>

      {canManageLocalServer && (
        <div className="mt-4 flex flex-col gap-3 rounded-xl border border-white/10 bg-black/10 p-4 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <div className="flex flex-wrap items-center gap-2">
              <h5 className="text-sm font-semibold text-white">Servidor MCP local</h5>
              <span className={`inline-flex items-center gap-1.5 whitespace-nowrap rounded-full px-2.5 py-1 text-xs font-medium ${mcpRuntime.running ? 'bg-emerald-400/15 text-emerald-200' : 'bg-slate-400/15 text-slate-300'}`}>
                <span className={`h-1.5 w-1.5 rounded-full ${mcpRuntime.running ? 'bg-emerald-300' : 'bg-slate-400'}`} aria-hidden="true" />
                {mcpRuntime.running ? 'MCP activo' : 'MCP apagado'}
              </span>
            </div>
            <p className="mt-1 text-xs text-gray-400">Solo escucha en este equipo. Las herramientas activadas ejecutan y guardan sus cambios directamente.</p>
            {mcpRuntime.last_error && <p className="mt-2 text-xs text-amber-200">{mcpRuntime.last_error}</p>}
          </div>
          <button
            type="button"
            onClick={() => void toggleLocalMcp()}
            disabled={mcpLoading}
            className={`shrink-0 rounded-lg px-4 py-2 text-sm font-semibold text-white transition disabled:cursor-not-allowed disabled:opacity-60 ${mcpRuntime.running ? 'bg-rose-600 hover:bg-rose-500' : 'bg-emerald-600 hover:bg-emerald-500'}`}
          >
            {mcpLoading ? 'Actualizando…' : (mcpRuntime.running ? 'Apagar MCP' : 'Encender MCP')}
          </button>
        </div>
      )}

      {!hasValidEndpoint && (
        <p className="mt-4 rounded-lg border border-amber-400/25 bg-amber-400/[0.08] p-3 text-sm text-amber-100">
          Introduce una URL local como <code>{LOCAL_ENDPOINT}</code> o una URL HTTPS pública. ChatGPT y Claude solo pueden usar la opción pública; Codex local puede usar <code>localhost</code>.
        </p>
      )}

      <div className="mt-5 grid grid-cols-1 gap-4 lg:grid-cols-3">
        <article className="rounded-xl border border-white/10 bg-white/[0.03] p-4">
          <h5 className="font-semibold text-white">Codex</h5>
          <p className="mt-1 text-xs leading-5 text-gray-400">Ejecuta este comando en tu terminal y, si el servidor lo solicita, completa la autenticación.</p>
          <pre className="mt-3 overflow-x-auto rounded-lg bg-black/30 p-3 text-xs text-cyan-100"><code>{codexCommand}</code></pre>
          <button type="button" onClick={() => void copy(codexCommand, 'Codex')} className="mt-3 rounded-lg border border-cyan-400/30 px-3 py-2 text-xs font-semibold text-cyan-100 hover:bg-cyan-400/10">Copiar comando</button>
        </article>

        <article className="rounded-xl border border-white/10 bg-white/[0.03] p-4">
          <h5 className="font-semibold text-white">ChatGPT</h5>
          <ol className="mt-2 list-decimal space-y-1 pl-5 text-xs leading-5 text-gray-400">
            <li>Activa el modo de desarrollador en Ajustes → Apps.</li>
            <li>Crea una app MCP personalizada e introduce la URL.</li>
            <li>Escanea las herramientas y habilita solo las necesarias.</li>
          </ol>
          <a href="https://help.openai.com/en/articles/12584461-developer-mode-and-full-mcp-connectors-in-chatgpt" target="_blank" rel="noreferrer" className="mt-3 inline-block text-xs font-semibold text-cyan-200 hover:text-cyan-100">Abrir guía de ChatGPT ↗</a>
        </article>

        <article className="rounded-xl border border-white/10 bg-white/[0.03] p-4">
          <h5 className="font-semibold text-white">Claude</h5>
          <ol className="mt-2 list-decimal space-y-1 pl-5 text-xs leading-5 text-gray-400">
            <li>Ve a Customize → Connectors.</li>
            <li>Selecciona “Add custom connector”.</li>
            <li>Pega la URL y completa el acceso autorizado.</li>
          </ol>
          <a href="https://support.claude.com/en/articles/11175166-get-started-with-custom-connectors-using-remote-mcp" target="_blank" rel="noreferrer" className="mt-3 inline-block text-xs font-semibold text-cyan-200 hover:text-cyan-100">Abrir guía de Claude ↗</a>
        </article>
      </div>

      <div className="mt-5 rounded-xl border border-white/10 bg-black/10 p-4">
        <div className="flex flex-col gap-1 sm:flex-row sm:items-center sm:justify-between">
          <h5 className="text-sm font-semibold text-white">Herramientas expuestas por el MCP local</h5>
          <span className="text-xs text-gray-500">Una herramienta desactivada no se muestra a la IA. Las activadas guardan los cambios directamente.</span>
        </div>
        <ul className="mt-3 grid grid-cols-1 gap-2 sm:grid-cols-2">
          {TOOLS.map((tool) => {
            const enabled = Boolean(mcpRuntime.tool_states?.[tool.name]);
            return (
            <li key={tool.name} className="rounded-lg border border-white/5 bg-white/[0.03] px-3 py-2">
              <div className="flex items-start justify-between gap-3">
                <code className="text-xs font-semibold text-cyan-200">{tool.name}</code>
                {canManageLocalServer && (
                  <button
                    type="button"
                    role="switch"
                    aria-checked={enabled}
                    onClick={() => void toggleTool(tool.name, !enabled)}
                    disabled={Boolean(toolBusy)}
                    className={`rounded-full px-2.5 py-1 text-xs font-semibold transition disabled:opacity-60 ${enabled ? 'bg-emerald-500/20 text-emerald-100' : 'bg-slate-500/20 text-slate-300'}`}
                  >
                    {toolBusy === tool.name ? 'Guardando…' : (enabled ? 'Activada' : 'Desactivada')}
                  </button>
                )}
              </div>
              <p className="mt-1 text-xs text-gray-400">{tool.description}</p>
            </li>
            );
          })}
        </ul>
      </div>
    </section>
  );
};

export default McpConnectionSettings;
