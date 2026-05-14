import { CorpusSummary } from "../api/client";

export function CorpusList({
  corpora,
  isLoading,
  error,
  selectedCorpusId,
  onSelect,
}: {
  corpora: CorpusSummary[];
  isLoading: boolean;
  error: Error | null;
  selectedCorpusId: string | null;
  onSelect: (id: string) => void;
}) {
  return (
    <section className="corpus-list" aria-labelledby="corpora-title">
      <div className="section-heading">
        <h2 id="corpora-title">Article Sets</h2>
        <span>{corpora.length}</span>
      </div>
      {isLoading && <p className="muted">Loading article sets</p>}
      {error && <p className="error-line">{error.message}</p>}
      {!isLoading && corpora.length === 0 && (
        <p className="muted">No article sets yet.</p>
      )}
      <div className="corpus-buttons">
        {corpora.map((corpus) => (
          <button
            className={corpus.id === selectedCorpusId ? "selected" : ""}
            key={corpus.id}
            onClick={() => onSelect(corpus.id)}
            type="button"
          >
            <strong>{corpus.name}</strong>
            <span>{corpus.article_count} articles</span>
          </button>
        ))}
      </div>
    </section>
  );
}
