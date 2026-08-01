import { useCallback, useEffect, useMemo, useState } from 'react';
import { apiFetch } from '../config';
import { Spinner } from './ui';
import ollamaLogo from '../assets/ollama-logo.png';

const USE_CASES = [
  {
    id: 'emotion',
    label: 'Análisis emocional',
    description: 'Clasifica las notas vinculadas a tus operaciones.',
    defaultModel: 'clasificador_emociones_gemma4:latest',
  },
  {
    id: 'chat',
    label: 'EVA · Analista IA',
    description: 'Da soporte al chat de análisis dentro de EmoVest.',
    defaultModel: 'qwen3.5:latest',
  },
];

const LOCAL_PROVIDERS = new Set(['ollama', 'llamacpp']);

const STATUS_LABELS = {
  available: 'Disponible',
  not_installed: 'No instalado',
  service_stopped: 'Servicio detenido',
  model_missing: 'Modelo ausente',
  disabled: 'Desactivada',
  unreachable: 'No accesible',
};

const getErrorMessage = async (response, fallback) => {
  try {
    const data = await response.json();
    return data.detail || fallback;
  } catch {
    return fallback;
  }
};

const AiSettings = () => {
  const [aiStatus, setAiStatus] = useState(null);
  const [drafts, setDrafts] = useState({});
  const [phase, setPhase] = useState('loading');
  const [error, setError] = useState('');
  const [savingUseCase, setSavingUseCase] = useState('');
  const [savedUseCase, setSavedUseCase] = useState('');

  const loadSettings = useCallback(async () => {
    const token = sessionStorage.getItem('token');
    if (!token) {
      setPhase('error');
      setError('Inicia sesión para consultar la configuración de IA.');
      return;
    }

    setPhase('loading');
    setError('');
    try {
      const response = await apiFetch('/ia/status', {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!response.ok) {
        throw new Error(await getErrorMessage(response, 'No se pudo cargar la configuración de IA.'));
      }

      const statuses = (await response.json()).statuses || {};
      setAiStatus(statuses);
      setDrafts(Object.fromEntries(USE_CASES.map(({ id, defaultModel }) => {
        const config = statuses[id]?.config || {};
        return [id, {
          model: config.model || defaultModel,
          baseUrl: config.base_url || 'http://localhost:11434',
          installMode: config.install_mode || 'manual',
        }];
      })));
      setPhase('ready');
    } catch (requestError) {
      setPhase('error');
      setError(requestError.message || 'No se pudo conectar con el servicio de IA.');
    }
  }, []);

  useEffect(() => {
    const timerId = window.setTimeout(() => {
      void loadSettings();
    }, 0);
    return () => window.clearTimeout(timerId);
  }, [loadSettings]);

  const externalProviders = useMemo(() => USE_CASES
    .filter(({ id }) => {
      const provider = aiStatus?.[id]?.config?.provider;
      return provider && !LOCAL_PROVIDERS.has(provider);
    })
    .map(({ label }) => label), [aiStatus]);

  const updateDraft = (useCase, field, value) => {
    setDrafts((current) => ({
      ...current,
      [useCase]: { ...current[useCase], [field]: value },
    }));
    setSavedUseCase('');
  };

  const saveOllamaConfig = async (useCase) => {
    const draft = drafts[useCase];
    if (!draft?.model?.trim() || !draft?.baseUrl?.trim()) {
      setError('Indica un modelo y la URL local de Ollama antes de guardar.');
      return;
    }

    const token = sessionStorage.getItem('token');
    if (!token) return;

    setSavingUseCase(useCase);
    setError('');
    try {
      const response = await apiFetch(`/ia/config/${useCase}`, {
        method: 'PUT',
        headers: {
          Authorization: `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          provider: 'ollama',
          model: draft.model.trim(),
          base_url: draft.baseUrl.trim(),
          install_mode: draft.installMode || 'manual',
        }),
      });
      if (!response.ok) {
        throw new Error(await getErrorMessage(response, 'No se pudo guardar la configuración de Ollama.'));
      }

      setSavedUseCase(useCase);
      await loadSettings();
    } catch (requestError) {
      setError(requestError.message || 'No se pudo guardar la configuración de Ollama.');
    } finally {
      setSavingUseCase('');
    }
  };

  return (
    <section className="pt-6 border-t border-white/10">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <h4 className="text-lg font-semibold text-white">Configuración de IA</h4>
          <p className="mt-1 text-sm text-gray-400">
            El análisis emocional es opcional: tus operaciones se guardan aunque la IA no esté disponible.
          </p>
        </div>
        <button
          type="button"
          onClick={() => void loadSettings()}
          disabled={phase === 'loading'}
          className="self-start rounded-lg border border-blue-400/30 px-3 py-2 text-xs font-semibold text-blue-200 hover:bg-blue-400/10 disabled:opacity-50"
        >
          {phase === 'loading' ? 'Actualizando…' : 'Actualizar estado'}
        </button>
      </div>

      <div className="mt-5 grid grid-cols-1 gap-4 lg:grid-cols-2">
        <article className="rounded-xl border border-emerald-400/25 bg-emerald-400/[0.06] p-5">
          <div className="flex items-center gap-3">
            <span className="flex h-9 w-9 items-center justify-center rounded-lg bg-emerald-400/15 text-emerald-300" aria-hidden="true">⌂</span>
            <div>
              <h5 className="font-semibold text-white">IA local</h5>
              <p className="text-xs text-emerald-100/70">Ollama se ejecuta en tu equipo.</p>
            </div>
          </div>
          <p className="mt-3 text-sm text-gray-300">
            Las notas se procesan contra un servicio local, normalmente en <code className="text-emerald-200">localhost:11434</code>. Requiere tener Ollama y los modelos instalados.
          </p>
        </article>

        <article className="rounded-xl border border-violet-400/25 bg-violet-400/[0.06] p-5">
          <div className="flex items-center gap-3">
            <span className="flex h-9 w-9 items-center justify-center rounded-lg bg-violet-400/15 text-violet-200" aria-hidden="true">☁</span>
            <div>
              <h5 className="font-semibold text-white">IA no local</h5>
              <p className="text-xs text-violet-100/70">El proveedor procesa las solicitudes fuera del equipo.</p>
            </div>
          </div>
          <p className="mt-3 text-sm text-gray-300">
            Está pensada para proveedores externos como OpenRouter. Requiere configurar la clave del proveedor en el backend; no se guarda ninguna clave en esta pantalla.
          </p>
          {externalProviders.length > 0 && (
            <p className="mt-3 text-xs text-violet-200">Configuración externa activa: {externalProviders.join(', ')}.</p>
          )}
        </article>
      </div>

      {error && (
        <p role="alert" className="mt-4 rounded-lg border border-red-400/30 bg-red-400/10 p-3 text-sm text-red-200">{error}</p>
      )}

      <div className="mt-5 rounded-xl border border-white/10 bg-white/[0.03] p-5">
        <div className="flex items-center gap-3">
          <img
            src={ollamaLogo}
            alt=""
            aria-hidden="true"
            className="h-9 w-9 rounded-lg bg-white p-1 object-contain"
          />
          <div>
            <h5 className="font-semibold text-white">Ollama local</h5>
            <p className="text-xs text-gray-400">Configuración activa del backend para cada función de IA.</p>
          </div>
        </div>

        {phase === 'loading' && !aiStatus ? (
          <div className="flex items-center gap-2 py-8 text-sm text-gray-400"><Spinner size="sm" /> Cargando configuración de Ollama…</div>
        ) : (
          <div className="mt-5 space-y-5">
            {USE_CASES.map(({ id, label, description }) => {
              const statusItem = aiStatus?.[id];
              const status = statusItem?.status;
              const activeProvider = statusItem?.config?.provider;
              const draft = drafts[id] || {};
              const isSaving = savingUseCase === id;
              const availableModels = Array.isArray(status?.models) ? status.models : [];
              const selectedModelIsAvailable = availableModels.includes(draft.model);
              const activeModel = statusItem?.config?.model || '';
              const hasUnsavedModel = draft.model && draft.model !== activeModel;

              return (
                <div key={id} className="rounded-lg border border-white/10 p-4">
                  <div className="flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
                    <div>
                      <h6 className="font-medium text-white">{label}</h6>
                      <p className="mt-1 text-xs text-gray-400">{description}</p>
                    </div>
                    <span className={`self-start rounded-full px-2.5 py-1 text-xs font-medium ${status?.available ? 'bg-emerald-400/15 text-emerald-200' : 'bg-amber-400/15 text-amber-200'}`}>
                      {STATUS_LABELS[status?.state] || 'Sin comprobar'}
                    </span>
                  </div>

                  {activeProvider && activeProvider !== 'ollama' && (
                    <p className="mt-3 rounded-md bg-amber-400/10 p-2 text-xs text-amber-200">
                      Actualmente usa {activeProvider}. Guardar estos ajustes lo cambiará a Ollama local.
                    </p>
                  )}

                  <p className="mt-3 text-xs text-slate-300">
                    Modelo activo: <span className="font-medium text-white">{activeModel || 'Sin configurar'}</span>
                    {hasUnsavedModel && (
                      <span className="text-amber-300"> · Cambio pendiente: {draft.model}</span>
                    )}
                  </p>

                  <div className="mt-4 grid grid-cols-1 gap-4 md:grid-cols-2">
                    <label className="block text-sm text-gray-300">
                      Modelo de Ollama
                      <select
                        value={draft.model || ''}
                        onChange={(event) => updateDraft(id, 'model', event.target.value)}
                        className="mt-2 w-full rounded-lg border border-white/10 bg-black/20 px-3 py-2 text-sm text-white outline-none transition focus:border-blue-400"
                      >
                        {!selectedModelIsAvailable && draft.model && (
                          <option value={draft.model}>{draft.model} (no instalado)</option>
                        )}
                        {availableModels.length === 0 && !draft.model && (
                          <option value="">No hay modelos disponibles</option>
                        )}
                        {availableModels.map((model) => (
                          <option key={model} value={model}>{model}</option>
                        ))}
                      </select>
                      <p className="mt-1 text-xs text-gray-500">
                        {availableModels.length > 0
                          ? `${availableModels.length} modelo${availableModels.length === 1 ? '' : 's'} instalado${availableModels.length === 1 ? '' : 's'} en este equipo.`
                          : 'Inicia Ollama e instala un modelo para poder seleccionarlo.'}
                      </p>
                    </label>
                    <label className="block text-sm text-gray-300">
                      URL de Ollama
                      <input
                        type="url"
                        value={draft.baseUrl || ''}
                        onChange={(event) => updateDraft(id, 'baseUrl', event.target.value)}
                        placeholder="http://localhost:11434"
                        className="mt-2 w-full rounded-lg border border-white/10 bg-black/20 px-3 py-2 text-sm text-white outline-none transition focus:border-blue-400"
                      />
                    </label>
                  </div>

                  <div className="mt-4 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
                    <p className="text-xs text-gray-400">{status?.message || 'Aún no se ha comprobado el estado de este servicio.'}</p>
                    <button
                      type="button"
                      disabled={isSaving || phase === 'loading' || !selectedModelIsAvailable}
                      onClick={() => void saveOllamaConfig(id)}
                      className="inline-flex shrink-0 items-center justify-center gap-2 rounded-lg bg-blue-600 px-4 py-2 text-sm font-semibold text-white hover:bg-blue-500 disabled:cursor-not-allowed disabled:opacity-50"
                    >
                      {isSaving && <Spinner size="sm" />}
                      {isSaving ? 'Guardando…' : 'Guardar Ollama'}
                    </button>
                  </div>
                  {savedUseCase === id && (
                    <p className="mt-3 text-xs text-emerald-300">
                      Configuración guardada. El chat usará {activeModel || draft.model} en el siguiente mensaje.
                    </p>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </div>
    </section>
  );
};

export default AiSettings;
