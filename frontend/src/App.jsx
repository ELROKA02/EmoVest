import { BrowserRouter as Router, Routes, Route, useLocation } from 'react-router-dom';
import Header from './components/Header';
import Footer from './components/Footer';
import Hero from './components/Hero';
import Login from './components/Login';
import Signup from './components/Signup';
import Dashboard from './components/Dashboard';
import OperacionesTrading from './components/OperacionesTrading';

function AppContent() {
  const location = useLocation();
  const isHomePage = location.pathname === '/';

  const bgGradient = {
    background: 'radial-gradient(circle at center, #1a364d 0%, #10202d 50%, #101422 100%)',
  };

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
        </Routes>
      </main>
      {isHomePage && <Footer />}
    </div>
  );
}

function App() {
  return (
    <Router>
      <AppContent />
    </Router>
  );
}

export default App;