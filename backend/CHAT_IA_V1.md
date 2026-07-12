# Chat analista de EmoVest — V1

LangChain normaliza mensajes, herramientas y streaming entre proveedores. No es
una frontera de seguridad, un sistema de autorizacion ni una fuente de verdad
financiera: esas responsabilidades permanecen en el backend de EmoVest.

- El backend construye el contexto con el usuario autenticado y la cuenta
  confirmada. El modelo no controla esos valores.
- Las herramientas son internas, tipadas y de solo lectura. Cada consulta ORM
  comprueba la propiedad de los datos.
- El modelo y LangChain no acceden directamente a MySQL, endpoints internos,
  archivos, Redis arbitrario ni operaciones de escritura.
- Redis almacena solo sesiones temporales de UX; no autoriza ni aporta datos
  financieros. Las sesiones caducan tras ocho horas de inactividad.
- El backend limita el ciclo secuencial de herramientas a cuatro rondas.

El asistente ofrece analisis educativo de patrones, riesgos y habitos. No da
senales ni ordenes de compra o venta. Sus conclusiones basadas en datos incluyen
evidencias de cuenta, periodo, metricas y operaciones relevantes.

La configuracion de IA sigue siendo global y modificable por cualquier usuario
autenticado, segun la politica actual. Las claves externas permanecen en
variables de entorno, pero permitir cambios globales de proveedor, modelo y URL
supone riesgo operativo y de coste.
