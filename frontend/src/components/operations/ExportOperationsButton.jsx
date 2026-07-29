import { useState } from 'react';
import { API_BASE_URL } from '../../config';

const FALLBACK_FILENAME = 'operaciones.csv';

const getDownloadFilename = (contentDisposition) => {
  if (!contentDisposition) return FALLBACK_FILENAME;

  const encodedMatch = contentDisposition.match(/filename\*=UTF-8''([^;]+)/i);
  if (encodedMatch) {
    try {
      return decodeURIComponent(encodedMatch[1].trim().replace(/^"|"$/g, ''));
    } catch {
      return FALLBACK_FILENAME;
    }
  }

  const filenameMatch = contentDisposition.match(/filename="?([^";]+)"?/i);
  return filenameMatch?.[1]?.trim() || FALLBACK_FILENAME;
};

const triggerBlobDownload = (blob, filename) => {
  const objectUrl = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = objectUrl;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(objectUrl);
};

const ExportOperationsButton = ({
  cuentaId,
  filterType = 'TODOS',
  filterActivo = 'TODOS',
  sortBy = 'fecha',
  sortDirection = 'desc',
  disabled = false,
}) => {
  const [isExporting, setIsExporting] = useState(false);
  const [error, setError] = useState('');

  const handleExport = async () => {
    if (!cuentaId || disabled || isExporting) return;

    setIsExporting(true);
    setError('');

    try {
      const params = new URLSearchParams({
        cuenta_ids: String(cuentaId),
        sort_by: sortBy,
        sort_direction: sortDirection,
      });

      if (filterType && filterType !== 'TODOS') {
        params.set('tipo_operacion', filterType);
      }
      if (filterActivo && filterActivo !== 'TODOS') {
        params.set('activo', filterActivo);
      }

      const token = sessionStorage.getItem('token');
      const response = await fetch(`${API_BASE_URL}/operaciones/export.csv?${params}`, {
        headers: token ? { Authorization: `Bearer ${token}` } : {},
      });

      if (!response.ok) {
        let message = 'No se pudieron exportar las operaciones.';
        try {
          const payload = await response.json();
          if (typeof payload.detail === 'string') message = payload.detail;
        } catch {
          // La respuesta puede no ser JSON; conservamos un mensaje util para el usuario.
        }
        throw new Error(message);
      }

      const blob = await response.blob();
      const filename = getDownloadFilename(response.headers.get('Content-Disposition'));
      triggerBlobDownload(blob, filename);
    } catch (exportError) {
      setError(exportError.message || 'No se pudieron exportar las operaciones.');
    } finally {
      setIsExporting(false);
    }
  };

  return (
    <div className="flex flex-col items-start gap-1 sm:items-end">
      <button
        type="button"
        onClick={handleExport}
        disabled={disabled || !cuentaId || isExporting}
        aria-busy={isExporting}
        className="inline-flex items-center justify-center gap-2 rounded-full border border-cyan-400/30 bg-cyan-400/10 px-4 py-2.5 text-sm font-semibold text-cyan-100 transition hover:border-cyan-300/50 hover:bg-cyan-400/20 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-cyan-300 disabled:cursor-not-allowed disabled:opacity-50"
      >
        <svg aria-hidden="true" className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 3v12m0 0 4-4m-4 4-4-4M5 19h14" />
        </svg>
        {isExporting ? 'Exportando…' : 'Exportar CSV'}
      </button>
      {error && (
        <p role="alert" className="max-w-xs text-left text-xs text-red-300 sm:text-right">
          {error}
        </p>
      )}
    </div>
  );
};

export default ExportOperationsButton;
