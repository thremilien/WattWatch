// Formatting helpers shared across components.

const DASH = '—'; // —

export function fmtNumber(value, digits = 1) {
  if (value === null || value === undefined || Number.isNaN(value)) return DASH;
  return value.toLocaleString(undefined, {
    minimumFractionDigits: digits,
    maximumFractionDigits: digits
  });
}

export function fmtWatts(value) {
  if (value === null || value === undefined || Number.isNaN(value)) return DASH;
  return fmtNumber(value, 1);
}

export function fmtVolts(value) {
  return fmtNumber(value, 1);
}

export function fmtAmps(value) {
  return fmtNumber(value, 3);
}

export function fmtKwh(value, digits = 2) {
  return fmtNumber(value, digits);
}

export function fmtEuro(value, digits = 2) {
  return fmtNumber(value, digits);
}

export function humanizeUptime(seconds) {
  if (seconds === null || seconds === undefined || Number.isNaN(seconds) || seconds < 0) {
    return DASH;
  }
  const s = Math.floor(seconds);
  const days = Math.floor(s / 86400);
  const hours = Math.floor((s % 86400) / 3600);
  const minutes = Math.floor((s % 3600) / 60);

  const parts = [];
  if (days > 0) parts.push(`${days}d`);
  if (days > 0 || hours > 0) parts.push(`${hours}h`);
  parts.push(`${minutes}m`);

  return parts.join(' ');
}

export function humanizeAgo(isoTimestamp) {
  if (!isoTimestamp) return 'unknown time';
  const then = new Date(isoTimestamp).getTime();
  if (Number.isNaN(then)) return 'unknown time';
  const diffMs = Date.now() - then;
  const diffSec = Math.max(0, Math.floor(diffMs / 1000));

  if (diffSec < 5) return 'just now';
  if (diffSec < 60) return `${diffSec}s ago`;
  const diffMin = Math.floor(diffSec / 60);
  if (diffMin < 60) return `${diffMin}m ago`;
  const diffHr = Math.floor(diffMin / 60);
  if (diffHr < 24) return `${diffHr}h ago`;
  const diffDay = Math.floor(diffHr / 24);
  return `${diffDay}d ago`;
}

export function fmtClockTime(isoTimestamp) {
  if (!isoTimestamp) return DASH;
  const d = new Date(isoTimestamp);
  if (Number.isNaN(d.getTime())) return DASH;
  return d.toLocaleTimeString(undefined, { hour: '2-digit', minute: '2-digit' });
}

export function fmtDate(isoTimestamp) {
  if (!isoTimestamp) return DASH;
  const d = new Date(isoTimestamp);
  if (Number.isNaN(d.getTime())) return DASH;
  return d.toLocaleDateString(undefined, { month: 'short', day: 'numeric' });
}

export const MONTH_NAMES = [
  'January', 'February', 'March', 'April', 'May', 'June',
  'July', 'August', 'September', 'October', 'November', 'December'
];

export { DASH };
