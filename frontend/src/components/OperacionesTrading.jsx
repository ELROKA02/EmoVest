import React, { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import Sidebar from './Sidebar';
import CustomSelect from './CustomSelect';
import { fetchAndStoreUserName } from '../utils/userSession';
import { formatCurrency } from '../utils/currency';
import { apiFetch, createAuthenticatedObjectUrl } from '../config';
import { LoadingState, ErrorState, EmptyState } from './ui';
import ImportOperationsButton from './operations/ImportOperationsButton';
import ExportOperationsButton from './operations/ExportOperationsButton';

const getAuthHeaders = ({ isJson = true } = {}) => {
  const token = sessionStorage.getItem('token');
  const headers = {
    ...(token && { 'Authorization': `Bearer ${token}` })
  };

  if (isJson) {
    headers['Content-Type'] = 'application/json';
  }

  return headers;
};

const revokeBlobUrl = (url) => {
  if (url && url.startsWith('blob:')) {
    URL.revokeObjectURL(url);
  }
};

const toLocalDatetimeInputValue = (date) => {
  const pad = (n) => String(n).padStart(2, '0');
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}T${pad(date.getHours())}:${pad(date.getMinutes())}`;
};

const parseNumericField = (value) => {
  const parsed = parseFloat(value);
  return Number.isFinite(parsed) ? parsed : null;
};

const calculateRiskRewardRatio = ({ tipo_operacion, precio_entrada, stop_loss, take_profit }) => {
  const entry = parseNumericField(precio_entrada);
  const stopLoss = parseNumericField(stop_loss);
  const takeProfit = parseNumericField(take_profit);

  if (entry === null || stopLoss === null || takeProfit === null) {
    return '';
  }

  const isLong = tipo_operacion === 'LONG';
  const risk = isLong ? entry - stopLoss : stopLoss - entry;
  const reward = isLong ? takeProfit - entry : entry - takeProfit;

  if (risk <= 0 || reward <= 0) {
    return '';
  }

  return (reward / risk).toFixed(2);
};

const InfoIcon = ({ text }) => {
  const [alignRight, setAlignRight] = useState(false);
  const iconRef = useRef(null);

  const handlePointerEnter = () => {
    if (!iconRef.current) return;
    const rect = iconRef.current.getBoundingClientRect();
    const tooltipWidth = 288; // w-64
    const formElement = iconRef.current.closest('form');

    if (!formElement) {
      const rightSpace = window.innerWidth - rect.right;
      const leftSpace = rect.left;
      setAlignRight(rightSpace < tooltipWidth && leftSpace > tooltipWidth);
      return;
    }

    const formRect = formElement.getBoundingClientRect();
    const rightSpace = formRect.right - rect.right;
    const leftSpace = rect.left - formRect.left;
    setAlignRight(rightSpace < tooltipWidth && leftSpace > tooltipWidth);
  };

  return (
    <div ref={iconRef} className="relative group inline-flex items-center overflow-visible" onPointerEnter={handlePointerEnter}>
      <svg className="w-3.5 h-3.5 text-gray-400 hover:text-blue-400 cursor-help transition-colors" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
      </svg>
      <div className={`absolute bottom-full mb-2 hidden group-hover:block w-64 max-w-[18rem] break-words whitespace-normal p-2 bg-[#1a2235] border border-white/10 text-[10px] text-gray-300 rounded shadow-xl z-50 pointer-events-none ${alignRight ? 'right-0 text-right' : 'left-0 text-left'}`}>
        {text}
        <div className={`absolute top-full border-4 border-transparent border-t-[#1a2235] ${alignRight ? 'right-4' : 'left-4'}`}></div>
      </div>
    </div>
  );
};

const OperacionesTrading = () => {
  console.log('OperacionesTrading renderizado');

  // Obtener estado del sidebar desde localStorage o usar true por defecto
  const [sidebarOpen, setSidebarOpen] = useState(() => {
    const saved = localStorage.getItem('sidebarOpen');
    return saved !== null ? JSON.parse(saved) : true;
  });
  const navigate = useNavigate();

  // Estados para backend
  const [cuentas, setCuentas] = useState([]);
  const [cuentaSeleccionada, setCuentaSeleccionada] = useState(() => {
    const saved = localStorage.getItem('selectedAccountId');
    return saved ? parseInt(saved) : null;
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const isMutatingRef = useRef(false);
  const operationImageUrlsRef = useRef(new Set());
  const [operaciones, setOperaciones] = useState([]);

  const [userName, setUserName] = useState(localStorage.getItem('userName') || 'Usuario');
  const selectedAccount = cuentas.find(cuenta => cuenta.id === cuentaSeleccionada);
  const currencyDivisa = selectedAccount?.divisa || 'USD';

  useEffect(() => {
    let isMounted = true;

    const loadCurrentUser = async () => {
      try {
        const name = await fetchAndStoreUserName();
        if (name && isMounted) {
          setUserName(name);
        }
      } catch (error) {
        console.error('Error al cargar usuario actual:', error);
      }
    };

    loadCurrentUser();

    return () => {
      isMounted = false;
    };
  }, []);

  useEffect(() => () => {
    operationImageUrlsRef.current.forEach(revokeBlobUrl);
    operationImageUrlsRef.current.clear();
  }, []);

  // Guardar cuenta seleccionada en localStorage cuando cambia
  useEffect(() => {
    if (cuentaSeleccionada) {
      localStorage.setItem('selectedAccountId', cuentaSeleccionada);
    }
  }, [cuentaSeleccionada]);

  async function cargarCuentas() {
    setLoading(true);
    setError(null);
    try {
      const response = await apiFetch('/cuentas/vercuentas', {
        method: 'GET',
        headers: getAuthHeaders()
      });
      if (!response.ok) {
        throw new Error('Error al cargar cuentas');
      }
      const data = await response.json();
      setCuentas(data);
      if (data.length > 0) {
        const savedAccountId = localStorage.getItem('selectedAccountId');
        const accountToSelect = savedAccountId 
          ? data.find(acc => acc.id === parseInt(savedAccountId))?.id 
          : data[0].id;
        setCuentaSeleccionada(accountToSelect || data[0].id);
      } else {
        setError('No se han creado cuentas de trading. Crea una desde el Tablero.');
      }
    } catch (err) {
      setError(err.message);
      console.error(err);
    } finally {
      setLoading(false);
    }
  }

  async function cargarOperacionesDeCuenta() {
    if (!cuentaSeleccionada) return;
    setLoading(true);
    setError(null);
    try {
      const response = await apiFetch(`/cuentas/${cuentaSeleccionada}/operaciones/`, {
        method: 'GET',
        headers: getAuthHeaders()
      });
      if (!response.ok) {
        throw new Error('Error al cargar operaciones');
      }
      const data = await response.json();
      operationImageUrlsRef.current.forEach(revokeBlobUrl);
      operationImageUrlsRef.current.clear();
      const operacionesConImagen = await Promise.all(data.map(async (op) => {
        if (!op.screenshot) return op;
        try {
          const screenshot = await createAuthenticatedObjectUrl(op.screenshot);
          if (screenshot?.startsWith('blob:')) {
            operationImageUrlsRef.current.add(screenshot);
          }
          return { ...op, screenshot };
        } catch (imageError) {
          console.error(`No se pudo cargar la imagen de la operación ${op.id}:`, imageError);
          return { ...op, screenshot: null };
        }
      }));
      setOperaciones(operacionesConImagen);
    } catch (err) {
      setError(err.message);
      console.error(err);
    } finally {
      setLoading(false);
    }
  }

  // Cargar cuentas al montar
  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    cargarCuentas();
  }, []);

  // Cargar operaciones cuando cambia la cuenta
  useEffect(() => {
    if (cuentaSeleccionada) {
      // eslint-disable-next-line react-hooks/set-state-in-effect
      cargarOperacionesDeCuenta();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [cuentaSeleccionada]);

  const bgGradient = {
    background: 'radial-gradient(circle at center, #1a364d 0%, #10202d 50%, #101422 100%)',
  };

  const handleLogout = () => {
    sessionStorage.removeItem('token');
    localStorage.removeItem('rememberedEmail');
    localStorage.removeItem('userName');
    navigate('/login');
  };

  const [previewImage, setPreviewImage] = useState(null);
  const [showFilters, setShowFilters] = useState(false);
  const [filterType, setFilterType] = useState('TODOS');
  const [filterActivo, setFilterActivo] = useState('TODOS');
  const [sortBy, setSortBy] = useState('fecha');
  const [sortDirection, setSortDirection] = useState('desc');
  const [currentPage, setCurrentPage] = useState(1);
  const PAGE_SIZE = 25;

  const [showForm, setShowForm] = useState(false);
  const [editing, setEditing] = useState(null);
  const [isListeningNotes, setIsListeningNotes] = useState(false);
  const recognitionRef = useRef(null);

  // Cerrar dropdowns cuando se abre el modal
  useEffect(() => {
    if (showForm) {
      // Simular click outside para cerrar cualquier dropdown abierto
      document.dispatchEvent(new Event('mousedown'));
    }
  }, [showForm]);

  const [formData, setFormData] = useState({
    fecha_hora: '',
    tipo_operacion: 'LONG',
    cantidad: '',
    activo: '',
    precio_entrada: '',
    precio_salida: '',
    notas: '',
    stop_loss: '',
    take_profit: '',
    comisiones: '',
    resultado: '',
    ratio_rr: '',
    nivel_confianza: 0,
    screenshot: null,
    screenshotFile: null,
    remove_screenshot: false
  });

  const calculatedRatioRR = calculateRiskRewardRatio(formData);

  const getSpeechRecognition = () => {
    if (typeof window === 'undefined') return null;
    return window.SpeechRecognition || window.webkitSpeechRecognition || null;
  };

  const requestMicrophoneAccess = async () => {
    if (!navigator.mediaDevices?.getUserMedia) {
      throw new Error('mediaDevices.getUserMedia no está disponible en este navegador.');
    }

    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    stream.getTracks().forEach(track => track.stop());
  };

  const getMicrophonePermissionState = async () => {
    if (!navigator.permissions?.query) return 'desconocido';

    try {
      const permission = await navigator.permissions.query({ name: 'microphone' });
      return permission.state;
    } catch {
      return 'desconocido';
    }
  };

  // Efecto para calcular el resultado automáticamente
  useEffect(() => {
    if (formData.precio_entrada && formData.precio_salida && formData.cantidad) {
      const pe = parseFloat(formData.precio_entrada);
      const ps = parseFloat(formData.precio_salida);
      const qty = parseFloat(formData.cantidad);
      if (!isNaN(pe) && !isNaN(ps) && !isNaN(qty)) {
        let res = 0;
        if (formData.tipo_operacion === 'LONG') {
          res = (ps - pe) * qty;
        } else {
          res = (pe - ps) * qty;
        }
        const resStr = res.toFixed(2);
        if (formData.resultado !== resStr) {
          // eslint-disable-next-line react-hooks/set-state-in-effect
          setFormData(prev => ({ ...prev, resultado: resStr }));
        }
      }
    }
  }, [formData.precio_entrada, formData.precio_salida, formData.cantidad, formData.tipo_operacion, formData.resultado]);

  const handleImageChange = (e) => {
    const file = e.target.files?.[0];
    if (file) {
      // Validar que sea una imagen
      if (!file.type.startsWith('image/')) {
        setError('Por favor selecciona un archivo de imagen válido');
        return;
      }
      // Validar tamaño (máximo 5MB)
      if (file.size > 5 * 1024 * 1024) {
        setError('La imagen no debe superar 5MB');
        return;
      }
      const previewUrl = URL.createObjectURL(file);
      setFormData(prev => {
        revokeBlobUrl(prev.screenshot);
        return {
          ...prev,
          screenshot: previewUrl,
          screenshotFile: file,
          remove_screenshot: false
        };
      });
    }
  };

  const handleRemoveImage = () => {
    setFormData(prev => {
      revokeBlobUrl(prev.screenshot);
      return {
        ...prev,
        screenshot: null,
        screenshotFile: null,
        remove_screenshot: true
      };
    });
  };

  const handleCloseForm = () => {
    recognitionRef.current?.stop();
    revokeBlobUrl(formData.screenshot);
    setShowForm(false);
  };

  useEffect(() => {
    return () => {
      revokeBlobUrl(formData.screenshot);
    };
  }, [formData.screenshot]);

  useEffect(() => {
    return () => {
      recognitionRef.current?.stop();
    };
  }, []);

  const handleToggleVoiceNotes = async () => {
    if (isListeningNotes) {
      recognitionRef.current?.stop();
      setIsListeningNotes(false);
      return;
    }

    const SpeechRecognition = getSpeechRecognition();
    if (!SpeechRecognition) {
      setError('Tu navegador no soporta dictado por voz. Prueba con Chrome o Edge.');
      return;
    }

    const recognition = new SpeechRecognition();
    recognition.lang = 'es-ES';
    recognition.continuous = true;
    recognition.interimResults = false;

    recognition.onresult = (event) => {
      const transcript = Array.from(event.results)
        .slice(event.resultIndex)
        .filter(result => result.isFinal)
        .map(result => result[0].transcript.trim())
        .filter(Boolean)
        .join(' ');

      if (!transcript) return;

      setFormData(prev => ({
        ...prev,
        notas: prev.notas ? `${prev.notas.trim()} ${transcript}` : transcript
      }));
    };

    recognition.onerror = async (event) => {
      setIsListeningNotes(false);
      const permissionState = await getMicrophonePermissionState();
      const errorMessages = {
        'not-allowed': `Chrome bloqueó el inicio del dictado. Permiso del micro: ${permissionState}.`,
        'audio-capture': 'Chrome no detecta ningún micrófono disponible para capturar audio.',
        network: 'El servicio de reconocimiento de voz de Chrome no está disponible ahora.',
        'no-speech': 'No se detectó voz. Pulsa el micro e inténtalo de nuevo.',
        aborted: 'Dictado cancelado.'
      };

      setError(errorMessages[event.error] || `No se pudo transcribir el audio. Error: ${event.error || 'desconocido'}.`);
    };

    recognition.onend = () => {
      setIsListeningNotes(false);
      recognitionRef.current = null;
    };

    recognitionRef.current = recognition;
    setError(null);
    try {
      await requestMicrophoneAccess();
      recognition.start();
      setIsListeningNotes(true);
    } catch (err) {
      console.error('Error al iniciar dictado:', err);
      recognitionRef.current = null;
      setIsListeningNotes(false);
      const permissionState = await getMicrophonePermissionState();
      setError(`${err?.name || 'Error'} al iniciar el dictado. Permiso del micro: ${permissionState}. ${err?.message || 'Inténtalo de nuevo.'}`);
    }
  };

  const activosDisponibles = Array.from(new Set(operaciones.map(op => op.activo))).sort();

  const displayedOperaciones = operaciones
    .filter(op => filterType === 'TODOS' ? true : op.tipo_operacion === filterType)
    .filter(op => filterActivo === 'TODOS' ? true : op.activo?.toLowerCase() === filterActivo.toLowerCase())
    .sort((a, b) => {
      if (sortBy === 'beneficio') {
        const valueA = a.resultado ?? 0;
        const valueB = b.resultado ?? 0;
        const diff = valueA - valueB;
        return sortDirection === 'asc' ? diff : -diff;
      }
      const dateA = new Date(a.fecha_hora).getTime();
      const dateB = new Date(b.fecha_hora).getTime();
      return sortDirection === 'asc' ? dateA - dateB : dateB - dateA;
    });

  const totalPages = Math.max(1, Math.ceil(displayedOperaciones.length / PAGE_SIZE));
  const paginatedOperaciones = displayedOperaciones.slice((currentPage - 1) * PAGE_SIZE, currentPage * PAGE_SIZE);

  useEffect(() => {
    if (currentPage > totalPages) {
      // eslint-disable-next-line react-hooks/set-state-in-effect
      setCurrentPage(1);
    }
  }, [currentPage, totalPages]);

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setCurrentPage(1);
  }, [filterType, filterActivo, sortBy, sortDirection, cuentaSeleccionada, operaciones.length]);

  const handleCreate = () => {
    setEditing(null);
    setFormData({
      fecha_hora: toLocalDatetimeInputValue(new Date()),
      tipo_operacion: 'LONG',
      cantidad: '',
      activo: '',
      precio_entrada: '',
      precio_salida: '',
      notas: '',
      stop_loss: '',
      take_profit: '',
      comisiones: '',
      resultado: '',
      ratio_rr: '',
      nivel_confianza: 0,
      screenshot: null,
      screenshotFile: null,
      remove_screenshot: false
    });
    setShowForm(true);
  };

  const handleEdit = (op) => {
    setEditing(op.id);
    setFormData({
      fecha_hora: toLocalDatetimeInputValue(new Date(op.fecha_hora)),
      tipo_operacion: op.tipo_operacion,
      cantidad: op.cantidad,
      activo: op.activo,
      precio_entrada: op.precio_entrada,
      precio_salida: op.precio_salida || '',
      notas: op.notas || '',
      stop_loss: op.stop_loss || '',
      take_profit: op.take_profit || '',
      comisiones: op.comisiones || '',
      resultado: op.resultado || '',
      ratio_rr: op.ratio_rr || '',
      nivel_confianza: op.nivel_confianza ?? 0,
      screenshot: op.screenshot || null,
      screenshotFile: null,
      remove_screenshot: false
    });
    setShowForm(true);
  };

  const handleDelete = async (id) => {
    if (isMutatingRef.current) return;
    if (!window.confirm('¿Estás seguro de eliminar esta operación?')) return;

    isMutatingRef.current = true;
    setLoading(true);
    setError(null);
    try {
      const response = await apiFetch(`/cuentas/${cuentaSeleccionada}/operaciones/${id}`, {
        method: 'DELETE',
        headers: getAuthHeaders()
      });
      if (!response.ok) {
        throw new Error('Error al eliminar operación');
      }
      setOperaciones(operaciones.filter(op => op.id !== id));
    } catch (err) {
      setError(err.message);
      console.error(err);
    } finally {
      isMutatingRef.current = false;
      setLoading(false);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (isMutatingRef.current) return;

    if (!cuentaSeleccionada) {
      setError('Debes seleccionar una cuenta');
      return;
    }

    const data = new FormData();
    data.append('fecha_hora', new Date(formData.fecha_hora).toISOString());
    data.append('tipo_operacion', formData.tipo_operacion);
    data.append('cantidad', String(parseFloat(formData.cantidad)));
    data.append('activo', formData.activo);
    data.append('precio_entrada', String(parseFloat(formData.precio_entrada)));

    if (formData.precio_salida) data.append('precio_salida', String(parseFloat(formData.precio_salida)));
    if (formData.notas) data.append('notas', formData.notas);
    if (formData.stop_loss) data.append('stop_loss', String(parseFloat(formData.stop_loss)));
    if (formData.take_profit) data.append('take_profit', String(parseFloat(formData.take_profit)));
    if (formData.resultado) data.append('resultado', String(parseFloat(formData.resultado)));
    if (calculatedRatioRR) data.append('ratio_rr', String(parseFloat(calculatedRatioRR)));
    if (formData.nivel_confianza !== null && formData.nivel_confianza !== undefined && formData.nivel_confianza !== '') {
      data.append('nivel_confianza', String(parseInt(formData.nivel_confianza)));
    }
    if (formData.screenshotFile) {
      data.append('screenshot', formData.screenshotFile);
    }
    if (editing && formData.remove_screenshot) {
      data.append('remove_screenshot', 'true');
    }

    isMutatingRef.current = true;
    setLoading(true);
    setError(null);
    try {
      if (editing) {
        const response = await apiFetch(`/cuentas/${cuentaSeleccionada}/operaciones/${editing}`, {
          method: 'PUT',
          headers: getAuthHeaders({ isJson: false }),
          body: data
        });
        if (!response.ok) {
          throw new Error('Error al actualizar operación');
        }
        await cargarOperacionesDeCuenta();
      } else {
        const response = await apiFetch(`/cuentas/${cuentaSeleccionada}/operaciones/`, {
          method: 'POST',
          headers: getAuthHeaders({ isJson: false }),
          body: data
        });
        if (!response.ok) {
          throw new Error('Error al crear operación');
        }
        await cargarOperacionesDeCuenta();
      }
      setShowForm(false);
    } catch (err) {
      setError(err.message);
      console.error(err);
    } finally {
      isMutatingRef.current = false;
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex" style={bgGradient}>
      <Sidebar sidebarOpen={sidebarOpen} onToggle={() => setSidebarOpen(prev => !prev)} />

      {/* Main Content */}
      <div className="flex-1 flex flex-col">
        {/* Top Bar */}
        <header className="sticky top-0 z-40 bg-black/30 backdrop-blur-xl border-b border-white/10 px-6 py-4 flex justify-between items-center">
          <div className="flex items-center gap-4">
            <button
              onClick={() => setSidebarOpen(!sidebarOpen)}
              className="text-gray-300 hover:text-white transition-colors"
            >
              <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
              </svg>
            </button>
            <h2 className="text-xl font-semibold text-white">Operaciones de Trading</h2>
          </div>

          <div className="flex items-center gap-8">
            {/* User Icon */}
            <div onClick={() => navigate('/perfil')} className="flex items-center gap-2 text-gray-300 hover:text-white cursor-pointer transition-colors" title="Ver perfil">
              <svg className="w-8 h-8" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
              </svg>
              <span className="font-medium">{userName}</span>
            </div>

            {/* Logout Button */}
            <button
              onClick={handleLogout}
              className="px-4 py-2 bg-red-600 hover:bg-red-700 text-white font-semibold rounded-full transition-all duration-300 flex items-center gap-2"
            >
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1" />
              </svg>
              Cerrar Sesión
            </button>
          </div>
        </header>

        {/* Content Area */}
        <main className="flex-1 overflow-auto p-8">
          <div className="container mx-auto">
            {error && (
              <div className={showForm ? 'fixed left-1/2 top-6 z-[10001] w-[calc(100%-2rem)] max-w-2xl -translate-x-1/2 shadow-2xl' : 'mb-4'}>
                <ErrorState variant="inline" message={error} onDismiss={() => setError(null)} className="backdrop-blur-xl" />
              </div>
            )}

            <div className="flex flex-col sm:flex-row gap-4 items-start sm:items-center justify-between mb-4">
              <div className="flex flex-col gap-2 min-w-[240px]">
                <label className="text-sm text-gray-300">Seleccionar Cuenta:</label>
                <CustomSelect
                  value={cuentaSeleccionada ? cuentas.find(c => c.id === cuentaSeleccionada)?.nombre_cuenta + ' (' + cuentas.find(c => c.id === cuentaSeleccionada)?.divisa + ')' : 'Cargando cuentas...'}
                  onChange={(selectedText) => {
                    const cuenta = cuentas.find(c => selectedText.includes(c.nombre_cuenta));
                    if (cuenta) setCuentaSeleccionada(cuenta.id);
                  }}
                  options={cuentas.length === 0 ? ['Cargando cuentas...'] : cuentas.map(cuenta => `${cuenta.nombre_cuenta} (${cuenta.divisa})`)}
                />
              </div>

              <div className="flex w-full flex-col items-stretch gap-4 sm:w-auto sm:items-end">
                <div className="hidden flex-wrap items-start justify-end gap-3 sm:flex">
                  <ImportOperationsButton
                    cuentaId={cuentaSeleccionada}
                    disabled={!cuentaSeleccionada || loading}
                    onImported={cargarOperacionesDeCuenta}
                  />
                  <ExportOperationsButton
                    cuentaId={cuentaSeleccionada}
                    filterType={filterType}
                    filterActivo={filterActivo}
                    sortBy={sortBy}
                    sortDirection={sortDirection}
                    disabled={!cuentaSeleccionada || loading}
                  />
                  <button
                    type="button"
                    onClick={handleCreate}
                    disabled={!cuentaSeleccionada || loading}
                    className="inline-flex min-h-11 items-center justify-center rounded-full bg-blue-600 px-6 py-2.5 font-semibold text-white transition-all duration-300 hover:bg-blue-700 disabled:cursor-not-allowed disabled:bg-blue-600/50"
                  >
                    {loading ? 'Cargando...' : 'Crear Operación'}
                  </button>
                </div>

                <div className="flex items-start justify-end gap-2 sm:hidden">
                  <details className="group relative">
                    <summary className="inline-flex min-h-11 cursor-pointer list-none items-center justify-center gap-2 rounded-full border border-slate-500/70 bg-slate-800/80 px-5 py-2.5 text-sm font-semibold text-slate-100 transition hover:bg-slate-700/90 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-400 [&::-webkit-details-marker]:hidden">
                      Datos
                      <svg className="h-4 w-4 transition-transform group-open:rotate-180" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="m6 9 6 6 6-6" />
                      </svg>
                    </summary>
                    <div className="absolute right-0 z-30 mt-2 flex w-max max-w-[calc(100vw-3rem)] min-w-56 flex-col gap-3 rounded-2xl border border-white/10 bg-[#111827]/95 p-3 shadow-2xl backdrop-blur-xl">
                      <ImportOperationsButton
                        cuentaId={cuentaSeleccionada}
                        disabled={!cuentaSeleccionada || loading}
                        onImported={cargarOperacionesDeCuenta}
                      />
                      <ExportOperationsButton
                        cuentaId={cuentaSeleccionada}
                        filterType={filterType}
                        filterActivo={filterActivo}
                        sortBy={sortBy}
                        sortDirection={sortDirection}
                        disabled={!cuentaSeleccionada || loading}
                      />
                    </div>
                  </details>
                  <button
                    type="button"
                    onClick={handleCreate}
                    disabled={!cuentaSeleccionada || loading}
                    className="inline-flex min-h-11 items-center justify-center rounded-full bg-blue-600 px-5 py-2.5 text-sm font-semibold text-white transition-all duration-300 hover:bg-blue-700 disabled:cursor-not-allowed disabled:bg-blue-600/50"
                  >
                    Crear operación
                  </button>
                </div>

                <button
                  type="button"
                  onClick={() => setShowFilters(prev => !prev)}
                  className="px-4 py-2 bg-slate-700 hover:bg-slate-600 text-white rounded-full text-sm transition-all"
                >
                  {showFilters ? 'Ocultar filtros' : 'Mostrar filtros'}
                </button>
              </div>
            </div>
            {showFilters && (
              <div className="mb-6 rounded-2xl border border-white/10 bg-white/5 p-4 shadow-inner">
                <div className="grid gap-4 lg:grid-cols-4 items-end">
                  <div className="flex flex-col gap-2">
                    <label className="text-sm text-gray-300">Filtrar por tipo</label>
                    <CustomSelect
                      value={filterType === 'TODOS' ? 'Todos' : filterType}
                      onChange={(val) => setFilterType(val === 'Todos' ? 'TODOS' : val)}
                      options={['Todos', 'LONG', 'SHORT']}
                    />
                  </div>

                  <div className="flex flex-col gap-2">
                    <label className="text-sm text-gray-300">Filtrar por activo</label>
                    <CustomSelect
                      value={filterActivo === 'TODOS' ? 'Todos' : filterActivo}
                      onChange={(val) => setFilterActivo(val === 'Todos' ? 'TODOS' : val)}
                      options={['Todos', ...activosDisponibles]}
                    />
                  </div>

                  <div className="flex flex-col gap-2">
                    <label className="text-sm text-gray-300">Ordenar por</label>
                    <CustomSelect
                      value={sortBy === 'fecha' ? 'Fecha' : 'Beneficio'}
                      onChange={(val) => setSortBy(val === 'Fecha' ? 'fecha' : 'beneficio')}
                      options={['Fecha', 'Beneficio']}
                    />
                  </div>

                  <div className="flex flex-col gap-2">
                    <label className="text-sm text-gray-300">Orden</label>
                    <button
                      type="button"
                      onClick={() => setSortDirection(prev => prev === 'asc' ? 'desc' : 'asc')}
                      className="rounded-xl border border-white/10 bg-[#1a2235]/90 px-3 py-2 text-sm text-white hover:bg-[#1a2235]/80 transition"
                    >
                      {sortDirection === 'asc' ? 'Ascendente' : 'Descendente'}
                    </button>
                  </div>
                </div>
              </div>
            )}

            <div className="mt-4 bg-white/5 backdrop-blur-xl rounded-2xl p-6 border border-white/10 overflow-x-auto">
              {loading ? (
                <LoadingState message="Cargando operaciones..." />
              ) : operaciones.length === 0 ? (
                <EmptyState message="No hay operaciones registradas para esta cuenta." />
              ) : displayedOperaciones.length === 0 ? (
                <EmptyState message="No hay operaciones que coincidan con los filtros seleccionados." />
              ) : (
                <>
                  <div className="mb-4 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between text-sm text-gray-300">
                    <div>
                      Mostrando {paginatedOperaciones.length} de {displayedOperaciones.length} operaciones
                    </div>
                    <div className="flex items-center gap-2">
                      <button
                        type="button"
                        onClick={() => setCurrentPage(prev => Math.max(1, prev - 1))}
                        disabled={currentPage === 1}
                        className="rounded-full border border-white/10 bg-[#1a2235]/90 px-4 py-2 text-white transition hover:bg-[#1a2235]/80 disabled:cursor-not-allowed disabled:opacity-50"
                      >
                        Anterior
                      </button>
                      <span>Página {currentPage} de {totalPages}</span>
                      <button
                        type="button"
                        onClick={() => setCurrentPage(prev => Math.min(totalPages, prev + 1))}
                        disabled={currentPage === totalPages}
                        className="rounded-full border border-white/10 bg-[#1a2235]/90 px-4 py-2 text-white transition hover:bg-[#1a2235]/80 disabled:cursor-not-allowed disabled:opacity-50"
                      >
                        Siguiente
                      </button>
                    </div>
                  </div>
                  <table className="w-full text-left">
                    <thead>
                      <tr className="text-gray-400 border-b border-white/10">
                        <th className="p-4 text-center">Fecha</th>
                        <th className="p-4 text-center">Tipo</th>
                        <th className="p-4 text-center">Activo</th>
                        <th className="p-4 text-center">Cantidad</th>
                        <th className="p-4 text-center">Precio Entrada</th>
                        <th className="p-4 text-center">Precio Salida</th>
                        <th className="p-4 text-center">Profit</th>
                        <th className="p-4 text-center">Imagen</th>
                        <th className="p-4 text-center">Acciones</th>
                      </tr>
                    </thead>
                    <tbody>
                      {paginatedOperaciones.map(op => (
                        <tr key={op.id} className="border-t text-white border-white/10 hover:bg-white/5 transition-colors">
                          <td className="p-4 text-center">{new Date(op.fecha_hora).toLocaleString()}</td>
                          <td className={`p-4 text-center font-bold ${op.tipo_operacion === 'LONG' ? 'text-green-400' : 'text-red-400'}`}>
                            {op.tipo_operacion}
                          </td>
                          <td className="p-4 text-center text-white">{op.activo}</td>
                          <td className="p-4 text-center text-white">{op.cantidad}</td>
                          <td className="p-4 text-center font-mono text-white">{formatCurrency(op.precio_entrada, currencyDivisa)}</td>
                          <td className="p-4 text-center font-mono text-white">{op.precio_salida !== null && op.precio_salida !== undefined ? formatCurrency(op.precio_salida, currencyDivisa) : '-'}</td>
                          <td className={`p-4 text-center font-semibold ${op.resultado > 0 ? 'text-green-400' : op.resultado < 0 ? 'text-red-400' : 'text-gray-300'}`}>
                            {op.resultado !== null && op.resultado !== undefined ? `${op.resultado > 0 ? '+' : ''}${formatCurrency(op.resultado, currencyDivisa)}` : '-'}
                          </td>
                          <td className="p-4 text-center">
                            {op.screenshot ? (
                              <button
                                type="button"
                                onClick={() => setPreviewImage(op.screenshot)}
                                className="mx-auto inline-block h-14 w-14 overflow-hidden rounded-xl border border-white/10 shadow-inner transition-all hover:border-blue-400"
                              >
                                <img src={op.screenshot} alt={`Operación ${op.id}`} className="h-full w-full object-cover" />
                              </button>
                            ) : (
                              <span className="text-gray-500">-</span>
                            )}
                          </td>
                          <td className="p-4 flex gap-2 justify-center">
                            <button
                              onClick={() => handleEdit(op)}
                              disabled={loading}
                              className="px-4 py-2 text-white bg-purple-600 hover:bg-purple-700 disabled:bg-purple-600/50 rounded-full text-sm transition-colors disabled:cursor-not-allowed"
                            >
                              Editar
                            </button>
                            <button
                              onClick={() => handleDelete(op.id)}
                              disabled={loading}
                              className="px-4 py-2 text-white bg-red-600 hover:bg-red-700 disabled:bg-red-600/50 rounded-full text-sm transition-colors disabled:cursor-not-allowed"
                            >
                              Eliminar
                            </button>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                  {totalPages > 1 && (
                    <div className="mt-4 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between text-sm text-gray-300">
                      <div>
                        Mostrando {paginatedOperaciones.length} de {displayedOperaciones.length} operaciones
                      </div>
                      <div className="flex items-center gap-2">
                        <button
                          type="button"
                          onClick={() => setCurrentPage(prev => Math.max(1, prev - 1))}
                          disabled={currentPage === 1}
                          className="rounded-full border border-white/10 bg-[#1a2235]/90 px-4 py-2 text-white transition hover:bg-[#1a2235]/80 disabled:cursor-not-allowed disabled:opacity-50"
                        >
                          Anterior
                        </button>
                        <span>Página {currentPage} de {totalPages}</span>
                        <button
                          type="button"
                          onClick={() => setCurrentPage(prev => Math.min(totalPages, prev + 1))}
                          disabled={currentPage === totalPages}
                          className="rounded-full border border-white/10 bg-[#1a2235]/90 px-4 py-2 text-white transition hover:bg-[#1a2235}/80 disabled:cursor-not-allowed disabled:opacity-50"
                        >
                          Siguiente
                        </button>
                      </div>
                    </div>
                  )}
                </>
              )}
            </div>

            {showForm && (
              <div className="fixed inset-0 bg-black/50 backdrop-blur-md flex items-center justify-center z-[10000] p-4">
                <div className="bg-[#1a2235]/80 backdrop-blur-lg rounded-2xl p-6 border border-white/30 w-full max-w-2xl max-h-[90vh] overflow-y-auto shadow-2xl">
                  <h2 className="text-2xl font-bold mb-4 text-white">{editing ? 'Editar Operación' : 'Crear Operación'}</h2>
                  <form onSubmit={handleSubmit} className="space-y-3">
                    <div className="grid grid-cols-3 gap-2">
                      <div className="col-span-2">
                        <div className="flex items-center gap-1 mb-1">
                          <label className="block text-xs text-white">Fecha y Hora</label>
                          <InfoIcon text="Fecha y hora de la operación." />
                        </div>
                        <input
                          type="datetime-local"
                          value={formData.fecha_hora}
                          onChange={(e) => setFormData({...formData, fecha_hora: e.target.value})}
                          className="w-full p-1.5 text-xs text-white bg-white/10 border border-white/10 rounded-xl focus:outline-none focus:border-blue-500"
                          disabled={loading}
                          required
                        />
                      </div>
                      <div className="min-w-0">
                        <div className="flex items-start gap-1 mb-1 min-w-0">
                          <label className="block text-xs text-white">Tipo</label>
                          <InfoIcon text="Elige si la operación fue LONG o SHORT." />
                        </div>
                        <CustomSelect
                          value={formData.tipo_operacion}
                          onChange={(value) => setFormData({...formData, tipo_operacion: value})}
                          options={['LONG', 'SHORT']}
                        />
                      </div>
                    </div>
                    <div className="grid grid-cols-3 gap-2">
                      <div>
                        <div className="flex items-start gap-1 mb-1 min-w-0">
                          <label className="block text-xs text-white">Activo</label>
                          <InfoIcon text="Activo o par operado, por ejemplo BTC." />
                        </div>
                        <input
                          type="text"
                          placeholder="BTC"
                          value={formData.activo}
                          onChange={(e) => setFormData({...formData, activo: e.target.value.toUpperCase()})}
                          className="w-full p-1.5 text-xs text-white bg-white/10 border border-white/10 rounded-xl focus:outline-none focus:border-blue-500"
                          disabled={loading}
                          required
                        />
                      </div>
                      <div>
                        <div className="flex items-start gap-1 mb-1 min-w-0">
                          <label className="block text-xs text-white">Cantidad</label>
                          <InfoIcon text="Tamaño de la posición." />
                        </div>
                        <input
                          type="number"
                          step="any"
                          value={formData.cantidad}
                          onChange={(e) => setFormData({...formData, cantidad: e.target.value})}
                          className="w-full p-1.5 text-xs text-white bg-white/10 border border-white/10 rounded-xl focus:outline-none focus:border-blue-500"
                          disabled={loading}
                          required
                        />
                      </div>
                      <div>
                        <div className="flex items-start gap-1 mb-1 min-w-0">
                          <label className="block text-xs text-white">Comisiones</label>
                          <InfoIcon text="Costes de la operación. No disponible todavía." />
                        </div>
                        <input
                          type="number"
                          step="any"
                          value={formData.comisiones}
                          readOnly
                          className="w-full p-1.5 text-xs text-gray-400 bg-white/5 border border-white/10 rounded-xl cursor-not-allowed opacity-80"
                          disabled
                          placeholder="No disponible todavía"
                        />
                      </div>
                    </div>
                    <div className="grid grid-cols-3 gap-2">
                      <div>
                        <div className="flex items-start gap-1 mb-1 min-w-0">
                          <label className="block text-xs text-white">Precio Entrada</label>
                          <InfoIcon text="Precio de entrada." />
                        </div>
                        <input
                          type="number"
                          step="any"
                          value={formData.precio_entrada}
                          onChange={(e) => setFormData({...formData, precio_entrada: e.target.value})}
                          className="w-full p-1.5 text-xs text-white bg-white/10 border border-white/10 rounded-xl focus:outline-none focus:border-blue-500"
                          disabled={loading}
                          required
                        />
                      </div>
                      <div>
                        <div className="flex items-start gap-1 mb-1 min-w-0">
                          <label className="block text-xs text-white">Precio Salida</label>
                          <InfoIcon text="Precio de cierre, si ya saliste." />
                        </div>
                        <input
                          type="number"
                          step="any"
                          value={formData.precio_salida}
                          onChange={(e) => setFormData({...formData, precio_salida: e.target.value})}
                          className="w-full p-1.5 text-xs text-white bg-white/10 border border-white/10 rounded-xl focus:outline-none focus:border-blue-500"
                          disabled={loading}
                          placeholder="Opt"
                        />
                      </div>
                      <div>
                        <div className="flex items-start gap-1 mb-1 min-w-0">
                          <label className="block text-xs text-white">Stop Loss</label>
                          <InfoIcon text="Precio donde limitas la pérdida." />
                        </div>
                        <input
                          type="number"
                          step="any"
                          value={formData.stop_loss}
                          onChange={(e) => setFormData({...formData, stop_loss: e.target.value})}
                          className="w-full p-1.5 text-xs text-white bg-white/10 border border-white/10 rounded-xl focus:outline-none focus:border-blue-500"
                          disabled={loading}
                          placeholder="Opt"
                        />
                      </div>
                    </div>
                    <div className="grid grid-cols-3 gap-2">
                      <div>
                        <div className="flex items-start gap-1 mb-1 min-w-0">
                          <label className="block text-xs text-white">Take Profit</label>
                          <InfoIcon text="Precio objetivo de beneficio." />
                        </div>
                        <input
                          type="number"
                          step="any"
                          value={formData.take_profit}
                          onChange={(e) => setFormData({...formData, take_profit: e.target.value})}
                          className="w-full p-1.5 text-xs text-white bg-white/10 border border-white/10 rounded-xl focus:outline-none focus:border-blue-500"
                          disabled={loading}
                          placeholder="Opt"
                        />
                      </div>
                      <div>
                        <div className="flex items-start gap-1 mb-1 min-w-0">
                          <label className="block text-xs text-white">Resultado</label>
                          <InfoIcon text="Ganancia o pérdida de la operación." />
                        </div>
                        <input
                          type="number"
                          step="any"
                          value={formData.resultado}
                          onChange={(e) => setFormData({...formData, resultado: e.target.value})}
                          className="w-full p-1.5 text-xs text-white bg-white/10 border border-white/10 rounded-xl focus:outline-none focus:border-blue-500"
                          disabled={loading}
                          placeholder="G/P"
                        />
                      </div>
                      <div>
                        <div className="flex items-start gap-1 mb-1 min-w-0">
                          <label className="block text-xs text-white">Ratio RR</label>
                          <InfoIcon text="Relación entre riesgo y beneficio previsto." />
                        </div>
                        <input
                          type="number"
                          step="any"
                          value={calculatedRatioRR}
                          readOnly
                          className="w-full p-1.5 text-xs text-white bg-white/10 border border-white/10 rounded-xl focus:outline-none focus:border-blue-500"
                          disabled={loading}
                          placeholder="Auto"
                        />
                      </div>
                    </div>
                    <div>
                      <div className="flex items-center justify-between mb-2">
                        <div className="flex items-center gap-1">
                          <label className="block text-xs text-white">Confianza: <span className="text-blue-400 font-bold">{formData.nivel_confianza || 0}%</span></label>
                          <InfoIcon text="Confianza al tomar la operación." />
                        </div>
                      </div>
                      <input
                        type="range"
                        min="0"
                        max="100"
                        value={formData.nivel_confianza}
                        onChange={(e) => setFormData({...formData, nivel_confianza: e.target.value})}
                        className="w-full h-2 rounded-lg appearance-none cursor-pointer accent-blue-500"
                        style={{
                          background: `linear-gradient(to right, #3b82f6 ${formData.nivel_confianza || 0}%, rgba(255,255,255,0.1) ${formData.nivel_confianza || 0}%)`
                        }}
                        disabled={loading}
                      />
                    </div>
                    <div>
                      <div className="flex items-center justify-between gap-2 mb-1">
                        <div className="flex items-center gap-1">
                          <label className="block text-xs text-white">Notas</label>
                          <InfoIcon text="Anota contexto, motivo o emoción." />
                        </div>
                        <button
                          type="button"
                          onClick={handleToggleVoiceNotes}
                          disabled={loading}
                          className={`relative inline-flex h-8 w-8 items-center justify-center rounded-full border transition-all duration-200 disabled:opacity-50 ${
                            isListeningNotes
                              ? 'voice-neon-recording border-violet-400 bg-violet-700/35 text-violet-100 ring-2 ring-indigo-400/60 hover:bg-violet-700/45'
                              : 'border-white/10 bg-white/10 text-white hover:border-blue-400 hover:bg-blue-500/20'
                          }`}
                          title={isListeningNotes ? 'Detener dictado' : 'Dictar notas'}
                          aria-label={isListeningNotes ? 'Detener dictado de notas' : 'Iniciar dictado de notas'}
                        >
                          {isListeningNotes && (
                            <span className="absolute -right-0.5 -top-0.5 h-2.5 w-2.5 rounded-full bg-violet-400 shadow-[0_0_10px_rgba(139,92,246,0.95)] animate-ping" aria-hidden="true"></span>
                          )}
                          <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 3a3 3 0 00-3 3v6a3 3 0 006 0V6a3 3 0 00-3-3z" />
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M19 10v2a7 7 0 01-14 0v-2M12 19v2m-4 0h8" />
                          </svg>
                        </button>
                      </div>
                      <textarea
                        value={formData.notas}
                        onChange={(e) => setFormData({...formData, notas: e.target.value})}
                        className="w-full p-1.5 text-xs text-white bg-white/10 border border-white/10 rounded-xl focus:outline-none focus:border-blue-500 h-12"
                        disabled={loading}
                      />
                    </div>
                    <div>
                      <div className="flex items-center gap-1 mb-1">
                        <label className="block text-xs text-white">Imagen/Screenshot</label>
                        <InfoIcon text="Captura o imagen de la operación." />
                      </div>
                      <div className="flex gap-2">
                        <input
                          type="file"
                          accept="image/*"
                          onChange={handleImageChange}
                          disabled={loading}
                          className="w-full p-1.5 text-xs text-gray-300 bg-white/10 border border-white/10 rounded-xl focus:outline-none focus:border-blue-500 file:bg-blue-600 file:text-white file:border-0 file:px-2 file:py-1 file:rounded file:cursor-pointer file:text-xs hover:file:bg-blue-700"
                        />
                        {formData.screenshot && (
                          <button
                            type="button"
                            onClick={handleRemoveImage}
                            disabled={loading}
                            className="px-2 py-1.5 text-xs text-red-400 bg-red-500/10 border border-red-500/30 hover:bg-red-500/20 rounded-xl transition-colors disabled:opacity-50"
                            title="Eliminar imagen"
                          >
                            ✕
                          </button>
                        )}
                      </div>
                      {formData.screenshot && (
                        <div className="mt-3 p-2 bg-white/5 rounded-xl border border-white/10">
                          <img 
                            src={formData.screenshot} 
                            alt="Vista previa" 
                            className="max-h-40 max-w-full mx-auto rounded-lg object-contain"
                          />
                        </div>
                      )}
                    </div>
                    <div className="flex justify-end gap-2 pt-2">
                      <button
                        type="button"
                        onClick={handleCloseForm}
                        disabled={loading}
                        className="px-4 py-1.5 text-xs text-white bg-gray-700 hover:bg-gray-600 disabled:bg-gray-700/50 rounded-full transition-colors disabled:cursor-not-allowed"
                      >
                        Cancelar
                      </button>
                      <button
                        type="submit"
                        disabled={loading}
                        className="px-4 py-1.5 text-xs text-white bg-blue-600 hover:bg-blue-700 disabled:bg-blue-600/50 rounded-full transition-colors font-bold disabled:cursor-not-allowed"
                      >
                        {loading ? 'Guardando...' : 'Guardar'}
                      </button>
                    </div>
                  </form>
                </div>
              </div>
            )}
          </div>
        </main>
      </div>
      {previewImage && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4" onClick={() => setPreviewImage(null)}>
          <div className="relative max-w-4xl w-full max-h-[90vh] overflow-hidden rounded-3xl bg-[#0f172a] p-4 shadow-2xl" onClick={(e) => e.stopPropagation()}>
            <button
              type="button"
              onClick={() => setPreviewImage(null)}
              className="absolute right-4 top-4 rounded-full bg-white/10 px-3 py-2 text-xs text-white transition hover:bg-white/20"
            >Cerrar</button>
            <img src={previewImage} alt="Vista previa ampliada" className="mx-auto max-h-[80vh] w-full object-contain rounded-2xl" />
          </div>
        </div>
      )}
    </div>
  );
};

export default OperacionesTrading;
