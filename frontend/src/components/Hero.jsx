import React from 'react';
import { Link } from 'react-router-dom';

const Hero = () => {
  return (
    <div className="min-h-screen bg-gradient-to-br from-[#050a10] via-[#1a364d] to-[#101422]">
      {/* Hero Section */}
      <section className="relative overflow-hidden pt-24 sm:pt-68">
        <div className="container mx-auto px-6 pt-35 pb-70 sm:px-8 lg:px-12 py-20 lg:pt-25">
          <div className="text-center">
            <h1 className="text-4xl sm:text-5xl lg:text-6xl font-bold text-white mb-6 tracking-tight">
              Invierte con
              <span className="text-blue-400"> Inteligencia Emocional</span>
            </h1>
            <p className="text-lg sm:text-xl text-gray-300 mb-8 max-w-3xl mx-auto">
              Descubre el poder de combinar análisis financiero avanzado con inteligencia emocional para tomar decisiones de inversión más inteligentes y rentables.
            </p>
            <div className="flex flex-col sm:flex-row gap-4 justify-center">
              <Link 
                to="/login" 
                className="px-8 py-4 bg-blue-600 hover:bg-blue-700 text-white font-semibold rounded-full transition-all duration-300 hover:scale-105 shadow-lg"
              >
                Comenzar Ahora
              </Link>
              <Link 
                to="#sobre-nosotros" 
                className="px-8 py-4 border-2 border-purple-600/30 text-blue-400 hover:bg-purple-600 hover:text-white font-semibold rounded-full transition-all duration-300"
              >
                Saber Más
              </Link>
              <div id="que-somos"></div>
            </div>
          </div>
        </div>
      </section>

      {/* Quienes Somos Section */}
      <section className="py-20 pl-16 pr-16">
        <div className="container mx-auto px-6 sm:px-8 lg:px-12">
          <div className="text-center mb-12">
            <h2 className="text-3xl sm:text-4xl font-bold text-white mb-4">
              ¿Quiénes <span className="text-blue-400">Somos?</span>
            </h2>
            <p className="text-gray-300 max-w-2xl mx-auto">
              Somos un equipo de apasionados de las finanzas y la psicología dedicados a revolucionar el mundo de las inversiones.
            </p>
          </div>
          
          <div className="grid md:grid-cols-3 gap-8">
            <div className="bg-white/5 backdrop-blur-xl rounded-2xl p-6 border border-white/10">
              <div className="w-12 h-12 bg-blue-600 rounded-full flex items-center justify-center mb-4">
                <span className="text-white font-bold text-xl">1</span>
              </div>
              <h3 className="text-xl font-semibold text-white mb-3">Misión</h3>
              <p className="text-gray-300">
                Democratizar el acceso a herramientas de inversión avanzadas basadas en inteligencia emocional para todos los inversores.
              </p>
            </div>
            
            <div className="bg-white/5 backdrop-blur-xl rounded-2xl p-6 border border-white/10">
              <div className="w-12 h-12 bg-green-600 rounded-full flex items-center justify-center mb-4">
                <span className="text-white font-bold text-xl">2</span>
              </div>
              <h3 className="text-xl font-semibold text-white mb-3">Visión</h3>
              <p className="text-gray-300">
                Convertirnos en la plataforma líder global de inversión emocionalmente inteligente.
              </p>
            </div>
            
            <div className="bg-white/5 backdrop-blur-xl rounded-2xl p-6 border border-white/10">
              <div className="w-12 h-12 bg-purple-600 rounded-full flex items-center justify-center mb-4">
                <span className="text-white font-bold text-xl">3</span>
              </div>
              <h3 className="text-xl font-semibold text-white mb-3">Valores</h3>
              <p className="text-gray-300">
                Innovación, transparencia, educación y éxito compartido con nuestros usuarios.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* Suscripciones Section */}
      <section id="suscripciones" className="py-20 bg-black/20">
  <div className="container mx-auto px-6 sm:px-8 lg:px-12">
    <div className="text-center mb-12">
      <h2 className="text-3xl sm:text-4xl font-bold text-white mb-4">
        Nuestras <span className="text-green-400">Suscripciones</span>
      </h2>
      <p className="text-gray-300 max-w-2xl mx-auto">
        Elige el plan perfecto para tu perfil de inversor y empieza a transformar tu estrategia.
      </p>
    </div>

    <div className="grid md:grid-cols-3 gap-8 max-w-6xl mx-auto items-stretch">
      {/* Plan Gratis */}
      <div className="bg-white/5 backdrop-blur-xl rounded-2xl p-8 border border-white/10 hover:border-blue-500/50 transition-all duration-300 flex flex-col">
        <h3 className="text-2xl font-bold text-white mb-2">Gratis</h3>
        <p className="text-gray-400 mb-6">Plan idóneo para probar Emovest.</p>
        <div className="text-4xl font-bold text-white mb-6">
          0€<span className="text-lg text-gray-400 font-normal">/mes</span>
        </div>
        <ul className="space-y-3 mb-8 flex-grow">
          <li className="flex items-start text-gray-300">
            <span className="text-green-400 mr-2">✓</span>
            Análisis básico de emociones
          </li>
          <li className="flex items-start text-gray-300">
            <span className="text-green-400 mr-2">✓</span>
            Hasta 15 registros mensuales
          </li>
          <li className="flex items-start text-gray-300">
            <span className="text-green-400 mr-2">✓</span>
            Acceso al diario emocional
          </li>
        </ul>
        <button 
          onClick={() => window.location.href = '/signin'}
          className="w-full py-3 bg-blue-600 hover:bg-blue-700 text-white font-semibold rounded-xl transition-all duration-300 mt-auto cursor-pointer"
        >
          Empezar
        </button>
      </div>

      {/* Plan Profesional */}
      <div className="bg-white/5 backdrop-blur-xl rounded-2xl p-8 border-2 border-green-500/50 hover:border-green-400 transition-all duration-300 relative flex flex-col scale-105 z-10">
        <div className="absolute -top-4 left-1/2 transform -translate-x-1/2 bg-green-600 text-white px-4 py-1 rounded-full text-sm font-semibold whitespace-nowrap">
          Recomendado
        </div>
        <h3 className="text-2xl font-bold text-white mb-2">Profesional</h3>
        <p className="text-gray-400 mb-6">Para inversores serios</p>
        <div className="mb-6">
          <div className="text-4xl font-bold text-white">14.99€<span className="text-lg text-gray-400 font-normal">/mes</span></div>
          <div className="text-sm text-green-400 font-medium">o 119€ al año (ahorra 33%)</div>
        </div>
        <ul className="space-y-3 mb-8 flex-grow">
          <li className="flex items-start text-gray-300">
            <span className="text-green-400 mr-2">✓</span>
            Registros ilimitados
          </li>
          <li className="flex items-start text-gray-300">
            <span className="text-green-400 mr-2">✓</span>
            Gestión emocional avanzada
          </li>
          <li className="flex items-start text-gray-300">
            <span className="text-green-400 mr-2">✓</span>
            Exportación de datos
          </li>
          <li className="flex items-start text-gray-300">
            <span className="text-green-400 mr-2">✓</span>
            Coaching personalizado
          </li>
        </ul>
        <button 
          onClick={() => window.location.href = '/signin'}
          className="w-full py-3 bg-green-600 hover:bg-green-700 text-white font-semibold rounded-xl transition-all duration-300 mt-auto cursor-pointer"
        >
          Empezar
        </button>
      </div>

      {/* Plan Enterprise */}
      <div className="bg-white/5 backdrop-blur-xl rounded-2xl p-8 border border-white/10 hover:border-purple-500/50 transition-all duration-300 flex flex-col">
        <h3 className="text-2xl font-bold text-white mb-2">Partners / Academia</h3>
        <p className="text-gray-400 mb-6">Para instituciones, escuelas o Academias</p>
        <div className="text-2xl font-bold text-white mb-6">
          Cupos por volúmenes<span className="text-lg text-gray-400 font-normal"></span>
        </div>
        <ul className="space-y-3 mb-8 flex-grow">
          <li className="flex items-start text-gray-300">
            <span className="text-green-400 mr-2">✓</span>
            Acceso premium para estudiantes
          </li>
          <li className="flex items-start text-gray-300">
            <span className="text-green-400 mr-2">✓</span>
            API completa
          </li>
          <li className="flex items-start text-gray-300">
            <span className="text-green-400 mr-2">✓</span>
            Soporte prioritario
          </li>
          <li className="flex items-start text-gray-300">
            <span className="text-green-400 mr-2">✓</span>
            Integración personalizada
          </li>
        </ul>
        <button id="sobre-nosotros" className="w-full py-3 bg-purple-600 hover:bg-purple-700 text-white font-semibold rounded-xl transition-all duration-300 mt-auto">
          Contactar
        </button>
      </div>
    </div>
  </div>
</section>

      {/* Sobre Nosotros Section */}
      <section className="py-20 pl-16 pr-16">
        <div className="container mx-auto px-6 sm:px-8 lg:px-12">
          <div className="grid lg:grid-cols-2 gap-12 items-center">
            <div>
              <h2 className="text-3xl sm:text-4xl font-bold text-white mb-6">
                Sobre <span className="text-blue-400">EmoVest</span>
              </h2>
              <p className="text-gray-300 mb-6">
                Fundada en 2026, EmoVest nació de una simple pero poderosa idea: las decisiones financieras no deben basarse únicamente en datos fríos y análisis técnicos. Las emociones juegan un papel crucial en cómo invertimos, y entenderlas es la clave del éxito.
              </p>
              <p className="text-gray-300 mb-6">
                Nuestra plataforma combina algoritmos de inteligencia artificial para proporcionar ayuda a nuestros usuarios a tomar mejores decisiones de inversión.
              </p>
              <div className="flex flex-wrap gap-4">
                <div className="text-center">
                  <div className="text-3xl font-bold text-green-400 mb-1">85%</div>
                  <div className="text-gray-400 text-sm">Tasa de Éxito</div>
                </div>
                <div className="text-center">
                  <div className="text-3xl font-bold text-purple-400 mb-1">24/7</div>
                  <div className="text-gray-400 text-sm">Análisis Continuo</div>
                </div>
              </div>
            </div>
            <div className="bg-white/5 backdrop-blur-xl rounded-2xl p-8 border border-white/10">
              <h3 className="text-2xl font-bold text-white mb-6">Nuestra Tecnología</h3>
              <div className="space-y-4">
                <div className="flex items-start space-x-4">
                  <div className="w-8 h-8 bg-blue-600 rounded-full flex items-center justify-center flex-shrink-0">
                    <span className="text-white text-sm font-bold">AI</span>
                  </div>
                  <div>
                    <h4 className="text-lg font-semibold text-white mb-2">Inteligencia Artificial</h4>
                    <p className="text-gray-300 text-sm">
                      Algoritmos que analizan patrones emocionales y de mercado en tiempo real.
                    </p>
                  </div>
                </div>
                <div className="flex items-start space-x-4">
                  <div className="w-8 h-8 bg-green-600 rounded-full flex items-center justify-center flex-shrink-0">
                    <span className="text-white text-sm font-bold">PS</span>
                  </div>
                  <div>
                    <h4 className="text-lg font-semibold text-white mb-2">Psicología Financiera</h4>
                    <p className="text-gray-300 text-sm">
                      Principios probados de comportamiento inversor y gestión emocional.
                    </p>
                  </div>
                </div>
                <div className="flex items-start space-x-4">
                  <div className="w-8 h-8 bg-purple-600 rounded-full flex items-center justify-center flex-shrink-0">
                    <span className="text-white text-sm font-bold">BD</span>
                  </div>
                  <div>
                    <h4 className="text-lg font-semibold text-white mb-2">Big Data</h4>
                    <p className="text-gray-300 text-sm">
                      Análisis de millones de puntos de datos para predicciones precisas.
                    </p>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>
    </div>
  );
};

export default Hero;