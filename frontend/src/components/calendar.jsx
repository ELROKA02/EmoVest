import React, { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import Sidebar from './Sidebar';
import CustomSelect from './CustomSelect';
import { fetchAndStoreUserName } from '../utils/userSession';
import { formatCurrency } from '../utils/currency';
import { API_BASE_URL } from '../config';
import FullCalendar from '@fullcalendar/react';
import dayGridPlugin from '@fullcalendar/daygrid';
import timeGridPlugin from '@fullcalendar/timegrid';
import interactionPlugin from '@fullcalendar/interaction';

const Calendar = () => {
  const [sidebarOpen, setSidebarOpen] = useState(() => {
    const saved = localStorage.getItem('sidebarOpen');
    return saved !== null ? JSON.parse(saved) : true;
  });
  const navigate = useNavigate();

  const [userName, setUserName] = useState(localStorage.getItem('userName') || 'Usuario');
  const [cuentaSeleccionada, setCuentaSeleccionada] = useState(() => {
    const saved = localStorage.getItem('selectedAccountId');
    return saved ? saved : '';
  });
  const [cuentas, setCuentas] = useState([]);
  const [estadisticasDiarias, setEstadisticasDiarias] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [diaSeleccionado, setDiaSeleccionado] = useState(null);
  const calendarRef = useRef(null);

  const currentYear = new Date().getFullYear();
  const currentMonth = new Date().getMonth() + 1;
  const [year, setYear] = useState(currentYear.toString());
  const [month, setMonth] = useState(currentMonth.toString());

  const meses = [
    { id: '1', nombre: 'Enero' },
    { id: '2', nombre: 'Febrero' },
    { id: '3', nombre: 'Marzo' },
    { id: '4', nombre: 'Abril' },
    { id: '5', nombre: 'Mayo' },
    { id: '6', nombre: 'Junio' },
    { id: '7', nombre: 'Julio' },
    { id: '8', nombre: 'Agosto' },
    { id: '9', nombre: 'Septiembre' },
    { id: '10', nombre: 'Octubre' },
    { id: '11', nombre: 'Noviembre' },
    { id: '12', nombre: 'Diciembre' }
  ];

  useEffect(() => {
    if (cuentaSeleccionada) {
      localStorage.setItem('selectedAccountId', cuentaSeleccionada);
    }
  }, [cuentaSeleccionada]);

  useEffect(() => {
    const cargarCuentas = async () => {
      const token = sessionStorage.getItem('token');
      if (!token) return;
      try {
        const response = await fetch(`${API_BASE_URL}/cuentas/vercuentas`, {
          headers: { 'Authorization': `Bearer ${token}` }
        });
        if (response.ok) {
          const data = await response.json();
          setCuentas(data);
          if (data.length > 0 && !cuentaSeleccionada) {
            setCuentaSeleccionada(data[0].id.toString());
          }
        }
      } catch (err) {
        console.error('Error al cargar cuentas:', err);
      }
    };
    cargarCuentas();
  }, []);

  useEffect(() => {
    const cargarOperaciones = async () => {
      if (!cuentaSeleccionada) return;
      setLoading(true);
      setError(null);
      try {
        const token = sessionStorage.getItem('token');
        if (!token) {
          setError('No hay sesión activa');
          return;
        }
        const statsResponse = await fetch(
          `${API_BASE_URL}/cuentas/${cuentaSeleccionada}/estadisticas/calendario?year=${year}&month=${month}`,
          { headers: { 'Authorization': `Bearer ${token}` } }
        );
        if (statsResponse.ok) {
          const statsData = await statsResponse.json();
          setEstadisticasDiarias(statsData);
        }
      } catch (error) {
        setError('Error de conexión al cargar operaciones', error);
      } finally {
        setLoading(false);
      }
    };
    cargarOperaciones();
  }, [cuentaSeleccionada, year, month]);

  useEffect(() => {
    // Navegar el calendario al mes y año seleccionados cuando cambian desde los selects
    if (calendarRef.current) {
      const calendarApi = calendarRef.current.getApi();
      if (calendarApi) {
        calendarApi.gotoDate(new Date(parseInt(year), parseInt(month) - 1, 1));
      }
    }
  }, [month, year]);

  const handleLogout = () => {
    sessionStorage.removeItem('token');
    localStorage.removeItem('rememberedEmail');
    localStorage.removeItem('userName');
    navigate('/login');
  };

  const bgGradient = {
    background: 'radial-gradient(circle at center, #1a364d 0%, #10202d 50%, #101422 100%)',
  };

  const newLocal = `
                    .fc { 
                      font-family: 'Inter', system-ui, sans-serif;
                      --fc-border-color: transparent;
                      --fc-button-bg-color: rgba(59, 130, 246, 0.2);
                      --fc-button-border-color: rgba(59, 130, 246, 0.3);
                      --fc-button-text-color: #ffffff;
                      --fc-button-hover-bg-color: rgba(59, 130, 246, 0.3);
                      --fc-button-hover-border-color: rgba(59, 130, 246, 0.5);
                      --fc-today-bg-color: rgba(16, 185, 129, 0.15);
                    }
                    .fc-toolbar-title { 
                      color: #ffffff !important; 
                      font-weight: 700; 
                      font-size: 1.3rem; 
                      text-shadow: 0 2px 4px rgba(0, 0, 0, 0.3);
                      letter-spacing: 0.5px;
                      position: absolute !important;
                      left: 50% !important;
                      top: 50% !important;
                      transform: translate(-50%, -50%) !important;
                      white-space: nowrap !important;
                      z-index: 2 !important;
                    }
                    .fc-toolbar-center {
                      position: relative !important;
                      flex: 1 !important;
                      display: flex !important;
                    }
                    .fc-toolbar {
                      position: relative !important;
                      display: flex !important;
                      align-items: center !important;
                      justify-content: space-between !important;
                    }
                    .fc-toolbar-left {
                      flex: 0 0 auto !important;
                      display: flex !important;
                      align-items: center !important;
                      gap: 8px !important;
                    }
                    .fc-toolbar-right {
                      flex: 0 0 auto !important;
                    }
                    .fc-button { 
                      background: linear-gradient(135deg, rgba(59, 130, 246, 0.2), rgba(147, 51, 234, 0.2)) !important; 
                      border: 1px solid rgba(59, 130, 246, 0.3) !important; 
                      color: #ffffff !important; 
                      border-radius: 12px !important; 
                      padding: 8px 16px !important; 
                      margin: 0 8px !important;
                      font-weight: 600 !important; 
                      font-size: 0.875rem !important;
                      transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1) !important;
                      box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1) !important;
                      backdrop-filter: blur(10px) !important;
                    }
                    .fc-button:hover { 
                      background: linear-gradient(135deg, rgba(59, 130, 246, 0.3), rgba(147, 51, 234, 0.3)) !important; 
                      border-color: rgba(59, 130, 246, 0.5) !important; 
                      transform: translateY(-2px) scale(1.05) !important;
                      box-shadow: 0 8px 12px rgba(59, 130, 246, 0.3) !important;
                    }
                    .fc-button-active { 
                      background: linear-gradient(135deg, rgba(59, 130, 246, 0.4), rgba(147, 51, 234, 0.4)) !important; 
                      border-color: rgba(59, 130, 246, 0.6) !important; 
                      color: #ffffff !important;
                      box-shadow: 0 6px 10px rgba(59, 130, 246, 0.4) !important;
                    }
                    .fc-today-button { 
                      background: linear-gradient(135deg, rgba(16, 185, 129, 0.3), rgba(5, 150, 105, 0.3)) !important; 
                      border-color: rgba(16, 185, 129, 0.5) !important; 
                      color: #10f981 !important;
                      font-weight: 700 !important;
                    }
                    .fc-today-button:hover { 
                      background: linear-gradient(135deg, rgba(16, 185, 129, 0.4), rgba(5, 150, 105, 0.4)) !important; 
                      border-color: rgba(16, 185, 129, 0.6) !important;
                      box-shadow: 0 8px 12px rgba(16, 185, 129, 0.4) !important;
                    }
                    .fc-toolbar { 
                      margin-top: 1.5rem !important;
                      margin-bottom: 1.5rem !important;
                      padding: 0 1rem;
                    }
                    .fc-col-header-cell { 
                      background: linear-gradient(135deg, rgba(168, 0, 255, 0.85), rgba(147, 0, 230, 0.75)) !important; 
                      box-shadow: inset 0 0 0 1px #000000 !important;
                      color: #000000 !important; 
                      font-weight: 700 !important; 
                      text-transform: uppercase !important; 
                      font-size: 0.75rem !important; 
                      padding: 12px 8px !important;
                      letter-spacing: 0.5px;
                      border-radius: 8px !important;
                    }
                    .fc-col-header-cell-cushion {
                      color: #ffffff !important;
                    }
                    .fc-day-sun.fc-col-header-cell {
                      box-shadow: inset 0 0 0 1px #000000 !important;
                    }
                    .fc-daygrid-day,
                    .fc-daygrid-day .fc-daygrid-day-frame {
                      height: 100% !important;
                    }
                    .fc-daygrid-day-frame {
                      display: flex !important;
                      flex-direction: column !important;
                      min-height: 100px !important;
                      background: linear-gradient(135deg, rgba(17, 24, 39, 0.8), rgba(31, 41, 55, 0.6));
                      border-color: rgba(255, 255, 255, 0.06) !important;
                      border-radius: 10px !important;
                      transition: all 0.3s ease !important;
                    }
                    .fc-daygrid-day-frame:hover {
                      background: linear-gradient(135deg, rgba(59, 130, 246, 0.1), rgba(147, 51, 234, 0.05)) !important;
                      border-color: rgba(59, 130, 246, 0.2) !important;
                    }
                    .fc-daygrid-day-top {
                      flex: 1 !important;
                      width: 100% !important;
                      overflow: visible !important;
                    }
                    .fc-day-today { 
                      background: transparent !important;
                      border-color: transparent !important;
                      box-shadow: none !important;
                    }
                    .fc-day-today .fc-daygrid-day-frame {
                      box-shadow: inset 0 0 0 2px rgba(168, 0, 255, 0.7) !important;
                    }
                    .fc-daygrid-day-number {
                      color: #ffffff !important;
                      font-weight: 700 !important;
                    }
                    .fc-day-today .fc-daygrid-day-number { 
                      color: #a800ff !important; 
                      font-weight: 800 !important;
                      text-shadow: 0 0 10px rgba(168, 0, 255, 0.5);
                    }
                    .fc-day-other-month { 
                      background: linear-gradient(135deg, rgba(0, 0, 0, 0.3), rgba(0, 0, 0, 0.1)) !important; 
                      opacity: 0.4 !important;
                    }
                    .fc-day-other-month .fc-daygrid-day-number { 
                      color: #6b7280 !important;
                    }
                    .fc-daygrid-day.fc-day-past { 
                      opacity: 0.8 !important;
                    }
                    .fc-daygrid-day.fc-day-future { 
                      opacity: 1 !important;
                    }
                    .fc-daygrid-event { 
                      border-radius: 10px !important; 
                      margin: 2px 3px !important; 
                      border: none !important; 
                      box-shadow: 0 4px 8px rgba(0, 0, 0, 0.2) !important; 
                      transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1) !important;
                      backdrop-filter: blur(10px) !important;
                      font-weight: 600 !important;
                    }
                    .fc-daygrid-event:hover { 
                      transform: scale(1.08) translateY(-2px) !important; 
                      box-shadow: 0 8px 16px rgba(0, 0, 0, 0.4) !important; 
                      z-index: 20 !important;
                    }
                    .fc-timegrid-slot { 
                      background: linear-gradient(135deg, rgba(17, 24, 39, 0.8), rgba(31, 41, 55, 0.6)) !important; 
                      border-color: rgba(255, 255, 255, 0.06) !important;
                    }
                    .fc-timegrid-slot-label { 
                      color: #9ca3af !important; 
                      font-size: 0.8rem;
                      font-weight: 600;
                    }
                    .fc-timegrid-axis { 
                      background: linear-gradient(135deg, rgba(0, 0, 0, 0.4), rgba(0, 0, 0, 0.2)) !important; 
                      border-color: rgba(255, 255, 255, 0.08) !important;
                    }
                    .fc-timegrid-divider { 
                      border-color: rgba(255, 255, 255, 0.06) !important;
                    }
                    .fc-timegrid-event { 
                      border-radius: 10px !important; 
                      border: none !important; 
                      box-shadow: 0 4px 8px rgba(0, 0, 0, 0.2) !important;
                      backdrop-filter: blur(10px) !important;
                    }
                    .fc-scrollgrid { 
                      border: none !important;
                    }
                    .fc-scrollgrid td, 
                    .fc-scrollgrid th { 
                      border-color: rgba(255, 255, 255, 0.06) !important;
                    }
                    .fc-scrollgrid-section-liquid > td,
                    .fc-scrollgrid-section > td:first-of-type,
                    .fc-scrollgrid-section > th:first-of-type {
                      border-left: none !important;
                      border-left-width: 0 !important;
                      border-left-color: transparent !important;
                    }
                    .fc-popover { 
                      background: linear-gradient(135deg, rgba(31, 41, 55, 0.95), rgba(17, 24, 39, 0.95)) !important; 
                      border: 1px solid rgba(255, 255, 255, 0.15) !important; 
                      border-radius: 16px !important; 
                      box-shadow: 0 20px 40px rgba(0, 0, 0, 0.5) !important;
                      backdrop-filter: blur(20px) !important;
                    }
                    .fc-popover-title { 
                      background: linear-gradient(135deg, rgba(0, 0, 0, 0.4), rgba(0, 0, 0, 0.2)) !important; 
                      color: #ffffff !important; 
                      border-bottom: 1px solid rgba(255, 255, 255, 0.1) !important; 
                      font-weight: 700 !important;
                      padding: 12px 16px !important;
                    }
                    .fc-more-link { 
                      color: #60a5fa !important; 
                      background: linear-gradient(135deg, rgba(96, 165, 250, 0.2), rgba(59, 130, 246, 0.1)) !important; 
                      border-radius: 8px !important; 
                      padding: 4px 8px !important; 
                      font-weight: 600 !important;
                      border: 1px solid rgba(96, 165, 250, 0.3) !important;
                      transition: all 0.3s ease !important;
                    }
                    .fc-more-link:hover { 
                      background: linear-gradient(135deg, rgba(96, 165, 250, 0.3), rgba(59, 130, 246, 0.2)) !important;
                      transform: scale(1.05) !important;
                    }
                  `;
  return (
    <div className="min-h-screen flex" style={bgGradient}>
      {/* Sidebar */}
      <Sidebar sidebarOpen={sidebarOpen} onToggle={() => setSidebarOpen(prev => !prev)} />

      {/* Main Content */}
      <div className="flex-1 flex flex-col">
        <header className="sticky top-0 z-40 bg-black/30 backdrop-blur-xl border-b border-white/10 px-6 py-4 flex justify-between items-center">
          <div className="flex items-center gap-4">
            <button onClick={() => setSidebarOpen(!sidebarOpen)} className="text-gray-300 hover:text-white transition-colors">
              <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" /></svg>
            </button>
            <h2 className="text-xl font-semibold text-white">Calendario</h2>
          </div>
          <div className="flex items-center gap-8">
            <div onClick={() => navigate('/perfil')} className="flex items-center gap-2 text-gray-300 hover:text-white cursor-pointer transition-colors" title="Ver perfil">
              <svg className="w-8 h-8" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" /></svg>
              <span className="font-medium">{userName}</span>
            </div>
            <button onClick={handleLogout} className="px-4 py-2 bg-red-600 hover:bg-red-700 text-white font-semibold rounded-full transition-all duration-300 flex items-center gap-2">
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1" /></svg>
              Cerrar Sesión
            </button>
          </div>
        </header>

        <main className="flex-1 overflow-auto p-14">
          <div className="max-w-7xl mx-auto space-y-6">
            {error && <div className="p-4 bg-red-500/20 border border-red-500/50 rounded-lg text-red-300">{error}</div>}

            {/* Calendario */}
            <div className="rounded-2xl bg-white/5 backdrop-blur-xl p-6 transform transition-all duration-300">
              <div className="flex items-center justify-between mb-6">
                <div className="flex items-center gap-3">
                  <div className="w-4 h-4 rounded-full bg-indigo-500 shadow-lg shadow-indigo-500/50"></div>
                  <h3 className="text-white font-bold text-xl">Calendario de Operaciones</h3>
                </div>
              </div>

              {/* Fila: select de cuenta (izquierda) + controles de fecha (derecha) */}
              <div className="flex items-center justify-between mb-4">
                <div className="flex items-center gap-2">
                  <label className="text-sm text-gray-300 font-medium">Cuenta:</label>
                  <CustomSelect
                    value={cuentas.find(c => c.id.toString() === cuentaSeleccionada)?.nombre_cuenta || 'Sin cuenta'}
                    onChange={(val) => {
                      const cuenta = cuentas.find(c => c.nombre_cuenta === val);
                      if (cuenta) setCuentaSeleccionada(cuenta.id.toString());
                    }}
                    options={cuentas.length === 0 ? ['Sin cuenta'] : cuentas.map(c => c.nombre_cuenta)}
                    className="w-36"
                  />
                </div>

                {/* Controles de navegación de fecha */}
                <div className="flex items-center gap-2">
                <button 
                  onClick={() => {
                    const currentDate = new Date();
                    const currentYear = currentDate.getFullYear();
                    const currentMonth = currentDate.getMonth() + 1;
                    setYear(currentYear.toString());
                    setMonth(currentMonth.toString());
                  }}
                  className="px-4 py-2 bg-gradient-to-r from-purple-600/20 to-purple-500/20 hover:from-purple-600/30 hover:to-purple-500/30 text-purple-400 border border-purple-500/30 hover:border-purple-500/50 font-bold rounded-lg transition-all duration-300 flex items-center gap-2 backdrop-blur-sm"
                >
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
                  </svg>
                  Hoy
                </button>

                <CustomSelect
                  value={meses.find(m => m.id === month)?.nombre || 'Enero'}
                  onChange={(val) => setMonth(meses.find(m => m.nombre === val)?.id || '1')}
                  options={meses.map(m => m.nombre)}
                  className="w-28 z-50"
                />
                
                <CustomSelect
                  value={year}
                  onChange={(val) => setYear(val)}
                  options={Array.from({ length: 10 }, (_, i) => new Date().getFullYear() - i).map(year => year.toString())}
                  className="w-24 z-50"
                />
                </div>
              </div>
              
              {loading ? (
                <div className="flex justify-center items-center py-20">
                  <div className="relative">
                    <div className="w-16 h-16 border-4 border-blue-500 border-t-transparent rounded-full animate-spin"></div>
                    <div className="absolute inset-0 flex items-center justify-center">
                      <div className="w-8 h-8 bg-blue-500 rounded-full animate-pulse"></div>
                    </div>
                  </div>
                  <div className="ml-4 text-white text-lg font-medium">Cargando operaciones...</div>
                </div>
              ) : (
                <div className="bg-white/5 backdrop-blur-xl rounded-xl">
                  <style>{newLocal}</style>
                  <FullCalendar
                    key={`${year}-${month}-${estadisticasDiarias.length}`}
                    ref={calendarRef}
                    plugins={[dayGridPlugin, timeGridPlugin, interactionPlugin]}
                    initialView="dayGridMonth"
                    initialDate={`${year}-${String(month).padStart(2, '0')}-01`}
                    headerToolbar={{
                      left: 'prev,next',
                      center: 'title',
                      right: ''
                    }}
                    dateClick={(arg) => {
                      const dateStr = arg.dateStr;
                      const stats = estadisticasDiarias.find(s => s.fecha === dateStr);
                      setDiaSeleccionado({ fecha: dateStr, stats: stats || null });
                    }}
                    dayCellDidMount={(arg) => {
                      const dateStr = arg.date.toLocaleDateString('en-CA');
                      const stats = estadisticasDiarias.find(s => s.fecha === dateStr);
                      if (!stats) return;
                      const divisa = cuentas.find(c => c.id.toString() === cuentaSeleccionada)?.divisa || 'EUR';
                      const color = stats.ganancia_neta > 0 ? '#10f981' : stats.ganancia_neta < 0 ? '#f87171' : '#9ca3af';
                      const bg = stats.ganancia_neta > 0 ? 'rgba(16,185,129,0.25)' : stats.ganancia_neta < 0 ? 'rgba(239,68,68,0.25)' : 'rgba(107,114,128,0.12)';
                      const border = stats.ganancia_neta > 0 ? 'rgba(16,185,129,0.3)' : stats.ganancia_neta < 0 ? 'rgba(239,68,68,0.3)' : 'rgba(107,114,128,0.3)';
                      const frame = arg.el.querySelector('.fc-daygrid-day-frame');
                      if (!frame) return;
                      frame.style.background = bg;
                      frame.style.border = `1px solid ${border}`;
                      frame.style.borderRadius = '10px';
                      const overlay = document.createElement('div');
                      overlay.className = 'day-stats-overlay';
                      overlay.style.cssText = `
                        position: absolute;
                        inset: 0;
                        display: flex;
                        flex-direction: column;
                        align-items: center;
                        justify-content: center;
                        gap: 4px;
                        pointer-events: none;
                        z-index: 1;
                      `;
                      overlay.innerHTML = `
                        <div style="font-size:0.95rem;font-weight:800;color:${color};line-height:1.2">
                          ${stats.ganancia_neta > 0 ? '+' : stats.ganancia_neta < 0 ? '-' : ''}${formatCurrency(Math.abs(stats.ganancia_neta), divisa)}
                        </div>
                        <div style="font-size:0.72rem;font-weight:600;color:rgba(255,255,255,0.6);line-height:1">
                          ${stats.total_operaciones} op${stats.total_operaciones !== 1 ? 's' : ''}
                        </div>
                      `;
                      frame.style.position = 'relative';
                      frame.appendChild(overlay);
                    }}
                    datesSet={(dateInfo) => {
                      const d = dateInfo.view.currentStart;
                      const newMonth = (d.getMonth() + 1).toString();
                      const newYear = d.getFullYear().toString();
                      setMonth(prev => prev !== newMonth ? newMonth : prev);
                      setYear(prev => prev !== newYear ? newYear : prev);
                    }}
                    height="auto"
                    aspectRatio={1.8}
                    stickyHeaderDates={false}
                    locale="es"
                    firstDay={1}
                    buttonText={{
                      today: 'Hoy',
                      month: 'Mes',
                      week: 'Semana',
                      day: 'Día',
                      list: 'Lista'
                    }}
                  />
                </div>
              )}

              {/* Panel de notas del día seleccionado */}
              {diaSeleccionado && (
                <div className="mt-6 rounded-2xl bg-white/5 backdrop-blur-xl border border-white/10 p-5">
                  <div className="flex items-center justify-between mb-4">
                    <div className="flex items-center gap-3">
                      <div className="w-3 h-3 rounded-full bg-yellow-400 shadow-lg shadow-yellow-400/40"></div>
                      <h3 className="text-white font-bold text-lg">
                        Notas del {new Date(diaSeleccionado.fecha + 'T00:00:00').toLocaleDateString('es-ES', { weekday: 'long', day: 'numeric', month: 'long', year: 'numeric' })}
                      </h3>
                    </div>
                    <button
                      onClick={() => setDiaSeleccionado(null)}
                      className="text-gray-400 hover:text-white transition-colors text-xl leading-none"
                    >
                      ✕
                    </button>
                  </div>

                  {!diaSeleccionado.stats || diaSeleccionado.stats.notas_operaciones.length === 0 ? (
                    <p className="text-gray-400 text-sm italic">No hay notas registradas en las operaciones de este día.</p>
                  ) : (
                    <div className="flex flex-col gap-3">
                      {diaSeleccionado.stats.notas_operaciones.map((nota, i) => (
                        <div key={i} className="flex gap-3 bg-white/5 rounded-xl p-4 border border-white/10">
                          <div className="mt-1 w-2 h-2 rounded-full bg-yellow-400 flex-shrink-0"></div>
                          <p className="text-gray-200 text-sm leading-relaxed">{nota}</p>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              )}
            </div>
          </div>
        </main>
      </div>
    </div>
  );
};

export default Calendar;