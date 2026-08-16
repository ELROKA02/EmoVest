import { useCallback, useEffect, useState } from 'react';
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

const OPENROUTER_PRESET_MODELS = [
  { id: 'openai/gpt-5.6-terra', name: 'GPT-5.6 Terra · Equilibrado', detail: '$2.50 / $15 por 1M tokens' },
  { id: 'anthropic/claude-sonnet-4.6', name: 'Claude Sonnet 4.6 · Equilibrado', detail: '$3 / $15 por 1M tokens' },
  { id: 'google/gemini-3-flash-preview', name: 'Gemini 3 Flash · Gran valor', detail: '$0.50 / $3 por 1M tokens' },
  { id: 'qwen/qwen3.5-9b', name: 'Qwen 3.5 9B · Económico', detail: 'Modelo ligero para EVA' },
  { id: 'openai/gpt-4o-mini', name: 'GPT-4o mini · Muy económico', detail: '$0.15 / $0.60 por 1M tokens' },
];

const OPENROUTER_EMOTION_PRESET_MODELS = [
  { id: 'google/gemini-3-flash-preview', name: 'Gemini 3 Flash · Recomendado', detail: '$0.50 / $3 por 1M tokens' },
  { id: 'openai/gpt-4o-mini', name: 'GPT-4o mini · Muy económico', detail: '$0.15 / $0.60 por 1M tokens' },
  { id: 'qwen/qwen3.5-9b', name: 'Qwen 3.5 9B · Económico', detail: 'Modelo ligero para clasificar' },
];

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
  const [openRouterDraft, setOpenRouterDraft] = useState({
    model: '', baseUrl: 'https://openrouter.ai/api/v1', apiKey: '',
  });
  const [openRouterModels, setOpenRouterModels] = useState([]);
  const [openRouterEmotionModels, setOpenRouterEmotionModels] = useState([]);
  const [openRouterEmotionDraft, setOpenRouterEmotionDraft] = useState({
    model: '', baseUrl: 'https://openrouter.ai/api/v1',
  });
  const [loadingOpenRouterModels, setLoadingOpenRouterModels] = useState(false);
  const [removingOpenRouterKey, setRemovingOpenRouterKey] = useState(false);
  // No asumimos Ollama mientras se carga la configuración. De ese modo cada
  // selector refleja exclusivamente el proveedor activo que el backend ha
  // confirmado para su caso de uso.
  const [activeProviders, setActiveProviders] = useState({});

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
      const chatConfig = statuses.chat?.config || {};
      const emotionConfig = statuses.emotion?.config || {};
      const chatProfiles = statuses.chat?.profiles || {};
      const emotionProfiles = statuses.emotion?.profiles || {};
      setActiveProviders({
        chat: chatConfig.provider,
        emotion: emotionConfig.provider,
      });
      setOpenRouterDraft((current) => ({
        ...current,
        model: chatProfiles.openrouter?.model || current.model,
        baseUrl: chatProfiles.openrouter?.base_url
          || current.baseUrl
          || 'https://openrouter.ai/api/v1',
      }));
      setOpenRouterEmotionDraft((current) => ({
        ...current,
        model: emotionProfiles.openrouter?.model || current.model,
        baseUrl: emotionProfiles.openrouter?.base_url
          || current.baseUrl
          || 'https://openrouter.ai/api/v1',
      }));
      setDrafts(Object.fromEntries(USE_CASES.map(({ id, defaultModel }) => {
        const config = statuses[id]?.profiles?.ollama || {};
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

  const loadOpenRouterModels = useCallback(async (useCase = 'chat') => {
    const token = sessionStorage.getItem('token');
    if (!token) return;
    setLoadingOpenRouterModels(true);
    setError('');
    try {
      const response = await apiFetch(`/ia/openrouter/models?use_case=${useCase}`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!response.ok) {
        throw new Error(await getErrorMessage(response, 'No se pudieron cargar los modelos de OpenRouter.'));
      }
      const models = (await response.json()).models || [];
      if (useCase === 'emotion') setOpenRouterEmotionModels(models);
      else setOpenRouterModels(models);
    } catch (requestError) {
      setError(requestError.message || 'No se pudieron cargar los modelos de OpenRouter.');
    } finally {
      setLoadingOpenRouterModels(false);
    }
  }, []);

  useEffect(() => {
    const timerId = window.setTimeout(() => {
      void loadSettings();
    }, 0);
    return () => window.clearTimeout(timerId);
  }, [loadSettings]);

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
          activate: activeProviders[useCase] === 'ollama',
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

  const saveOpenRouterConfig = async () => {
    if (!openRouterDraft.model.trim()) {
      setError('Selecciona o indica un modelo de OpenRouter para EVA.');
      return;
    }
    const token = sessionStorage.getItem('token');
    if (!token) return;

    setSavingUseCase('openrouter');
    setError('');
    try {
      const response = await apiFetch('/ia/config/chat', {
        method: 'PUT',
        headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' },
        body: JSON.stringify({
          provider: 'openrouter',
          model: openRouterDraft.model.trim(),
          base_url: openRouterDraft.baseUrl.trim() || 'https://openrouter.ai/api/v1',
          install_mode: 'remote',
          activate: activeProviders.chat === 'openrouter',
          ...(openRouterDraft.apiKey.trim() ? { api_key: openRouterDraft.apiKey.trim() } : {}),
        }),
      });
      if (!response.ok) {
        throw new Error(await getErrorMessage(response, 'No se pudo guardar la configuración de OpenRouter.'));
      }
      setOpenRouterDraft((current) => ({ ...current, apiKey: '' }));
      setSavedUseCase('openrouter');
      await loadSettings();
      await loadOpenRouterModels();
    } catch (requestError) {
      setError(requestError.message || 'No se pudo guardar la configuración de OpenRouter.');
    } finally {
      setSavingUseCase('');
    }
  };

  const saveOpenRouterEmotionConfig = async () => {
    if (!openRouterEmotionDraft.model.trim()) {
      setError('Selecciona o indica un modelo de OpenRouter para el análisis emocional.');
      return;
    }
    const token = sessionStorage.getItem('token');
    if (!token) return;

    setSavingUseCase('openrouter-emotion');
    setError('');
    try {
      const response = await apiFetch('/ia/config/emotion', {
        method: 'PUT',
        headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' },
        body: JSON.stringify({
          provider: 'openrouter',
          model: openRouterEmotionDraft.model.trim(),
          base_url: openRouterEmotionDraft.baseUrl.trim() || 'https://openrouter.ai/api/v1',
          install_mode: 'remote',
          activate: activeProviders.emotion === 'openrouter',
          ...(openRouterDraft.apiKey.trim() ? { api_key: openRouterDraft.apiKey.trim() } : {}),
        }),
      });
      if (!response.ok) {
        throw new Error(await getErrorMessage(response, 'No se pudo guardar el análisis emocional remoto.'));
      }
      setOpenRouterDraft((current) => ({ ...current, apiKey: '' }));
      setSavedUseCase('openrouter-emotion');
      await loadSettings();
      await loadOpenRouterModels('emotion');
    } catch (requestError) {
      setError(requestError.message || 'No se pudo guardar el análisis emocional remoto.');
    } finally {
      setSavingUseCase('');
    }
  };

  const removeOpenRouterKey = async () => {
    const token = sessionStorage.getItem('token');
    if (!token) return;
    setRemovingOpenRouterKey(true);
    setError('');
    try {
      const response = await apiFetch('/ia/openrouter/credentials', {
        method: 'DELETE', headers: { Authorization: `Bearer ${token}` },
      });
      if (!response.ok) throw new Error(await getErrorMessage(response, 'No se pudo eliminar la API key.'));
      setOpenRouterModels([]);
      await loadSettings();
    } catch (requestError) {
      setError(requestError.message || 'No se pudo eliminar la API key.');
    } finally {
      setRemovingOpenRouterKey(false);
    }
  };

  const openRouterKeyConfigured = Boolean(
    aiStatus?.chat?.config?.api_key_configured
    || aiStatus?.emotion?.config?.api_key_configured
    || aiStatus?.chat?.profiles?.openrouter?.api_key_configured
    || aiStatus?.emotion?.profiles?.openrouter?.api_key_configured,
  );

  const selectProvider = async (useCase, provider) => {
    const previousProvider = activeProviders[useCase];
    if (previousProvider === provider) return;

    const profileExists = Boolean(aiStatus?.[useCase]?.profiles?.[provider]);
    if (!profileExists) {
      setError('Configura y guarda este proveedor para activarlo.');
      return;
    }

    const token = sessionStorage.getItem('token');
    if (!token) return;
    setActiveProviders((current) => ({ ...current, [useCase]: provider }));
    setSavedUseCase('');
    setSavingUseCase(`select-${useCase}`);
    setError('');
    try {
      const response = await apiFetch(`/ia/config/${useCase}/active-provider`, {
        method: 'PUT',
        headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' },
        body: JSON.stringify({ provider }),
      });
      if (!response.ok) {
        throw new Error(await getErrorMessage(response, 'No se pudo seleccionar el proveedor de IA.'));
      }
      setSavedUseCase(`select-${useCase}`);
      await loadSettings();
    } catch (requestError) {
      setActiveProviders((current) => ({ ...current, [useCase]: previousProvider }));
      setError(requestError.message || 'No se pudo seleccionar el proveedor de IA.');
    } finally {
      setSavingUseCase('');
    }
  };

  const hasRemoteSelected = Object.values(activeProviders).includes('openrouter');

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

      {error && (
        <p role="alert" className="mt-4 rounded-lg border border-red-400/30 bg-red-400/10 p-3 text-sm text-red-200">{error}</p>
      )}

      {hasRemoteSelected && (
        <div className="mt-5 rounded-xl border border-violet-400/25 bg-violet-400/[0.05] p-4">
          <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
            <label className="block flex-1 text-sm text-gray-300">
              API key compartida de OpenRouter
              <input
                type="password"
                value={openRouterDraft.apiKey}
                onChange={(event) => setOpenRouterDraft((current) => ({ ...current, apiKey: event.target.value }))}
                placeholder={openRouterKeyConfigured ? 'Deja vacío para conservar la actual' : 'sk-or-…'}
                autoComplete="new-password"
                className="mt-2 w-full rounded-lg border border-white/10 bg-black/20 px-3 py-2 text-sm text-white outline-none transition focus:border-violet-400"
              />
              <p className="mt-1 text-xs text-gray-500">Se guarda cifrada en tu equipo y nunca vuelve a mostrarse.</p>
            </label>
            <div className="flex flex-wrap gap-2 sm:pt-6">
              <span className={`self-start rounded-full px-2.5 py-1 text-xs font-medium ${openRouterKeyConfigured ? 'bg-emerald-400/15 text-emerald-200' : 'bg-amber-400/15 text-amber-200'}`}>
                {openRouterKeyConfigured ? 'API key configurada' : 'API key pendiente'}
              </span>
              {openRouterKeyConfigured && <button type="button" onClick={() => void removeOpenRouterKey()} disabled={removingOpenRouterKey} className="rounded-lg border border-red-400/30 px-3 py-2 text-xs font-semibold text-red-200 hover:bg-red-400/10 disabled:opacity-50">
                {removingOpenRouterKey ? 'Eliminando…' : 'Eliminar API key'}
              </button>}
            </div>
          </div>
        </div>
      )}

      <div className="mt-5 grid grid-cols-1 gap-4 lg:grid-cols-2">
        {USE_CASES.map(({ id, label, description }) => {
          const selected = activeProviders[id];
          const selecting = savingUseCase === `select-${id}`;
          const isEmotion = id === 'emotion';
          const draft = drafts[id] || {};
          const statusItem = aiStatus?.[id];
          const localStatus = statusItem?.local_status || statusItem?.status;
          const availableModels = Array.isArray(localStatus?.models) ? localStatus.models : [];
          const selectedModelIsAvailable = availableModels.includes(draft.model);
          const remoteDraft = isEmotion ? openRouterEmotionDraft : openRouterDraft;
          const remoteModels = isEmotion ? openRouterEmotionModels : openRouterModels;
          const presets = isEmotion ? OPENROUTER_EMOTION_PRESET_MODELS : OPENROUTER_PRESET_MODELS;
          const isRemoteSaving = savingUseCase === (isEmotion ? 'openrouter-emotion' : 'openrouter');

          return (
            <div key={id} className="rounded-xl border border-white/10 bg-white/[0.03] p-5" role="radiogroup" aria-label={`Proveedor para ${label}`}>
              <h5 className="font-semibold text-white">{label}</h5>
              <p className="mt-1 text-xs text-gray-400">{description}</p>
              {!selected ? (
                <div className="mt-4 rounded-lg border border-white/10 bg-black/10 px-3 py-4 text-sm text-gray-400" role="status">
                  Cargando el proveedor seleccionado…
                </div>
              ) : <>
              <div className="mt-3 grid grid-cols-2 gap-2">
                <button type="button" role="radio" aria-checked={selected === 'ollama'} disabled={selecting} onClick={() => void selectProvider(id, 'ollama')} className={`rounded-lg border px-3 py-2 text-sm font-medium transition disabled:opacity-50 ${selected === 'ollama' ? 'border-emerald-300 bg-emerald-400/15 text-emerald-100' : 'border-white/10 text-gray-300 hover:bg-white/5'}`}>IA local</button>
                <button type="button" role="radio" aria-checked={selected === 'openrouter'} disabled={selecting} onClick={() => void selectProvider(id, 'openrouter')} className={`rounded-lg border px-3 py-2 text-sm font-medium transition disabled:opacity-50 ${selected === 'openrouter' ? 'border-violet-300 bg-violet-400/15 text-violet-100' : 'border-white/10 text-gray-300 hover:bg-white/5'}`}>IA no local</button>
              </div>
              {savedUseCase === `select-${id}` && <p className="mt-2 text-xs text-emerald-300">Proveedor activo actualizado.</p>}

              <div className={`mt-5 border-t pt-4 ${selected === 'ollama' ? 'border-emerald-400/20' : 'border-violet-400/20'}`}>
                {selected === 'ollama' ? (
                  <>
                    <div className="flex items-center justify-between gap-3">
                      <div className="flex items-center gap-2"><img src={ollamaLogo} alt="" aria-hidden="true" className="h-7 w-7 rounded bg-white p-1 object-contain" /><span className="text-sm font-medium text-white">Ollama local</span></div>
                      <span className={`rounded-full px-2.5 py-1 text-xs font-medium ${localStatus?.available ? 'bg-emerald-400/15 text-emerald-200' : 'bg-amber-400/15 text-amber-200'}`}>{STATUS_LABELS[localStatus?.state] || 'Sin comprobar'}</span>
                    </div>
                    <label className="mt-4 block text-sm text-gray-300">Modelo de Ollama
                      <select value={draft.model || ''} onChange={(event) => updateDraft(id, 'model', event.target.value)} className="mt-2 w-full rounded-lg border border-white/10 bg-black/20 px-3 py-2 text-sm text-white outline-none transition focus:border-blue-400">
                        {!selectedModelIsAvailable && draft.model && <option value={draft.model}>{draft.model} (no instalado)</option>}
                        {availableModels.map((model) => <option key={model} value={model}>{model}</option>)}
                      </select>
                    </label>
                    <label className="mt-4 block text-sm text-gray-300">URL de Ollama
                      <input type="url" value={draft.baseUrl || ''} onChange={(event) => updateDraft(id, 'baseUrl', event.target.value)} placeholder="http://localhost:11434" className="mt-2 w-full rounded-lg border border-white/10 bg-black/20 px-3 py-2 text-sm text-white outline-none transition focus:border-blue-400" />
                    </label>
                    <p className="mt-3 text-xs text-gray-400">{localStatus?.message || 'Aún no se ha comprobado este servicio.'}</p>
                    <button type="button" disabled={savingUseCase === id || phase === 'loading' || !selectedModelIsAvailable} onClick={() => void saveOllamaConfig(id)} className="mt-4 inline-flex items-center gap-2 rounded-lg bg-blue-600 px-4 py-2 text-sm font-semibold text-white hover:bg-blue-500 disabled:cursor-not-allowed disabled:opacity-50">
                      {savingUseCase === id && <Spinner size="sm" />}{savingUseCase === id ? 'Guardando…' : 'Guardar Ollama'}
                    </button>
                  </>
                ) : (
                  <>
                    <h6 className="text-sm font-medium text-white">OpenRouter · IA no local</h6>
                    <p className="mt-1 text-xs text-violet-100/70">{isEmotion ? 'Los modelos económicos son suficientes para esta clasificación estructurada.' : 'EVA requiere modelos compatibles con herramientas.'}</p>
                    <label className="mt-4 block text-sm text-gray-300">Modelos predeterminados
                      <select value="" onChange={(event) => { if (event.target.value) (isEmotion ? setOpenRouterEmotionDraft : setOpenRouterDraft)((current) => ({ ...current, model: event.target.value })); }} className="mt-2 w-full rounded-lg border border-white/10 bg-black/20 px-3 py-2 text-sm text-white outline-none transition focus:border-violet-400">
                        <option value="">Selecciona una recomendación</option>
                        {presets.map((model) => <option key={model.id} value={model.id}>{model.name} — {model.detail}</option>)}
                      </select>
                    </label>
                    <label className="mt-4 block text-sm text-gray-300">ID de modelo
                      <input list={`openrouter-${id}-models`} value={remoteDraft.model} onChange={(event) => (isEmotion ? setOpenRouterEmotionDraft : setOpenRouterDraft)((current) => ({ ...current, model: event.target.value }))} placeholder="Proveedor/modelo" className="mt-2 w-full rounded-lg border border-white/10 bg-black/20 px-3 py-2 text-sm text-white outline-none transition focus:border-violet-400" />
                      <datalist id={`openrouter-${id}-models`}>{remoteModels.map((model) => <option key={model.id} value={model.id}>{model.name}</option>)}</datalist>
                    </label>
                    <label className="mt-4 block text-sm text-gray-300">URL base avanzada
                      <input type="url" value={remoteDraft.baseUrl} onChange={(event) => (isEmotion ? setOpenRouterEmotionDraft : setOpenRouterDraft)((current) => ({ ...current, baseUrl: event.target.value }))} placeholder="https://openrouter.ai/api/v1" className="mt-2 w-full rounded-lg border border-white/10 bg-black/20 px-3 py-2 text-sm text-white outline-none transition focus:border-violet-400" />
                    </label>
                    <div className="mt-4 flex flex-wrap gap-2">
                      <button type="button" onClick={() => void loadOpenRouterModels(id)} disabled={loadingOpenRouterModels || !openRouterKeyConfigured} className="rounded-lg border border-violet-400/30 px-3 py-2 text-xs font-semibold text-violet-100 hover:bg-violet-400/10 disabled:opacity-50">{loadingOpenRouterModels ? 'Cargando modelos…' : 'Recargar modelos'}</button>
                      <button type="button" disabled={isRemoteSaving || phase === 'loading'} onClick={() => void (isEmotion ? saveOpenRouterEmotionConfig() : saveOpenRouterConfig())} className="inline-flex items-center gap-2 rounded-lg bg-violet-600 px-4 py-2 text-sm font-semibold text-white hover:bg-violet-500 disabled:cursor-not-allowed disabled:opacity-50">
                        {isRemoteSaving && <Spinner size="sm" />}{isRemoteSaving ? 'Guardando…' : 'Guardar OpenRouter'}
                      </button>
                    </div>
                  </>
                )}
              </div>
              </>}
            </div>
          );
        })}
      </div>
    </section>
  );
};

export default AiSettings;
