export function Metric({ label, value }: { label: string; value: unknown }) {
  return (
    <div className="metric">
      <span>{label}</span>
      <strong>{String(value ?? "n/a")}</strong>
    </div>
  );
}
