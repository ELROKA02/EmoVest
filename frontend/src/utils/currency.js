const getCurrencySymbol = (divisa) => {
  switch (divisa) {
    case 'EUR':
      return '€';
    case 'USD':
      return '$';
    default:
      return divisa || '$';
  }
};

const formatCurrency = (amount, divisa = 'USD') => {
  if (amount === null || amount === undefined || amount === '') return '-';

  const value = Number(amount);
  if (Number.isNaN(value)) return '-';

  const hasDecimals = Math.abs(value % 1) >= 0.005;
  const decimalPlaces = hasDecimals ? 2 : 0;

  let formatted = value.toLocaleString('es-ES', {
    minimumFractionDigits: decimalPlaces,
    maximumFractionDigits: decimalPlaces,
  });

  formatted = formatted.replace(/\./g, ' ');

  const symbol = getCurrencySymbol(divisa);
  return divisa === 'EUR' ? `${formatted} ${symbol}` : `${symbol}${formatted}`;
};

export { getCurrencySymbol, formatCurrency };