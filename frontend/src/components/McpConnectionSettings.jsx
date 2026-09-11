import { useMemo, useState } from 'react';

const ENDPOINT_STORAGE_KEY = 'emovestMcpPublicEndpoint';
const ENV_ENDPOINT = String(import.meta.env.VITE_MCP_PUBLIC_URL || '').trim().replace(/\/+$/, '');

const TOOLS = [
  { name: 'list_accounts', description: 'Lee las cuentas de trading disponibles.' },
  { name: 'list_operations', description: 'Lee las operaciones de una cuenta.' },
  { name: 'create_operation', description: 'Crea una operación en una cuenta.' },
  { name: 'update_operation', description: 'Edita los campos de una operación.' },
  { name: 'delete_operation', description: 'Elimina una operación.' },
  { name: 'update_account', description: 'Edita una cuenta de trading.' },
  { name: 'delete_account', description: 'Elimina una cuenta de trading.' },
];

const normalizeEndpoint = (value) => String(value || '').trim().replace(/\/+$/, '');

const initialEndpoint = () => {
  if (ENV_ENDPOINT) return ENV_ENDPOINT;
  if (typeof window === 'undefined') return '';
  return normalizeEndpoint(window.localStorage.getItem(ENDPOINT_STORAGE_KEY));
};

const McpConnectionSettings = () => {
  const [endpoint, setEndpoint] = useState(initialEndpoint);
  const [saved, setSaved] = useState(false);
  const [copied, setCopied] = useState('');

  const hasValidEndpoint = useMemo(() => /^https:\/\/[^\s]+$/i.test(endpoint), [endpoint]);
  const endpointForExamples = hasValidEndpoint ? endpoint : 'https://mcp.tu-dominio.com/mcp';

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
      <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <h4 id="mcp-settings-title" className="text-lg font-semibold text-white">Conexión externa con IA</h4>
          <p className="mt-1 text-sm text-gray-400">
            Conecta EmoVest mediante MCP para que Codex, ChatGPT o Claude puedan consultar y gestionar tus cuentas y operaciones.
          </p>
        </div>
        <span className={`self-start rounded-full px-2.5 py-1 text-xs font-medium ${hasValidEndpoint ? 'bg-emerald-400/15 text-emerald-200' : 'bg-amber-400/15 text-amber-200'}`}>
          {hasValidEndpoint ? 'Endpoint configurado' : 'Endpoint pendiente'}
        </span>
      </div>

      <div className="mt-5 rounded-xl border border-cyan-400/20 bg-cyan-400/[0.04] p-4">
        <label className="block text-sm font-medium text-white" htmlFor="mcp-public-endpoint">Endpoint MCP público</label>
        <p className="mt-1 text-xs text-cyan-100/70">Debe ser una URL HTTPS pública con transporte Streamable HTTP. No uses la URL local de EmoVest.</p>
        <div className="mt-3 flex flex-col gap-2 sm:flex-row">
          <input
            id="mcp-public-endpoint"
            type="url"
            value={endpoint}
            onChange={(event) => setEndpoint(event.target.value)}
            placeholder="https://mcp.tu-dominio.com/mcp"
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

      {!hasValidEndpoint && (
        <p className="mt-4 rounded-lg border border-amber-400/25 bg-amber-400/[0.08] p-3 text-sm text-amber-100">
          Falta publicar el servidor MCP. Hasta entonces la integración externa no estará disponible: ChatGPT y Claude no pueden conectarse a <code>localhost</code>.
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
          <h5 className="text-sm font-semibold text-white">Herramientas que expondrá EmoVest</h5>
          <span className="text-xs text-gray-500">Las acciones de edición o borrado deben pedir confirmación.</span>
        </div>
        <ul className="mt-3 grid grid-cols-1 gap-2 sm:grid-cols-2">
          {TOOLS.map((tool) => (
            <li key={tool.name} className="rounded-lg border border-white/5 bg-white/[0.03] px-3 py-2">
              <code className="text-xs font-semibold text-cyan-200">{tool.name}</code>
              <p className="mt-1 text-xs text-gray-400">{tool.description}</p>
            </li>
          ))}
        </ul>
      </div>
    </section>
  );
};

export default McpConnectionSettings;
