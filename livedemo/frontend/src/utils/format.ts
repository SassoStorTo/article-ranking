export function formatCell(value: unknown): string {
  if (typeof value === "number") {
    return formatScore(value);
  }
  if (Array.isArray(value)) {
    return value.map(String).join(", ");
  }
  if (value === null || value === undefined) {
    return "n/a";
  }
  return String(value);
}

export function formatIdList(value: unknown): string {
  if (Array.isArray(value)) {
    return value.length ? value.map(String).join(", ") : "none";
  }
  return typeof value === "string" ? value : "none";
}

export function formatUnknownScore(value: unknown): string {
  return typeof value === "number" ? formatScore(value) : String(value ?? "n/a");
}

export function formatScore(value: number | undefined) {
  return typeof value === "number" ? value.toFixed(3) : "n/a";
}

export function formatGroupName(group: string) {
  return group.replaceAll("_", " ");
}

export function formatDateTime(value: string | null) {
  return value ? new Date(value).toLocaleString() : "n/a";
}

export function dateStart(value: string) {
  return value ? `${value}T00:00:00` : undefined;
}

export function dateEnd(value: string) {
  return value ? `${value}T23:59:59` : undefined;
}
