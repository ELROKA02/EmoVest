import React from 'react';
import { Link } from 'react-router-dom';

const contactEmail = 'contactoemovest@gmail.com';

const glassCard = 'relative overflow-hidden rounded-2xl border border-white/10 bg-white/5 shadow-2xl shadow-black/20 backdrop-blur-xl';

const painPoints = [
  'Repites errores y después los justificas como estrategia.',
  'Tienes notas, capturas o excels, pero no los revisas de forma sistemática.',
  'Sospechas que tus peores días coinciden con miedo, euforia o exceso de confianza.',
];

const workflow = [
  {
    step: '01',
    title: 'Registra la operación',
    text: 'Cuenta, resultado, confianza, captura y nota emocional en el mismo flujo.',
  },
  {
    step: '02',
    title: 'La IA interpreta patrones',
    text: 'El análisis emocional es orientativo y te ayuda a ordenar lo que escribes.',
  },
  {
    step: '03',
    title: 'Revisa con datos',
    text: 'Une resultado, drawdown, rachas y emociones para aprender de tu propio proceso.',
  },
];

const valueCards = [
  {
    title: 'Diario de trading completo',
    text: 'Sustituye notas sueltas por un historial claro de operaciones, cuentas y contexto.',
    tint: 'from-violet-500/40',
  },
  {
    title: 'Patrones emocionales visibles',
    text: 'Convierte miedo, duda, euforia o confianza en señales que puedes revisar con calma.',
    tint: 'from-fuchsia-500/35',
  },
  {
    title: 'Privacidad primero',
    text: 'Arquitectura pensada para análisis local con Ollama, sin vender humo ni señales de trading.',
    tint: 'from-blue-500/35',
  },
];

const Hero = () => {
  return (
    <div className="min-h-screen bg-[#050a10] text-white">
      <section className="relative isolate overflow-hidden pt-28">
        <div className="absolute inset-0 -z-10 bg-[radial-gradient(circle_at_18%_18%,rgba(139,92,246,0.34),transparent_28%),radial-gradient(circle_at_82%_16%,rgba(192,38,211,0.22),transparent_24%),radial-gradient(circle_at_54%_76%,rgba(59,130,246,0.16),transparent_30%),linear-gradient(135deg,#050a10_0%,#10202d_48%,#101422_100%)]" />
        <div className="absolute inset-x-0 bottom-0 -z-10 h-40 bg-gradient-to-t from-[#050a10] to-transparent" />

        <div className="container mx-auto grid min-h-[calc(100vh-7rem)] max-w-7xl items-center gap-12 px-6 pb-20 pt-14 sm:px-8 lg:grid-cols-[1fr_0.95fr] lg:px-12">
          <div className="max-w-3xl">
            <h1 className="text-4xl font-black leading-tight tracking-tight sm:text-5xl lg:text-6xl">
              Deja de operar contra tus emociones sin darte cuenta.
            </h1>
            <p className="mt-6 max-w-2xl text-lg leading-8 text-slate-300 sm:text-xl">
              EmoVest te ayuda a registrar operaciones, detectar patrones emocionales y revisar tu rendimiento con contexto. No damos señales ni asesoramiento financiero: te damos un espejo más claro de tu proceso.
            </p>
            <div className="mt-9 flex flex-col gap-4 sm:flex-row">
              <Link
                to="/signup"
                className="inline-flex justify-center rounded-full bg-gradient-to-r from-violet-600 to-fuchsia-600 px-8 py-4 text-sm font-bold uppercase tracking-wider text-white shadow-lg shadow-violet-900/40 transition hover:from-violet-500 hover:to-fuchsia-500"
              >
                Crear mi diario gratis
              </Link>
              <a
                href="#como-funciona"
                className="inline-flex justify-center rounded-full border border-white/20 bg-white/5 px-8 py-4 text-sm font-bold uppercase tracking-wider text-white backdrop-blur-xl transition hover:border-violet-300/60 hover:bg-white/10"
              >
                Ver cómo funciona
              </a>
            </div>
            <p className="mt-5 text-sm text-slate-400">
              Prueba gratuita disponible del 29 de mayo al 21 de junio de 2026.
            </p>
          </div>

          <div className={`${glassCard} p-5`}>
            <div className="absolute right-0 top-0 h-36 w-36 rounded-full bg-gradient-to-br from-violet-500/50 to-transparent -mr-16 -mt-16" />
            <div className="absolute bottom-0 left-0 h-28 w-28 rounded-full bg-gradient-to-tr from-fuchsia-500/35 to-transparent -mb-14 -ml-14" />
            <div className="relative">
              <div className="mb-5 flex items-center justify-between gap-4 border-b border-white/10 pb-5">
                <div>
                  <p className="text-sm text-slate-400">Nota del trader</p>
                  <h2 className="text-2xl font-bold">Entrada emocional detectada</h2>
                </div>
                <span className="rounded-full border border-violet-400/30 bg-violet-500/15 px-3 py-1 text-sm font-semibold text-violet-100">
                  Duda
                </span>
              </div>

              <div className="rounded-2xl border border-white/10 bg-[#111827]/80 p-5">
                <p className="text-xs font-semibold uppercase tracking-wider text-violet-300">Nota escrita</p>
                <p className="mt-3 leading-7 text-slate-200">
                  “Entré tarde porque no quería perder el movimiento. Ya venía de una pérdida y dudé de mi plan, pero aun así ejecuté.”
                </p>
              </div>

              <div className="mt-4 grid gap-4 sm:grid-cols-3">
                <div className="rounded-2xl border border-white/10 bg-black/20 p-4">
                  <p className="text-sm text-slate-400">Emoción</p>
                  <p className="mt-2 text-2xl font-black text-violet-300">Duda</p>
                  <p className="mt-1 text-xs text-slate-500">Detectada por IA</p>
                </div>
                <div className="rounded-2xl border border-white/10 bg-black/20 p-4">
                  <p className="text-sm text-slate-400">Win rate</p>
                  <p className="mt-2 text-2xl font-black text-blue-300">41%</p>
                  <p className="mt-1 text-xs text-slate-500">Con esta emoción</p>
                </div>
                <div className="rounded-2xl border border-white/10 bg-black/20 p-4">
                  <p className="text-sm text-slate-400">Neto</p>
                  <p className="mt-2 text-2xl font-black text-fuchsia-300">-320€</p>
                  <p className="mt-1 text-xs text-slate-500">Histórico asociado</p>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      <section id="que-somos" className="py-20">
        <div className="container mx-auto max-w-7xl px-6 sm:px-8 lg:px-12">
          <div className={`${glassCard} p-7 md:p-9`}>
            <div className="absolute right-0 top-0 h-32 w-32 rounded-full bg-gradient-to-br from-violet-500/30 to-transparent -mr-14 -mt-14" />
            <div className="relative grid gap-8 lg:grid-cols-[0.9fr_1.1fr]">
              <div>
                <p className="text-sm font-semibold uppercase tracking-wider text-violet-300">El problema</p>
                <h2 className="mt-3 text-3xl font-bold sm:text-4xl">
                  Tu broker registra operaciones. EmoVest te ayuda a revisar comportamiento.
                </h2>
              </div>
              <div className="space-y-3">
                {painPoints.map((item) => (
                  <div key={item} className="rounded-xl border border-white/10 bg-black/20 p-4 text-slate-300">
                    {item}
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      </section>

      <section id="como-funciona" className="py-20">
        <div className="container mx-auto max-w-7xl px-6 sm:px-8 lg:px-12">
          <div className="max-w-3xl">
            <p className="text-sm font-semibold uppercase tracking-wider text-violet-300">Cómo funciona</p>
            <h2 className="mt-3 text-3xl font-bold sm:text-4xl">
              Un flujo simple para dejar de depender de la memoria.
            </h2>
          </div>

          <div className="mt-10 grid gap-6 md:grid-cols-3">
            {workflow.map((item) => (
              <article key={item.step} className={`${glassCard} p-7 transition hover:border-violet-400/40 hover:bg-white/[0.07]`}>
                <div className="absolute right-0 top-0 h-24 w-24 rounded-full bg-gradient-to-br from-violet-500/20 to-transparent -mr-10 -mt-10" />
                <div className="relative">
                  <span className="text-sm font-black text-fuchsia-300">{item.step}</span>
                  <h3 className="mt-4 text-xl font-bold">{item.title}</h3>
                  <p className="mt-3 leading-7 text-slate-300">{item.text}</p>
                </div>
              </article>
            ))}
          </div>
        </div>
      </section>

      <section id="suscripciones" className="py-20">
        <div className="container mx-auto max-w-7xl px-6 sm:px-8 lg:px-12">
          <div className="mx-auto max-w-3xl text-center">
            <p className="text-sm font-semibold uppercase tracking-wider text-violet-300">Por qué probarlo ahora</p>
            <h2 className="mt-3 text-3xl font-bold sm:text-4xl">
              Construye un historial que explique algo más que ganancias y pérdidas.
            </h2>
            <p className="mt-4 text-lg leading-8 text-slate-300">
              El MVP está en desarrollo activo y ahora puedes entrar gratis para validar si tu proceso mejora cuando revisas emoción, operación y resultado juntos.
            </p>
          </div>

          <div className="mt-12 grid gap-6 lg:grid-cols-3">
            {valueCards.map((card) => (
              <article key={card.title} className={`${glassCard} p-7`}>
                <div className={`absolute right-0 top-0 h-28 w-28 rounded-full bg-gradient-to-br ${card.tint} to-transparent -mr-12 -mt-12`} />
                <div className="relative">
                  <h3 className="text-xl font-bold">{card.title}</h3>
                  <p className="mt-3 leading-7 text-slate-300">{card.text}</p>
                </div>
              </article>
            ))}
          </div>

          <div className={`${glassCard} mt-8 p-7 md:flex md:items-center md:justify-between md:gap-8`}>
            <div>
              <h3 className="text-2xl font-bold">Acceso actual: prueba gratuita</h3>
              <p className="mt-2 max-w-2xl text-slate-300">
                Empieza registrando tus operaciones y revisa qué patrones aparecen. Si tienes dudas sobre acceso, soporte o colaboración, escríbenos.
              </p>
            </div>
            <div className="mt-6 flex flex-col gap-3 sm:flex-row md:mt-0">
              <Link
                to="/signup"
                className="inline-flex justify-center rounded-full bg-gradient-to-r from-violet-600 to-fuchsia-600 px-6 py-3 text-sm font-bold uppercase tracking-wider text-white transition hover:from-violet-500 hover:to-fuchsia-500"
              >
                Crear cuenta gratis
              </Link>
              <a
                href={`mailto:${contactEmail}`}
                className="inline-flex justify-center rounded-full border border-violet-400/30 bg-violet-500/10 px-6 py-3 text-sm font-bold uppercase tracking-wider text-violet-100 transition hover:bg-violet-500/20"
              >
                Contactar
              </a>
            </div>
          </div>
        </div>
      </section>

      <section id="sobre-nosotros" className="py-20">
        <div className="container mx-auto grid max-w-7xl gap-8 px-6 sm:px-8 lg:grid-cols-[0.9fr_1.1fr] lg:px-12">
          <div>
            <p className="text-sm font-semibold uppercase tracking-wider text-violet-300">Sobre EmoVest</p>
            <h2 className="mt-3 text-3xl font-bold sm:text-4xl">
              Para traders que quieren aprender de sus decisiones, no solo archivarlas.
            </h2>
            <p className="mt-5 leading-8 text-slate-300">
              EmoVest nace para tratar el estado mental como parte del diario de trading. La idea no es prometer rentabilidad, sino ayudarte a detectar patrones operativos y emocionales que suelen quedar escondidos entre capturas, notas y resultados.
            </p>
          </div>

          <div className="grid gap-5 sm:grid-cols-2">
            <div className={`${glassCard} p-6`}>
              <p className="text-4xl font-black text-violet-300">IA</p>
              <p className="mt-2 text-slate-300">Interpretación orientativa de tus notas emocionales.</p>
            </div>
            <div className={`${glassCard} p-6`}>
              <p className="text-4xl font-black text-blue-300">24/7</p>
              <p className="mt-2 text-slate-300">Diario disponible para revisar cada operación con contexto.</p>
            </div>
            <div className={`${glassCard} p-6 sm:col-span-2`}>
              <p className="text-sm font-semibold uppercase tracking-wider text-slate-400">Contacto</p>
              <a className="mt-3 block break-words text-2xl font-bold text-violet-300 hover:text-violet-200" href={`mailto:${contactEmail}`}>
                {contactEmail}
              </a>
              <p className="mt-3 text-slate-300">
                Escríbenos para soporte, feedback del MVP o colaboraciones.
              </p>
            </div>
          </div>
        </div>
      </section>
    </div>
  );
};

export default Hero;
