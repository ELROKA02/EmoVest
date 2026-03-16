import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import Header from './components/Header';
import Login from './components/Login';


function App() {

  const bgGradient = {
    background: 'radial-gradient(circle at center, #1a364d 0%, #10202d 50%, #101422 100%)',
  };

  return (
    <Router>
      <div
        style={bgGradient}
        className="min-h-screen flex flex-col items-center justify-center p-6"
      >
        <Header />
        <Routes>

          <Route path="/login" element={<Login />} />
        </Routes>
      </div>
    </Router>
  );
}

export default App;