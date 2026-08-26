# Importar un historial de MetaTrader 5

EmoVest importa reportes HTML generados por MetaTrader 5. El archivo se
procesa dentro de la aplicación de escritorio: no se sube a Internet, no se
renderiza como una página y no se cargan imágenes, scripts o enlaces externos.

## Preparar el reporte en MT5

1. Abre la pestaña **Historial** de la caja de herramientas de MetaTrader 5.
2. Selecciona el periodo completo que quieres revisar.
3. Muestra el historial como **Deals/Operaciones**, no únicamente como órdenes.
4. Abre el menú contextual, elige **Reporte** y guarda el archivo HTML.
5. Conserva el reporte original hasta comprobar la vista previa de EmoVest.

La primera versión importa posiciones completamente cerradas. Las posiciones
que sigan abiertas aparecen en la vista previa como omitidas y no se escriben
en la base de datos.

## Importar en EmoVest

1. Abre **Operaciones**, selecciona la cuenta de destino y pulsa **Importar**.
2. Elige **MetaTrader 5 — reporte HTML**.
3. Selecciona el archivo y la zona horaria IANA del servidor del broker. La
   hora mostrada por MT5 pertenece al servidor del broker, no necesariamente a
   la zona horaria de Windows o macOS.
4. Revisa las operaciones propuestas, las filas omitidas, los duplicados y los
   movimientos de cuenta.
5. Si una cuenta hedging contiene cierres ambiguos, asigna las filas al grupo
   correcto. EmoVest no permite confirmar hasta que símbolo, dirección,
   cronología y volumen sean coherentes.
6. Confirma la importación. El archivo se vuelve a validar y todas las filas se
   guardan en una única transacción.

Importar otra vez el mismo archivo, o un reporte cuyo periodo se solape con uno
anterior, no crea deals duplicados.

La sección **Agrupación manual avanzada** muestra las filas normalizadas y su
`source_key`. Una resolución es una lista JSON de grupos; cada grupo declara un
identificador, el lado y las filas de entrada y salida:

```json
[
  {
    "position": "manual-1",
    "tipo_operacion": "LONG",
    "entries": ["source-key-deal-entrada"],
    "exits": ["source-key-deal-salida-1", "source-key-deal-salida-2"]
  }
]
```

Después de editarla hay que volver a previsualizar. Una fila no puede estar en
dos grupos y la cantidad total de entradas y salidas debe coincidir.

## Formatos y límites

- Reportes de MetaTrader 5 en español o inglés.
- HTML codificado como UTF-8, UTF-16 o Windows-1252.
- Tamaño máximo: 10 MiB.
- Máximo: 100.000 filas de historial.
- Se requiere una cuenta de origen y tickets de deal identificables para una
  deduplicación segura.

Los CSV creados por brokers no siguen un contrato universal y no deben
seleccionarse en el importador de MetaTrader. El menú **CSV de EmoVest** está
reservado para exportaciones de EmoVest, incluidas las versiones antiguas del
formato plano. Las exportaciones nuevas incluyen estado, cantidad abierta,
fecha de cierre, costes y el JSON de salidas; al reimportarlas se conserva ese
detalle.

## Resultados y costes

Para operaciones importadas, EmoVest conserva el beneficio, la comisión, el
swap y las tasas indicadas por el broker. No recalcula el resultado a partir de
la diferencia de precios y los lotes, ya que esa fórmula no representa todos
los contratos Forex, CFD, futuros ni conversiones de divisa.

Los depósitos, retiradas y ajustes generales se guardan como movimientos de
cuenta. Afectan al saldo, pero no cuentan como P&L de trading, operaciones para
el winrate o rachas. Las estadísticas exponen por separado la vista por
operación cerrada, la vista por ejecución de salida y el resumen de movimientos.
