import React, { useEffect, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import Sidebar from './Sidebar';
import { API_BASE_URL } from '../config';
import useChatMemory from '../context/useChatMemory';
import { fetchAndStoreUserName } from '../utils/userSession';
import evaAvatar from '../assets/eva-avatar.png';

const MAX_MESSAGE_LENGTH = 4000;
const GENERIC_CHAT_ERROR = 'No se pudo completar la respuesta de EVA. Inténtalo de nuevo.';
const WELCOME_TEXT = 'Hola, soy EVA. Puedo ayudarte a analizar tus resultados, operaciones y patrones emocionales. ¿Qué quieres revisar?';

let messageSequence = 0;

const nextMessageId = () => {
  messageSequence += 1;
  return `chat-message-${Date.now()}-${messageSequence}`;
};

const parseSseBlock = (block) => {
  let event = 'message';
  const dataLines = [];

  block.split(/\r?\n/).forEach((line) => {
    if (!line || line.startsWith(':')) return;
    const separator = line.indexOf(':');
    const field = separator === -1 ? line : line.slice(0, separator);
    let value = separator === -1 ? '' : line.slice(separator + 1);
    if (value.startsWith(' ')) value = value.slice(1);

    if (field === 'event') event = value;
    if (field === 'data') dataLines.push(value);
  });

  if (dataLines.length === 0) return null;

  try {
    return { event, data: JSON.parse(dataLines.join('\n')) };
  } catch {
    throw new Error('El servidor devolvió un evento de chat no válido.');
  }
};

const formatNumber = (value) => {
  if (typeof value !== 'number') return String(value);
  return new Intl.NumberFormat('es-ES', { maximumFractionDigits: 2 }).format(value);
};

const formatAccountBalance = (account) => {
  if (typeof account.balance !== 'number') return account.currency || '';
  try {
    return new Intl.NumberFormat('es-ES', {
      style: 'currency',
      currency: account.currency || 'EUR',
      maximumFractionDigits: 2,
    }).format(account.balance);
  } catch {
    return `${formatNumber(account.balance)} ${account.currency || ''}`.trim();
  }
};

const TOOL_NAMES = {
  resumen_resultados: 'Resumen de resultados',
  buscar_operaciones: 'Operaciones consultadas',
  detalle_operacion: 'Detalle de operación',
  analizar_emociones: 'Análisis emocional',
};

const MARKDOWN_PLUGINS = [remarkGfm];

const MARKDOWN_COMPONENTS = {
  h1: ({ children }) => <h1 className="mb-3 mt-5 text-xl font-bold leading-tight first:mt-0">{children}</h1>,
  h2: ({ children }) => <h2 className="mb-3 mt-5 text-lg font-bold leading-tight first:mt-0">{children}</h2>,
  h3: ({ children }) => <h3 className="mb-2 mt-4 text-base font-semibold leading-snug first:mt-0">{children}</h3>,
  h4: ({ children }) => <h4 className="mb-2 mt-4 text-sm font-semibold leading-snug first:mt-0">{children}</h4>,
  p: ({ children }) => <p className="my-3 leading-6 first:mt-0 last:mb-0">{children}</p>,
  ul: ({ children }) => <ul className="my-3 list-disc space-y-2 pl-5 marker:text-violet-400">{children}</ul>,
  ol: ({ children }) => <ol className="my-3 list-decimal space-y-2 pl-5 marker:font-semibold marker:text-violet-400">{children}</ol>,
  li: ({ children }) => <li className="pl-1 leading-6 [&>p]:my-0">{children}</li>,
  strong: ({ children }) => <strong className="font-bold text-violet-400">{children}</strong>,
  em: ({ children }) => <em className="text-gray-200">{children}</em>,
  blockquote: ({ children }) => (
    <blockquote className="my-4 border-l-2 border-violet-400/60 bg-violet-500/10 px-4 py-2 text-gray-300">
      {children}
    </blockquote>
  ),
  hr: () => <hr className="my-5 border-white/10" />,
  table: ({ children }) => (
    <div className="my-4 max-w-full overflow-x-auto rounded-xl border border-white/10">
      <table className="w-full min-w-max border-collapse text-left text-xs sm:text-sm">{children}</table>
    </div>
  ),
  thead: ({ children }) => <thead className="bg-white/10 text-gray-100">{children}</thead>,
  tbody: ({ children }) => <tbody className="divide-y divide-white/10">{children}</tbody>,
  tr: ({ children }) => <tr className="even:bg-white/[0.03]">{children}</tr>,
  th: ({ children }) => <th className="whitespace-nowrap px-3 py-2 font-semibold">{children}</th>,
  td: ({ children }) => <td className="whitespace-nowrap px-3 py-2 text-gray-300">{children}</td>,
  a: ({ children, href }) => (
    <a
      href={href}
      target="_blank"
      rel="noreferrer noopener"
      className="text-violet-300 underline decoration-violet-400/40 underline-offset-2 hover:text-violet-200"
    >
      {children}
    </a>
  ),
  pre: ({ children }) => (
    <pre className="my-4 max-w-full overflow-x-auto rounded-xl border border-white/10 bg-black/35 p-3 text-xs leading-5">
      {children}
    </pre>
  ),
  code: ({ children }) => (
    <code className="rounded bg-black/30 px-1.5 py-0.5 font-mono text-[0.9em] text-violet-100">{children}</code>
  ),
};

const MarkdownMessage = ({ children }) => (
  <div className="min-w-0 break-words text-sm sm:text-[15px]">
    <ReactMarkdown
      remarkPlugins={MARKDOWN_PLUGINS}
      components={MARKDOWN_COMPONENTS}
      skipHtml
    >
      {children}
    </ReactMarkdown>
  </div>
);

const evidenceRows = (item) => {
  const rows = [];
  const accountName = item.account && typeof item.account === 'object' ? item.account.name : null;

  if (accountName) rows.push(['Cuenta', accountName]);
  else if (item.account_id) rows.push(['Cuenta', `#${item.account_id}`]);
  if (typeof item.period_days === 'number') rows.push(['Periodo', `${item.period_days} días`]);
  if (typeof item.operations === 'number') rows.push(['Operaciones', formatNumber(item.operations)]);
  if (typeof item.pnl === 'number') rows.push(['Resultado', formatNumber(item.pnl)]);
  if (typeof item.wins === 'number') rows.push(['Ganadoras', formatNumber(item.wins)]);
  if (typeof item.losses === 'number') rows.push(['Perdedoras', formatNumber(item.losses)]);
  if (typeof item.average_rr === 'number') rows.push(['RR medio', formatNumber(item.average_rr)]);
  if (typeof item.records === 'number') rows.push(['Registros emocionales', formatNumber(item.records)]);
  if (Array.isArray(item.operation_ids) && item.operation_ids.length > 0) {
    rows.push(['Operaciones', item.operation_ids.map((id) => `#${id}`).join(', ')]);
  }
  if (item.averages && typeof item.averages === 'object') {
    Object.entries(item.averages).forEach(([emotion, value]) => {
      if (typeof value === 'number') {
        rows.push([`Media de ${emotion}`, formatNumber(value)]);
      }
    });
  }

  return rows;
};

const EvidencePanel = ({ items }) => {
  if (!Array.isArray(items) || items.length === 0) return null;

  return (
    <details className="mt-3 rounded-xl border border-white/10 bg-black/20 px-4 py-3 text-sm text-gray-300">
      <summary className="cursor-pointer select-none font-medium text-violet-300">
        Datos consultados ({items.length})
      </summary>
      <div className="mt-3 space-y-3">
        {items.map((item, index) => {
          const rows = evidenceRows(item);
          if (rows.length === 0) return null;
          return (
            <div key={`${item.tool || 'evidence'}-${index}`} className="rounded-lg bg-white/5 p-3">
              <p className="mb-2 font-semibold text-gray-200">
                {TOOL_NAMES[item.tool] || 'Consulta de EVA'}
              </p>
              <dl className="grid grid-cols-[auto_1fr] gap-x-3 gap-y-1 text-xs">
                {rows.map(([label, value]) => (
                  <React.Fragment key={`${label}-${value}`}>
                    <dt className="text-gray-500">{label}</dt>
                    <dd className="min-w-0 break-words text-right text-gray-300">{value}</dd>
                  </React.Fragment>
                ))}
              </dl>
            </div>
          );
        })}
      </div>
    </details>
  );
};

const ChatIA = () => {
  const navigate = useNavigate();
  const [sidebarOpen, setSidebarOpen] = useState(() => {
    if (window.innerWidth < 768) return false;
    const saved = localStorage.getItem('sidebarOpen');
    return saved !== null ? JSON.parse(saved) : true;
  });
  const [userName, setUserName] = useState(localStorage.getItem('userName') || 'Usuario');
  const {
    messages,
    setMessages,
    input,
    setInput,
    accountId,
    setAccountId,
    accountName,
    setAccountName,
    pendingQuestion,
    setPendingQuestion,
    isStreaming,
    setIsStreaming,
    isResetting,
    setIsResetting,
    statusText,
    setStatusText,
    sessionIdRef,
    currentRequestRef,
    chatOwnerTokenRef,
    clearChatMemory,
  } = useChatMemory();

  const messagesEndRef = useRef(null);
  const textareaRef = useRef(null);

  const bgGradient = {
    background: 'radial-gradient(circle at center, #1a364d 0%, #10202d 50%, #101422 100%)',
  };

  useEffect(() => {
    const token = sessionStorage.getItem('token');
    if (!token) {
      clearChatMemory();
      chatOwnerTokenRef.current = null;
      navigate('/login', { replace: true });
      return undefined;
    }
    if (chatOwnerTokenRef.current && chatOwnerTokenRef.current !== token) {
      clearChatMemory();
    }
    chatOwnerTokenRef.current = token;

    let mounted = true;
    fetchAndStoreUserName()
      .then((name) => {
        if (mounted && name) setUserName(name);
      })
      .catch(() => {
        // El chat sigue siendo usable con el nombre local mientras el token sea valido.
      });

    return () => {
      mounted = false;
    };
  }, [chatOwnerTokenRef, clearChatMemory, navigate]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth', block: 'end' });
  }, [messages, statusText]);

  const redirectToLogin = () => {
    clearChatMemory();
    chatOwnerTokenRef.current = null;
    sessionStorage.removeItem('token');
    localStorage.removeItem('userName');
    navigate('/login', { replace: true });
  };

  const updateAssistantMessage = (messageId, updater) => {
    setMessages((current) => current.map((message) => (
      message.id === messageId ? updater(message) : message
    )));
  };

  const sendMessage = async (rawMessage, options = {}) => {
    const message = rawMessage.trim();
    if (!message || message.length > MAX_MESSAGE_LENGTH || isStreaming) return;

    const token = sessionStorage.getItem('token');
    if (!token) {
      redirectToLogin();
      return;
    }

    const displayUser = options.displayUser !== false;
    const effectiveAccountId = options.accountOverride ?? accountId;
    const effectiveSessionId = options.sessionOverride ?? sessionIdRef.current;
    const assistantId = nextMessageId();
    const controller = new AbortController();
    let receivedText = '';
    let terminalEventReceived = false;

    if (displayUser) {
      setMessages((current) => [...current, {
        id: nextMessageId(),
        role: 'user',
        text: message,
        evidence: [],
      }]);
      if (!effectiveAccountId) setPendingQuestion(message);
    }

    setMessages((current) => [...current, {
      id: assistantId,
      role: 'assistant',
      text: '',
      evidence: [],
      pending: true,
    }]);
    setIsStreaming(true);
    setStatusText('EVA está consultando…');
    currentRequestRef.current = controller;

    const retryPayload = {
      message,
      accountId: effectiveAccountId,
    };

    try {
      const payload = { mensaje: message };
      if (effectiveSessionId) payload.session_id = effectiveSessionId;
      if (effectiveAccountId) payload.account_id = effectiveAccountId;

      const response = await fetch(`${API_BASE_URL}/ia/chat/mensajes`, {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${token}`,
          'Content-Type': 'application/json',
          Accept: 'text/event-stream',
        },
        body: JSON.stringify(payload),
        signal: controller.signal,
      });

      if (response.status === 401) {
        redirectToLogin();
        return;
      }
      if (!response.ok || !response.body) {
        throw new Error(GENERIC_CHAT_ERROR);
      }
      const contentType = response.headers.get('content-type') || '';
      if (!contentType.includes('text/event-stream')) {
        throw new Error('El servidor no devolvió una respuesta de chat válida.');
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';

      const consumeEvent = (parsed) => {
        if (!parsed) return;
        const { event, data } = parsed;

        if (!data || typeof data !== 'object') {
          throw new Error('El servidor devolvió un evento de chat no válido.');
        }

        if (event === 'session') {
          if (typeof data.session_id !== 'string' || !data.session_id) {
            throw new Error('El servidor devolvió una sesión de chat no válida.');
          }
          sessionIdRef.current = data.session_id;
          return;
        }

        if (event === 'status') {
          setStatusText('EVA está consultando…');
          return;
        }

        if (event === 'delta') {
          if (typeof data.text !== 'string') {
            throw new Error('El servidor devolvió un mensaje de chat no válido.');
          }
          receivedText += data.text;
          updateAssistantMessage(assistantId, (current) => ({
            ...current,
            text: receivedText,
          }));
          return;
        }

        if (event === 'evidence') {
          if (!Array.isArray(data.items)) {
            throw new Error('El servidor devolvió evidencias no válidas.');
          }
          const accountEvidence = data.items.find((item) => (
            item && item.tool === 'cuentas' && Array.isArray(item.accounts)
          ));
          const analyticalEvidence = data.items.filter((item) => item && item.tool !== 'cuentas');
          updateAssistantMessage(assistantId, (current) => ({
            ...current,
            evidence: analyticalEvidence,
            accountOptions: accountEvidence ? accountEvidence.accounts : current.accountOptions,
          }));
          return;
        }

        if (event === 'done') {
          terminalEventReceived = true;
          updateAssistantMessage(assistantId, (current) => ({ ...current, pending: false }));
          setStatusText('');
          return;
        }

        if (event === 'error') {
          terminalEventReceived = true;
          const safeMessage = typeof data.message === 'string' && data.message.trim()
            ? data.message
            : GENERIC_CHAT_ERROR;
          throw new Error(safeMessage);
        }

        throw new Error('El servidor devolvió un evento de chat desconocido.');
      };

      while (true) {
        const { value, done } = await reader.read();
        buffer += decoder.decode(value || new Uint8Array(), { stream: !done });

        let separator = buffer.match(/\r?\n\r?\n/);
        while (separator) {
          const block = buffer.slice(0, separator.index);
          buffer = buffer.slice(separator.index + separator[0].length);
          consumeEvent(parseSseBlock(block));
          separator = buffer.match(/\r?\n\r?\n/);
        }

        if (done) break;
      }

      if (buffer.trim()) consumeEvent(parseSseBlock(buffer.trim()));
      if (!terminalEventReceived) {
        throw new Error('La respuesta de EVA se interrumpió antes de terminar.');
      }
    } catch (error) {
      if (error.name === 'AbortError') return;
      const errorMessage = error.message || GENERIC_CHAT_ERROR;

      setMessages((current) => {
        const target = current.find((item) => item.id === assistantId);
        const completedMessages = current.map((item) => (
          item.id === assistantId ? { ...item, pending: false } : item
        ));

        if (target?.text) {
          return [...completedMessages, {
            id: nextMessageId(),
            role: 'error',
            text: errorMessage,
            retryPayload,
            evidence: [],
          }];
        }

        return completedMessages.map((item) => (
          item.id === assistantId
            ? { ...item, role: 'error', text: errorMessage, retryPayload, evidence: [] }
            : item
        ));
      });
      setStatusText('');
    } finally {
      if (currentRequestRef.current === controller) {
        currentRequestRef.current = null;
        setIsStreaming(false);
        setStatusText('');
      }
    }
  };

  const submitCurrentMessage = () => {
    const message = input.trim();
    if (!message || message.length > MAX_MESSAGE_LENGTH || isStreaming) return;
    setInput('');
    if (textareaRef.current) textareaRef.current.style.height = 'auto';
    void sendMessage(message);
  };

  const selectAccount = (account) => {
    if (isStreaming || !account || typeof account.id !== 'number') return;

    setAccountId(account.id);
    setAccountName(account.name || `Cuenta #${account.id}`);
    setMessages((current) => [
      ...current.map((message) => (
        Array.isArray(message.accountOptions) ? { ...message, accountOptions: null } : message
      )),
      {
        id: nextMessageId(),
        role: 'user',
        text: `Cuenta seleccionada: ${account.name || `#${account.id}`}`,
        evidence: [],
      },
    ]);

    const continuation = pendingQuestion
      ? 'Ya he seleccionado la cuenta. Responde ahora a mi pregunta anterior.'
      : 'Analiza la cuenta que acabo de seleccionar.';
    void sendMessage(continuation, {
      displayUser: false,
      accountOverride: account.id,
      sessionOverride: sessionIdRef.current,
    });
  };

  const retryMessage = (message) => {
    if (isStreaming || !message.retryPayload) return;
    setMessages((current) => current.filter((item) => item.id !== message.id));
    void sendMessage(message.retryPayload.message, {
      displayUser: false,
      accountOverride: message.retryPayload.accountId,
      sessionOverride: sessionIdRef.current,
    });
  };

  const resetConversation = async () => {
    const previousSessionId = sessionIdRef.current;
    const token = sessionStorage.getItem('token');

    clearChatMemory();
    setIsResetting(true);

    try {
      if (previousSessionId && token) {
        const response = await fetch(`${API_BASE_URL}/ia/chat/sesiones/${encodeURIComponent(previousSessionId)}`, {
          method: 'DELETE',
          headers: { Authorization: `Bearer ${token}` },
        });
        if (response.status === 401) {
          redirectToLogin();
          return;
        }
        if (!response.ok && response.status !== 404) {
          throw new Error('No se pudo cerrar la sesión anterior, pero puedes iniciar una conversación nueva.');
        }
      }
    } catch (error) {
      setMessages((current) => [...current, {
        id: nextMessageId(),
        role: 'error',
        text: error.message || 'No se pudo cerrar la sesión anterior.',
        evidence: [],
      }]);
    } finally {
      setIsResetting(false);
      textareaRef.current?.focus();
    }
  };

  const handleLogout = () => {
    clearChatMemory();
    chatOwnerTokenRef.current = null;
    sessionStorage.removeItem('token');
    localStorage.removeItem('rememberedEmail');
    localStorage.removeItem('userName');
    navigate('/login');
  };

  return (
    <div className="flex h-screen min-h-screen text-white" style={bgGradient}>
      <Sidebar sidebarOpen={sidebarOpen} onToggle={() => setSidebarOpen((open) => !open)} />

      <div className="relative flex min-w-0 flex-1 flex-col overflow-hidden">
        <header className="sticky top-0 z-40 flex items-center justify-between gap-4 border-b border-white/10 bg-black/30 px-4 py-4 backdrop-blur-xl sm:px-6">
          <div className="flex min-w-0 items-center gap-4">
            <button
              type="button"
              onClick={() => setSidebarOpen((open) => !open)}
              className="flex-shrink-0 text-gray-300 transition-colors hover:text-white"
              aria-label={sidebarOpen ? 'Contraer menú lateral' : 'Expandir menú lateral'}
            >
              <svg className="h-6 w-6" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
              </svg>
            </button>
            <h2 className="truncate text-xl font-semibold text-white">EVA · Analista IA</h2>
          </div>

          <div className="flex flex-shrink-0 items-center gap-2 sm:gap-4 xl:gap-8">
            {accountName && (
              <button
                type="button"
                onClick={resetConversation}
                disabled={isResetting}
                className="hidden max-w-44 truncate rounded-full border border-violet-400/30 bg-violet-500/10 px-3 py-2 text-xs font-medium text-violet-200 transition hover:bg-violet-500/20 disabled:opacity-50 md:block"
                title="Cambiar cuenta iniciando una conversación nueva"
              >
                {accountName} · Cambiar
              </button>
            )}
            <button
              type="button"
              onClick={resetConversation}
              disabled={isResetting}
              className="flex items-center gap-2 rounded-full border border-white/10 bg-white/5 px-3 py-2 text-sm text-gray-200 transition hover:bg-white/10 disabled:cursor-not-allowed disabled:opacity-50"
              title="Nueva conversación"
            >
              <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
              </svg>
              <span className="hidden lg:inline">Nueva conversación</span>
            </button>
            <button
              type="button"
              onClick={() => navigate('/perfil')}
              className="hidden items-center gap-2 text-gray-300 transition-colors hover:text-white sm:flex"
              title="Ver perfil"
            >
              <svg className="h-8 w-8" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
              </svg>
              <span className="hidden font-medium lg:inline">{userName}</span>
            </button>
            <button
              type="button"
              onClick={handleLogout}
              className="flex items-center gap-2 rounded-full bg-red-600 px-4 py-2 font-semibold text-white transition-all duration-300 hover:bg-red-700"
              title="Cerrar sesión"
              aria-label="Cerrar sesión"
            >
              <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1" />
              </svg>
              <span className="hidden lg:inline">Cerrar Sesión</span>
            </button>
          </div>
        </header>

        <main className="min-h-0 flex-1 overflow-y-auto px-4 pb-44 pt-6 sm:px-6 sm:pb-48 sm:pt-8">
          <div
            className={`mx-auto flex w-full max-w-3xl flex-col ${messages.length === 0 ? 'min-h-full items-center justify-center pb-8 text-center' : 'gap-5'}`}
            role="log"
            aria-live="polite"
            aria-label="Conversación con EVA"
          >
            {messages.length === 0 ? (
              <div className="flex max-w-xl flex-col items-center">
                <img
                  src={evaAvatar}
                  alt="EVA, analista de inteligencia artificial"
                  className="h-40 w-40 rounded-full object-cover shadow-[0_0_55px_rgba(168,85,247,0.3)] sm:h-52 sm:w-52"
                />
                <p className="mt-5 text-balance text-base leading-7 text-gray-200 sm:text-lg">
                  {WELCOME_TEXT}
                </p>
              </div>
            ) : messages.map((message) => (
              <div
                key={message.id}
                className={`flex gap-3 ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}
              >
                {message.role !== 'user' && (
                  <div className={`mt-1 flex h-10 w-10 flex-shrink-0 items-center justify-center overflow-hidden rounded-full border ${message.role === 'error' ? 'border-red-400/30 bg-red-500/15 text-red-300' : 'border-purple-400/40 bg-purple-500/10 shadow-[0_0_18px_rgba(168,85,247,0.2)]'}`}>
                    {message.role === 'error' ? (
                      <span className="font-bold" aria-hidden="true">!</span>
                    ) : (
                      <img src={evaAvatar} alt="" className="h-full w-full object-cover" />
                    )}
                  </div>
                )}

                <div className={`relative min-w-0 max-w-[86%] rounded-2xl px-4 py-3 shadow-lg sm:max-w-[78%] ${
                  message.role === 'user'
                    ? 'rounded-br-md bg-violet-600 text-white'
                    : message.role === 'error'
                      ? 'rounded-bl-md border border-red-500/30 bg-red-500/10 text-red-100'
                      : message.pending && !message.text
                        ? 'eva-thinking-bubble rounded-bl-md border border-violet-300/30 bg-white/5 text-gray-100 backdrop-blur-xl'
                        : 'rounded-bl-md border border-white/10 bg-white/5 text-gray-100 backdrop-blur-xl'
                }`}>
                  {message.pending && !message.text ? (
                    <div className="flex items-center gap-2 text-sm text-gray-300" role="status">
                      <span className="h-2 w-2 animate-pulse rounded-full bg-violet-400" />
                      EVA está consultando…
                    </div>
                  ) : message.role === 'assistant' ? (
                    <MarkdownMessage>{message.text}</MarkdownMessage>
                  ) : (
                    <p className="whitespace-pre-wrap break-words text-sm leading-6 sm:text-[15px]">{message.text}</p>
                  )}

                  {Array.isArray(message.accountOptions) && (
                    <div className="mt-4 space-y-2">
                      {message.accountOptions.length > 0 ? (
                        <>
                          <p className="text-xs font-medium uppercase tracking-wide text-gray-400">Selecciona una cuenta</p>
                          <div className="grid gap-2 sm:grid-cols-2">
                            {message.accountOptions.map((account) => (
                              <button
                                key={account.id}
                                type="button"
                                onClick={() => selectAccount(account)}
                                disabled={isStreaming}
                                className="rounded-xl border border-violet-400/25 bg-violet-500/10 p-3 text-left transition hover:border-violet-400/50 hover:bg-violet-500/20 disabled:cursor-not-allowed disabled:opacity-50"
                              >
                                <span className="block truncate text-sm font-semibold text-violet-100">{account.name || `Cuenta #${account.id}`}</span>
                                <span className="mt-1 block text-xs text-gray-400">{formatAccountBalance(account)}</span>
                              </button>
                            ))}
                          </div>
                        </>
                      ) : (
                        <div className="rounded-xl border border-dashed border-white/15 p-4 text-center">
                          <p className="text-sm text-gray-300">Todavía no tienes cuentas de trading.</p>
                          <button
                            type="button"
                            onClick={() => navigate('/dashboard')}
                            className="mt-3 rounded-full bg-violet-600 px-4 py-2 text-xs font-semibold text-white transition hover:bg-violet-700"
                          >
                            Crear una cuenta en el Tablero
                          </button>
                        </div>
                      )}
                    </div>
                  )}

                  <EvidencePanel items={message.evidence} />

                  {message.role === 'error' && message.retryPayload && (
                    <button
                      type="button"
                      onClick={() => retryMessage(message)}
                      disabled={isStreaming}
                      className="mt-3 rounded-full border border-red-400/40 px-3 py-1.5 text-xs font-semibold text-red-100 transition hover:bg-red-500/20 disabled:opacity-50"
                    >
                      Reintentar
                    </button>
                  )}
                </div>
              </div>
            ))}
            <div ref={messagesEndRef} />
          </div>
        </main>

        <div className="pointer-events-none absolute inset-x-0 bottom-0 z-30 px-4 pb-3 pt-20 sm:px-6 sm:pb-4 sm:pt-24">
          <div
            aria-hidden="true"
            className="absolute inset-0 bg-gradient-to-b from-transparent via-slate-950/10 to-slate-950/45 backdrop-blur-xl"
            style={{
              WebkitMaskImage: 'linear-gradient(to bottom, transparent 0%, rgba(0,0,0,.25) 28%, black 72%)',
              maskImage: 'linear-gradient(to bottom, transparent 0%, rgba(0,0,0,.25) 28%, black 72%)',
            }}
          />
          <form
            className="pointer-events-auto relative mx-auto w-full max-w-3xl"
            onSubmit={(event) => {
              event.preventDefault();
              submitCurrentMessage();
            }}
          >
            <div className="flex items-end gap-2 rounded-2xl border border-white/25 bg-gradient-to-br from-white/[0.14] via-white/[0.08] to-violet-400/[0.06] p-2 shadow-[inset_0_1px_0_rgba(255,255,255,0.12),0_16px_50px_rgba(0,0,0,0.32)] backdrop-blur-2xl backdrop-saturate-150 transition focus-within:border-violet-300/60 focus-within:from-white/[0.18] focus-within:via-white/[0.11]">
              <textarea
                ref={textareaRef}
                value={input}
                onChange={(event) => {
                  setInput(event.target.value);
                  event.target.style.height = 'auto';
                  event.target.style.height = `${Math.min(event.target.scrollHeight, 144)}px`;
                }}
                onKeyDown={(event) => {
                  if (event.key === 'Enter' && !event.shiftKey) {
                    event.preventDefault();
                    submitCurrentMessage();
                  }
                }}
                maxLength={MAX_MESSAGE_LENGTH}
                rows={1}
                disabled={isStreaming || isResetting}
                placeholder="Escribe un mensaje para EVA…"
                aria-label="Mensaje para EVA"
                className="max-h-36 min-h-11 flex-1 resize-none bg-transparent px-3 py-2.5 text-sm leading-6 text-white outline-none placeholder:text-gray-500 disabled:cursor-not-allowed disabled:opacity-60 sm:text-[15px]"
              />
              <button
                type="submit"
                disabled={!input.trim() || isStreaming || isResetting}
                className="flex h-11 w-11 flex-shrink-0 items-center justify-center rounded-xl bg-violet-600 text-white transition hover:bg-violet-700 disabled:cursor-not-allowed disabled:bg-gray-700 disabled:text-gray-400"
                aria-label="Enviar mensaje"
              >
                <svg className="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 12h14m-6-6l6 6-6 6" />
                </svg>
              </button>
            </div>
            <div className="mt-2 flex items-center justify-between px-1 text-[11px] text-gray-500">
              <span>EVA ofrece análisis educativo, no señales de compra o venta.</span>
              <span className={input.length > 3600 ? 'text-amber-300' : ''}>{input.length}/{MAX_MESSAGE_LENGTH}</span>
            </div>
          </form>
        </div>
      </div>
    </div>
  );
};

export default ChatIA;
