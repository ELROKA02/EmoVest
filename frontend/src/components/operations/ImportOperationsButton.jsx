import { useEffect, useRef, useState } from 'react';
import { apiFetch } from '../../config';

const SUCCESS_MESSAGE_DURATION_MS = 4500;
const ERROR_MESSAGE_DURATION_MS = 8000;

const readResponseBody = async (response) => {
  const responseText = await response.text();

  if (!responseText) return null;

  try {
    return JSON.parse(responseText);
  } catch {
    return responseText;
  }
};

const formatValidationIssue = (issue) => {
  if (typeof issue === 'string') return issue;

  const location = Array.isArray(issue?.loc)
    ? issue.loc.filter((part) => part !== 'body').join('.')
    : null;
  const parts = [
    issue?.row != null ? `Fila ${issue.row}` : null,
    issue?.field ? `campo «${issue.field}»` : location,
    issue?.error || issue?.msg,
  ].filter(Boolean);

  return parts.join(' · ') || 'Error de validación sin detalle';
};

const getImportError = (payload, status) => {
  const detail = payload?.detail ?? payload;

  if (typeof detail === 'string') {
    return { message: detail, issues: [] };
  }

  if (Array.isArray(detail)) {
    return {
      message: 'El archivo no ha superado la validación.',
      issues: detail.map(formatValidationIssue),
    };
  }

  if (detail && typeof detail === 'object') {
    return {
      message: detail.message || 'El CSV contiene datos no válidos.',
      issues: Array.isArray(detail.errors)
        ? detail.errors.map(formatValidationIssue)
        : [],
    };
  }

  if (typeof payload === 'string' && payload.trim()) {
    return { message: payload, issues: [] };
  }

  const statusMessages = {
    401: 'Tu sesión ha caducado. Vuelve a iniciar sesión para importar operaciones.',
    404: 'No se ha encontrado la cuenta seleccionada.',
    422: 'El CSV no tiene el formato esperado.',
  };

  return {
    message: statusMessages[status] || 'No se pudo importar el archivo CSV.',
    issues: [],
  };
};

const ImportOperationsButton = ({ cuentaId, disabled = false, onImported }) => {
  const inputRef = useRef(null);
  const [isImporting, setIsImporting] = useState(false);
  const [successMessage, setSuccessMessage] = useState('');
  const [error, setError] = useState(null);

  const isDisabled = disabled || isImporting || !cuentaId;

  useEffect(() => {
    if (!successMessage) return undefined;

    const timeoutId = window.setTimeout(() => {
      setSuccessMessage('');
    }, SUCCESS_MESSAGE_DURATION_MS);

    return () => window.clearTimeout(timeoutId);
  }, [successMessage]);

  useEffect(() => {
    if (!error) return undefined;

    const timeoutId = window.setTimeout(() => {
      setError(null);
    }, ERROR_MESSAGE_DURATION_MS);

    return () => window.clearTimeout(timeoutId);
  }, [error]);

  const openFilePicker = () => {
    if (isDisabled) return;

    setError(null);
    setSuccessMessage('');

    // Limpiarlo antes de abrir permite volver a seleccionar el mismo archivo.
    inputRef.current.value = '';
    inputRef.current.click();
  };

  const importFile = async (event) => {
    const file = event.target.files?.[0];

    // También se limpia aquí para permitir reintentar el mismo CSV tras un error.
    event.target.value = '';
    if (!file) return;

    if (!file.name.toLowerCase().endsWith('.csv')) {
      setSuccessMessage('');
      setError({ message: 'Selecciona un archivo con extensión .csv.', issues: [] });
      return;
    }

    if (!cuentaId) {
      setSuccessMessage('');
      setError({ message: 'Selecciona una cuenta antes de importar.', issues: [] });
      return;
    }

    const formData = new FormData();
    formData.append('cuenta_id', String(cuentaId));
    formData.append('file', file);

    const token = sessionStorage.getItem('token');
    setIsImporting(true);
    setError(null);
    setSuccessMessage('');

    try {
      const response = await apiFetch('/operaciones/import.csv', {
        method: 'POST',
        headers: token ? { Authorization: `Bearer ${token}` } : {},
        body: formData,
      });
      const payload = await readResponseBody(response);

      if (!response.ok) {
        setError(getImportError(payload, response.status));
        return;
      }

      const createdCount = Number(payload?.created_count) || 0;
      setSuccessMessage(
        `Importación completada: ${createdCount} ${createdCount === 1 ? 'operación importada' : 'operaciones importadas'}.`,
      );

      if (onImported) {
        try {
          await onImported(payload);
        } catch (callbackError) {
          console.error('Las operaciones se importaron, pero no se pudo refrescar la lista:', callbackError);
        }
      }
    } catch {
      setError({
        message: 'No se pudo conectar con el servidor para importar el CSV.',
        issues: [],
      });
    } finally {
      setIsImporting(false);
    }
  };

  return (
    <div className="inline-flex max-w-full items-start">
      <input
        ref={inputRef}
        type="file"
        accept=".csv,text/csv"
        onChange={importFile}
        disabled={isDisabled}
        className="sr-only"
        aria-label="Seleccionar CSV de operaciones para importar"
      />

      <button
        type="button"
        onClick={openFilePicker}
        disabled={isDisabled}
        aria-busy={isImporting}
        className="inline-flex min-h-11 min-w-44 items-center justify-center gap-2 rounded-full border border-slate-500/70 bg-slate-800/80 px-5 py-2.5 text-sm font-semibold text-slate-100 transition-all duration-200 hover:border-blue-400/70 hover:bg-slate-700/90 hover:text-white focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-400 focus-visible:ring-offset-2 focus-visible:ring-offset-slate-950 disabled:cursor-not-allowed disabled:opacity-50"
      >
        {isImporting ? (
          <svg className="h-4 w-4 animate-spin" viewBox="0 0 24 24" fill="none" aria-hidden="true">
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
            <path className="opacity-90" fill="currentColor" d="M4 12a8 8 0 018-8V0A12 12 0 000 12h4Z" />
          </svg>
        ) : (
          <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 16V4m0 0L8 8m4-4 4 4M4 15v3a2 2 0 002 2h12a2 2 0 002-2v-3" />
          </svg>
        )}
        {isImporting ? 'Importando…' : 'CSV de EmoVest'}
      </button>

      {successMessage && (
        <p
          className="fixed bottom-6 left-1/2 z-[10002] w-max max-w-[calc(100vw-2rem)] -translate-x-1/2 rounded-xl border border-emerald-400/30 bg-slate-950/95 px-4 py-3 text-sm font-medium text-emerald-300 shadow-2xl backdrop-blur-xl"
          role="status"
          aria-live="polite"
        >
          {successMessage}
        </p>
      )}

      {error && (
        <div
          className="fixed bottom-6 left-1/2 z-[10002] max-h-64 w-max max-w-[calc(100vw-2rem)] -translate-x-1/2 overflow-y-auto rounded-xl border border-red-400/30 bg-red-950/95 px-4 py-3 text-sm text-red-200 shadow-2xl backdrop-blur-xl"
          role="alert"
        >
          <p>{error.message}</p>
          {error.issues.length > 0 && (
            <ul className="mt-1 max-h-40 list-disc space-y-0.5 overflow-y-auto pl-5 text-xs text-red-200/90">
              {error.issues.map((issue, index) => (
                <li key={`${issue}-${index}`}>{issue}</li>
              ))}
            </ul>
          )}
        </div>
      )}
    </div>
  );
};

export default ImportOperationsButton;
