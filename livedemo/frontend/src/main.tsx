import {
  QueryClient,
  QueryClientProvider,
  useMutation,
  useQuery,
  useQueryClient,
} from "@tanstack/react-query";
import React, { FormEvent, useMemo, useState } from "react";
import ReactDOM from "react-dom/client";
import "./styles.css";

import {
  ArticleSummary,
  StructuredArticleRecord,
  CorpusDetail,
  CorpusSummary,
  ExecutionDetail,
  ExecutionResultJson,
  RankingEntry,
  createCorpus,
  decomposeArticle,
  deleteCorpus,
  getArticle,
  getCorpus,
  getExecution,
  listCorpora,
  runCompareExecution,
  runRankExecution,
  runSelectExecution,
  uploadArticles,
} from "./api/client";

const queryClient = new QueryClient();

function App() {
  const [selectedCorpusId, setSelectedCorpusId] = useState<string | null>(null);
  const [selectedArticleId, setSelectedArticleId] = useState<string | null>(null);
  const [selectedExecutionId, setSelectedExecutionId] = useState<string | null>(
    null,
  );
  const corpora = useQuery({ queryKey: ["corpora"], queryFn: listCorpora });

  const selectedCorpus = useMemo(() => {
    return corpora.data?.find((corpus) => corpus.id === selectedCorpusId) ?? null;
  }, [corpora.data, selectedCorpusId]);

  return (
    <main className="app-shell">
      <aside className="sidebar">
        <header className="brand-block">
          <p className="eyebrow">Live Demo</p>
          <h1>News Ranker</h1>
        </header>
        <NewCorpusForm
          onCreated={(id) => {
            setSelectedCorpusId(id);
            setSelectedArticleId(null);
          }}
        />
      </aside>

      <section className="workspace" aria-label="Corpus workspace">
        <CorpusList
          corpora={corpora.data ?? []}
          isLoading={corpora.isLoading}
          error={corpora.error}
          selectedCorpusId={selectedCorpusId}
          onSelect={(id) => {
            setSelectedCorpusId(id);
            setSelectedArticleId(null);
            setSelectedExecutionId(null);
          }}
        />
        {selectedCorpusId ? (
          <CorpusPanel
            corpusId={selectedCorpusId}
            fallbackCorpus={selectedCorpus}
            selectedArticleId={selectedArticleId}
            onSelectArticle={setSelectedArticleId}
            selectedExecutionId={selectedExecutionId}
            onSelectExecution={setSelectedExecutionId}
            onDeleted={() => {
              setSelectedCorpusId(null);
              setSelectedArticleId(null);
              setSelectedExecutionId(null);
            }}
          />
        ) : (
          <EmptyWorkspace />
        )}
      </section>
    </main>
  );
}

function NewCorpusForm({ onCreated }: { onCreated: (id: string) => void }) {
  const queryClient = useQueryClient();
  const [name, setName] = useState("");
  const [notes, setNotes] = useState("");
  const mutation = useMutation({
    mutationFn: createCorpus,
    onSuccess: async ({ id }) => {
      setName("");
      setNotes("");
      await queryClient.invalidateQueries({ queryKey: ["corpora"] });
      onCreated(id);
    },
  });

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    mutation.mutate({ name, notes: notes || undefined });
  }

  return (
    <form className="new-corpus" onSubmit={handleSubmit}>
      <label>
        Name
        <input
          value={name}
          onChange={(event) => setName(event.target.value)}
          required
          maxLength={200}
        />
      </label>
      <label>
        Notes
        <textarea
          value={notes}
          onChange={(event) => setNotes(event.target.value)}
          rows={3}
        />
      </label>
      <button type="submit" disabled={mutation.isPending || !name.trim()}>
        Create Corpus
      </button>
      {mutation.error && <p className="error-line">{mutation.error.message}</p>}
    </form>
  );
}

function CorpusList({
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
        <h2 id="corpora-title">Corpora</h2>
        <span>{corpora.length}</span>
      </div>
      {isLoading && <p className="muted">Loading corpora</p>}
      {error && <p className="error-line">{error.message}</p>}
      {!isLoading && corpora.length === 0 && (
        <p className="muted">No corpora yet.</p>
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

function CorpusPanel({
  corpusId,
  fallbackCorpus,
  selectedArticleId,
  onSelectArticle,
  selectedExecutionId,
  onSelectExecution,
  onDeleted,
}: {
  corpusId: string;
  fallbackCorpus: CorpusSummary | null;
  selectedArticleId: string | null;
  onSelectArticle: (id: string | null) => void;
  selectedExecutionId: string | null;
  onSelectExecution: (id: string | null) => void;
  onDeleted: () => void;
}) {
  const queryClient = useQueryClient();
  const corpus = useQuery({
    queryKey: ["corpus", corpusId],
    queryFn: () => getCorpus(corpusId),
  });
  const uploadMutation = useMutation({
    mutationFn: (files: FileList) => uploadArticles(corpusId, files),
    onSuccess: async () => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ["corpora"] }),
        queryClient.invalidateQueries({ queryKey: ["corpus", corpusId] }),
      ]);
    },
  });
  const deleteMutation = useMutation({
    mutationFn: () => deleteCorpus(corpusId),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["corpora"] });
      onDeleted();
    },
  });
  const rankMutation = useMutation({
    mutationFn: () => runRankExecution(corpusId),
    onSuccess: ({ execution_id }) => onSelectExecution(execution_id),
  });
  const selectMutation = useMutation({
    mutationFn: () => {
      const articleCount = detail?.articles.length ?? 1;
      return runSelectExecution(corpusId, Math.min(3, Math.max(1, articleCount)));
    },
    onSuccess: ({ execution_id }) => onSelectExecution(execution_id),
  });
  const compareMutation = useMutation({
    mutationFn: () => runCompareExecution(corpusId),
    onSuccess: ({ execution_id }) => onSelectExecution(execution_id),
  });

  const detail = corpus.data;
  const heading = detail?.name ?? fallbackCorpus?.name ?? "Corpus";

  return (
    <section className="detail-panel" aria-labelledby="corpus-title">
      <header className="detail-header">
        <div>
          <p className="eyebrow">Corpus</p>
          <h2 id="corpus-title">{heading}</h2>
          {detail?.notes && <p className="notes">{detail.notes}</p>}
        </div>
        <button
          className="danger"
          disabled={deleteMutation.isPending}
          onClick={() => deleteMutation.mutate()}
          type="button"
        >
          Delete
        </button>
      </header>

      <label className="upload-zone">
        <input
          accept=".txt,text/plain"
          multiple
          onChange={(event) => {
            if (event.target.files?.length) {
              uploadMutation.mutate(event.target.files);
              event.target.value = "";
            }
          }}
          type="file"
        />
        <span>Upload .txt Articles</span>
      </label>
      {uploadMutation.error && (
        <p className="error-line">{uploadMutation.error.message}</p>
      )}
      {deleteMutation.error && (
        <p className="error-line">{deleteMutation.error.message}</p>
      )}

      {corpus.isLoading && <p className="muted">Loading articles</p>}
      {corpus.error && <p className="error-line">{corpus.error.message}</p>}
      {detail && (
        <>
          <ExecutionControls
            articleCount={detail.articles.length}
            isRunning={
              rankMutation.isPending ||
              selectMutation.isPending ||
              compareMutation.isPending
            }
            onCompare={() => compareMutation.mutate()}
            onRank={() => rankMutation.mutate()}
            onSelect={() => selectMutation.mutate()}
          />
          {rankMutation.error && (
            <p className="error-line">{rankMutation.error.message}</p>
          )}
          {selectMutation.error && (
            <p className="error-line">{selectMutation.error.message}</p>
          )}
          {compareMutation.error && (
            <p className="error-line">{compareMutation.error.message}</p>
          )}
          <div className="article-grid">
            <ArticleList
              articles={detail.articles}
              selectedArticleId={selectedArticleId}
              onSelectArticle={onSelectArticle}
            />
            <ArticleBody articleId={selectedArticleId} />
          </div>
          <ExecutionPanel executionId={selectedExecutionId} />
        </>
      )}
    </section>
  );
}

function ExecutionControls({
  articleCount,
  isRunning,
  onRank,
  onSelect,
  onCompare,
}: {
  articleCount: number;
  isRunning: boolean;
  onRank: () => void;
  onSelect: () => void;
  onCompare: () => void;
}) {
  return (
    <div className="execution-controls">
      <button disabled={isRunning || articleCount === 0} onClick={onRank} type="button">
        Run Rank
      </button>
      <button
        disabled={isRunning || articleCount === 0}
        onClick={onSelect}
        type="button"
      >
        Run Select
      </button>
      <button
        disabled={isRunning || articleCount === 0}
        onClick={onCompare}
        type="button"
      >
        Compare Profiles
      </button>
    </div>
  );
}

function ExecutionPanel({ executionId }: { executionId: string | null }) {
  const execution = useQuery({
    queryKey: ["execution", executionId],
    queryFn: () => getExecution(executionId ?? ""),
    enabled: executionId !== null,
    refetchInterval: (query) => {
      const data = query.state.data as ExecutionDetail | undefined;
      return data?.status === "pending" || data?.status === "running"
        ? 1000
        : false;
    },
  });

  if (!executionId) {
    return null;
  }
  if (execution.isLoading) {
    return <section className="execution-panel muted">Loading execution</section>;
  }
  if (execution.error) {
    return (
      <section className="execution-panel error-line">
        {execution.error.message}
      </section>
    );
  }
  if (!execution.data) {
    return null;
  }

  return (
    <section className="execution-panel" aria-labelledby="execution-title">
      <header>
        <div>
          <p className="eyebrow">Execution</p>
          <h3 id="execution-title">{formatGroupName(execution.data.kind)}</h3>
        </div>
        <span className={`status-pill ${execution.data.status}`}>
          {execution.data.status}
        </span>
      </header>
      {execution.data.error && <p className="error-line">{execution.data.error}</p>}
      <details>
        <summary>Parameters</summary>
        <pre>{JSON.stringify(execution.data.config_json, null, 2)}</pre>
      </details>
      {execution.data.results.map((result) => (
        <ResultPayloadTable
          key={result.id}
          payload={result.result_json}
          selectedArticleIds={selectedArticleIds(result.result_json)}
        />
      ))}
    </section>
  );
}

function ResultPayloadTable({
  payload,
  selectedArticleIds,
}: {
  payload: ExecutionResultJson;
  selectedArticleIds: Set<string>;
}) {
  if (payload.__type__ === "profile_comparison") {
    return (
      <div className="comparison-grid">
        {Object.entries(payload.rankings).map(([profile, ranking]) => (
          <RankingTable
            entries={ranking.entries}
            key={profile}
            profile={profile}
            selectedArticleIds={selectedArticleIds}
          />
        ))}
      </div>
    );
  }

  if (payload.__type__ === "selection_result") {
    return (
      <RankingTable
        entries={payload.ranking.entries}
        profile={`${payload.profile} · selected ${payload.m}`}
        selectedArticleIds={selectedArticleIds}
      />
    );
  }

  return (
    <RankingTable
      entries={payload.entries}
      profile={payload.profile}
      selectedArticleIds={selectedArticleIds}
    />
  );
}

function RankingTable({
  profile,
  entries,
  selectedArticleIds,
}: {
  profile: string;
  entries: RankingEntry[];
  selectedArticleIds: Set<string>;
}) {
  return (
    <div className="result-table-wrap">
      <h4>{profile}</h4>
      <table className="result-table">
        <thead>
          <tr>
            <th>Rank</th>
            <th>Article</th>
            <th>Score</th>
            <th>Centrality</th>
            <th>Coverage</th>
            <th>Density</th>
            <th>Entities</th>
          </tr>
        </thead>
        <tbody>
          {entries.map((entry) => (
            <tr key={entry.article_id}>
              <td>{entry.rank}</td>
              <td>
                {entry.article_id}
                {selectedArticleIds.has(entry.article_id) && (
                  <span className="selected-badge">Selected</span>
                )}
              </td>
              <td>{formatScore(entry.score)}</td>
              <td>{formatScore(entry.components.centrality)}</td>
              <td>{formatScore(entry.components.coverage)}</td>
              <td>{formatScore(entry.components.density)}</td>
              <td>{formatScore(entry.components.entity_coverage)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function selectedArticleIds(payload: ExecutionResultJson): Set<string> {
  if (payload.__type__ !== "selection_result") {
    return new Set();
  }
  return new Set(payload.selected.map((entry) => entry.article_id));
}

function formatScore(value: number | undefined) {
  return typeof value === "number" ? value.toFixed(3) : "n/a";
}

function ArticleList({
  articles,
  selectedArticleId,
  onSelectArticle,
}: {
  articles: ArticleSummary[];
  selectedArticleId: string | null;
  onSelectArticle: (id: string) => void;
}) {
  if (articles.length === 0) {
    return <p className="muted">No articles uploaded.</p>;
  }

  return (
    <div className="article-list">
      {articles.map((article) => (
        <button
          className={article.id === selectedArticleId ? "selected" : ""}
          key={article.id}
          onClick={() => onSelectArticle(article.id)}
          type="button"
        >
          <strong>{article.title}</strong>
          <span>{article.filename}</span>
          <small>
            {article.body_length.toLocaleString()} chars ·{" "}
            {article.decomposition_status === "decomposed"
              ? "Decomposed"
              : "Pending"}
          </small>
        </button>
      ))}
    </div>
  );
}

function ArticleBody({ articleId }: { articleId: string | null }) {
  const queryClient = useQueryClient();
  const article = useQuery({
    queryKey: ["article", articleId],
    queryFn: () => getArticle(articleId ?? ""),
    enabled: articleId !== null,
  });
  const decomposeMutation = useMutation({
    mutationFn: () => decomposeArticle(articleId ?? ""),
    onSuccess: async () => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ["article", articleId] }),
        queryClient.invalidateQueries({ queryKey: ["corpus"] }),
      ]);
    },
  });

  if (!articleId) {
    return <div className="article-body muted">Select an article.</div>;
  }
  if (article.isLoading) {
    return <div className="article-body muted">Loading article</div>;
  }
  if (article.error) {
    return <div className="article-body error-line">{article.error.message}</div>;
  }
  if (!article.data) {
    return null;
  }
  return (
    <div className="article-inspector">
      <article className="article-body">
        <header>
          <div>
            <h3>{article.data.title}</h3>
            <p>{article.data.filename}</p>
          </div>
          <button
            disabled={decomposeMutation.isPending}
            onClick={() => decomposeMutation.mutate()}
            type="button"
          >
            {decomposeMutation.isPending ? "Running" : "Decompose"}
          </button>
        </header>
        {decomposeMutation.error && (
          <p className="error-line">{decomposeMutation.error.message}</p>
        )}
        <pre>{article.data.body}</pre>
      </article>
      <StructuredPanel structured={article.data.structured_article} />
    </div>
  );
}

function StructuredPanel({
  structured,
}: {
  structured: StructuredArticleRecord | null;
}) {
  if (!structured) {
    return (
      <aside className="structured-panel muted">
        <h3>Structured</h3>
        <p>No decomposition yet.</p>
      </aside>
    );
  }

  const payload = structured.payload_json;
  const entityGroups = Object.entries(payload.entities);

  return (
    <aside className="structured-panel">
      <header>
        <div>
          <p className="eyebrow">Structured</p>
          <h3>{payload.headline_neutral}</h3>
        </div>
        <small>{structured.llm_model}</small>
      </header>
      <section>
        <h4>Topic</h4>
        <p>{payload.topic}</p>
      </section>
      <section>
        <h4>Entities</h4>
        <div className="entity-groups">
          {entityGroups.map(([group, entities]) => (
            <div key={group}>
              <strong>{formatGroupName(group)}</strong>
              {entities.length === 0 ? (
                <p className="muted">None</p>
              ) : (
                entities.map((entity) => (
                  <p key={`${group}-${entity.name}`}>
                    {entity.name}
                    {entity.role ? <span>{entity.role}</span> : null}
                  </p>
                ))
              )}
            </div>
          ))}
        </div>
      </section>
      <section>
        <h4>Events</h4>
        {payload.events.map((event) => (
          <div className="fact-row" key={event.id}>
            <strong>{event.what}</strong>
            <span>{event.who.join(", ") || "Unknown"}</span>
          </div>
        ))}
      </section>
      <section>
        <h4>Claims</h4>
        {payload.claims.map((claim) => (
          <div className="fact-row" key={claim.id}>
            <strong>{claim.statement}</strong>
            <span>{claim.attributed_to ?? claim.type}</span>
          </div>
        ))}
      </section>
      {payload.context.length > 0 && (
        <section>
          <h4>Context</h4>
          {payload.context.map((item) => (
            <p key={item}>{item}</p>
          ))}
        </section>
      )}
    </aside>
  );
}

function formatGroupName(group: string) {
  return group.replace("_", " ");
}

function EmptyWorkspace() {
  return (
    <section className="detail-panel empty-state" aria-label="No corpus selected">
      <h2>Choose a Corpus</h2>
      <p className="muted">Create or select a corpus to manage text articles.</p>
    </section>
  );
}

ReactDOM.createRoot(document.getElementById("root") as HTMLElement).render(
  <React.StrictMode>
    <QueryClientProvider client={queryClient}>
      <App />
    </QueryClientProvider>
  </React.StrictMode>,
);
