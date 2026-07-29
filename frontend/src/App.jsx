import { BrowserRouter as Router, Routes, Route, useLocation } from 'react-router-dom';
import Header from './components/Header';
import Footer from './components/Footer';
import Hero from './components/Hero';
import Login from './components/Login';
import Signup from './components/Signup';
import Dashboard from './components/Dashboard';
import OperacionesTrading from './components/OperacionesTrading';
import PerfilUsuario from './components/PerfilUsuario';
import EstadisticasEmocionales from './components/EstadisticasEmocionales';
import Calendar from './components/calendar';
import ChatIA from './components/ChatIA';
import DesktopControls from './components/DesktopControls';
import { ChatMemoryProvider } from './context/ChatMemoryContext';

function AppContent() {
  const location = useLocation();
  const isHomePage = location.pathname === '/';

  return (
    <div className="min-h-screen flex flex-col">
      <Header />
      <main className="flex-1">
        <Routes>
          <Route path="/" element={<Hero />} />
          <Route path="/login" element={<Login />} />
          <Route path="/signup" element={<Signup />} />
          <Route path="/dashboard" element={<Dashboard />} />
          <Route path="/dashboard/operaciones" element={<Dashboard />} />
          <Route path="/trading" element={<OperacionesTrading />} />
          <Route path="/perfil" element={<PerfilUsuario />} />
          <Route path="/estadisticas" element={<EstadisticasEmocionales />} />
          <Route path="/calendar" element={<Calendar />} />
          <Route path="/chat" element={<ChatIA />} />
        </Routes>
      </main>
      {isHomePage && <Footer />}
      <DesktopControls />
    </div>
  );
}

function App() {
  return (
    <Router>
      <ChatMemoryProvider>
        <AppContent />
      </ChatMemoryProvider>
    </Router>
  );
}

export default App;
