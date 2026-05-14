import { CorpusSummary } from "../api/client";
import { Metric } from "../components/Metric";

export function HomePage({
  corpora,
  isLoading,
  onCreateCorpus,
  onOpenCorpus,
  onOpenExecutions,
}: {
  corpora: CorpusSummary[];
  isLoading: boolean;
  onCreateCorpus: () => void;
  onOpenCorpus: (id: string) => void;
  onOpenExecutions: () => void;
}) {
  const articleCount = corpora.reduce(
    (total, corpus) => total + corpus.article_count,
    0,
  );
  const newestCorpora = corpora.slice(0, 4);

  return (
    <section className="home-page" aria-labelledby="home-title">
      <div className="home-hero">
        <p className="eyebrow">Workspace</p>
        <h2 id="home-title">Rank event coverage from article set to evidence.</h2>
        <p>
          Create article sets, upload text files, inspect decomposition output,
          run rankings, and compare executions from one local demo.
        </p>
        <div className="home-actions">
          <button onClick={onCreateCorpus} type="button">
            Create Article Set
          </button>
          <button className="secondary" onClick={onOpenExecutions} type="button">
            View Executions
          </button>
        </div>
      </div>
      <div className="home-metrics">
        <Metric label="Article Sets" value={corpora.length} />
        <Metric label="Articles" value={articleCount} />
        <Metric label="Newest" value={corpora[0]?.name ?? "none"} />
      </div>
      <section className="home-recent" aria-labelledby="recent-corpora-title">
        <div className="section-heading">
          <h3 id="recent-corpora-title">Recent Article Sets</h3>
          <span>{corpora.length}</span>
        </div>
        {isLoading && <p className="muted">Loading article sets</p>}
        {!isLoading && newestCorpora.length === 0 ? (
          <p className="muted">Create an article set to begin ranking articles.</p>
        ) : null}
        <div className="corpus-buttons">
          {newestCorpora.map((corpus) => (
            <button
              key={corpus.id}
              onClick={() => onOpenCorpus(corpus.id)}
              type="button"
            >
              <strong>{corpus.name}</strong>
              <span>{corpus.article_count} articles</span>
            </button>
          ))}
        </div>
      </section>
    </section>
  );
}
