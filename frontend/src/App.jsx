import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import Header from './components/Header';
import Login from './components/Login';
import Signin from './components/Signin';




function App() {

  const bgGradient = {
    background: 'radial-gradient(circle at center, #1a364d 0%, #10202d 50%, #101422 100%)',
  };

  return (
    <Router>
      <div
        style={bgGradient}
        className="min-h-screen flex flex-col items-center justify-center p-4 sm:p-6 lg:p-8"
      >
        <Header />
        <Routes>

          <Route path="/login" element={<Login />} />
          <Route path="/signin" element={<Signin />} />
        </Routes>
      </div>

        
    </Router>
  );
}

export default App;