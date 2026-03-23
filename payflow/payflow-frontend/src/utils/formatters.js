export function formatCurrency(value, currency = "USD") {
  const number = Number(value);

  if (!Number.isFinite(number)) {
    return new Intl.NumberFormat("en-US", {
      style: "currency",
      currency,
    }).format(0);
  }

  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency,
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(number);
}

export function formatRelativeAmount(value, isSent, currency = "USD") {
  const formatted = formatCurrency(value, currency);
  return `${isSent ? "-" : "+"}${formatted}`;
}

export function formatDate(value) {
  if (!value) return "-";

  const date = new Date(value);

  if (Number.isNaN(date.getTime())) {
    return "-";
  }

  return date.toLocaleString();
}