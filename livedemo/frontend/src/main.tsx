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
  ExecutionKind,
  ExecutionResultJson,
  ExecutionStatus,
  ExecutionSummary,
  EvaluationArtifact,
  ProfileWeights,
  RankingEntry,
  RankerConfigPayload,
  createClusterInspectionArtifact,
  createComponentTableArtifact,
  createCorpus,
  createRankCorrelationArtifact,
  createTopMOverlapArtifact,
  createUserStudyBundleArtifact,
  defaultRankerConfig,
  decomposeArticle,
  deleteArticle,
  deleteCorpus,
  deleteExecution,
  getArticle,
  getCorpus,
  getExecution,
  listEvaluationArtifacts,
  listExecutions,
  listCorpora,
  runCompareExecution,
  runFullEvaluationSuite,
  runRankExecution,
  replayExecution,
  runSelectExecution,
  uploadArticles,
} from "./api/client";

const queryClient = new QueryClient();
type RunMode = Exclude<ExecutionKind, "evaluate">;
type AppPage = "home" | "corpora" | "new-corpus" | "articles" | "executions";
type ThemeMode = "light" | "dark";

type ParameterDraft = {
  mode: RunMode;
  config?: RankerConfigPayload;
  profile?: string;
  profiles?: string[];
  m?: number | null;
};

function App() {
  const [page, setPage] = useState<AppPage>("home");
  const [theme, setTheme] = useState<ThemeMode>("light");
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
    <main className="app-shell" data-theme={theme}>
      <TopNavigation
        currentPage={page}
        onNavigate={setPage}
        onToggleTheme={() =>
          setTheme((current) => (current === "light" ? "dark" : "light"))
        }
        theme={theme}
      />

      {page === "home" ? (
        <HomePage
          corpora={corpora.data ?? []}
          isLoading={corpora.isLoading}
          onCreateCorpus={() => setPage("new-corpus")}
          onOpenCorpus={(id) => {
            setSelectedCorpusId(id);
            setSelectedArticleId(null);
            setSelectedExecutionId(null);
            setPage("corpora");
          }}
          onOpenExecutions={() => setPage("executions")}
        />
      ) : null}

      {page === "new-corpus" ? (
        <NewCorpusPage
          onCreated={(id) => {
            setSelectedCorpusId(id);
            setSelectedArticleId(null);
            setSelectedExecutionId(null);
            setPage("articles");
          }}
        />
      ) : null}

      {page === "articles" ? (
        <ArticleManagementPage
          corpora={corpora.data ?? []}
          isLoadingCorpora={corpora.isLoading}
          selectedArticleId={selectedArticleId}
          selectedCorpusId={selectedCorpusId}
          onSelectArticle={setSelectedArticleId}
          onSelectCorpus={(id) => {
            setSelectedCorpusId(id);
            setSelectedArticleId(null);
            setSelectedExecutionId(null);
          }}
        />
      ) : null}

      {page === "executions" ? (
        <section className="workspace single-pane" aria-label="Executions workspace">
          <ExecutionsIndex
            corpora={corpora.data ?? []}
            onClose={() => setPage("corpora")}
            onOpenExecution={(execution) => {
              setSelectedCorpusId(execution.corpus_id);
              setSelectedArticleId(null);
              setSelectedExecutionId(execution.id);
              setPage("corpora");
            }}
          />
        </section>
      ) : null}

      {page === "corpora" ? (
        <section className="workspace" aria-label="Article set workspace">
          <aside className="sidebar">
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
          </aside>
          <div className="corpus-workspace">
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
          </div>
        </section>
      ) : null}
    </main>
  );
}

function TopNavigation({
  currentPage,
  onNavigate,
  onToggleTheme,
  theme,
}: {
  currentPage: AppPage;
  onNavigate: (page: AppPage) => void;
  onToggleTheme: () => void;
  theme: ThemeMode;
}) {
  return (
    <header className="topper">
      <div className="brand-block">
        <p className="eyebrow">Live Demo</p>
        <h1>News Ranker</h1>
      </div>
      <nav className="topper-nav" aria-label="Main sections">
        <button
          className={currentPage === "home" ? "nav-button selected" : "nav-button"}
          onClick={() => onNavigate("home")}
          type="button"
        >
          Home
        </button>
        <button
          className={
            currentPage === "corpora" ? "nav-button selected" : "nav-button"
          }
          onClick={() => onNavigate("corpora")}
          type="button"
        >
          Article Sets
        </button>
        <button
          className={
            currentPage === "new-corpus" ? "nav-button selected" : "nav-button"
          }
          onClick={() => onNavigate("new-corpus")}
          type="button"
        >
          Create Set
        </button>
        <button
          className={
            currentPage === "articles" ? "nav-button selected" : "nav-button"
          }
          onClick={() => onNavigate("articles")}
          type="button"
        >
          Articles
        </button>
        <button
          className={
            currentPage === "executions" ? "nav-button selected" : "nav-button"
          }
          onClick={() => onNavigate("executions")}
          type="button"
        >
          Executions
        </button>
        <button
          aria-pressed={theme === "dark"}
          className="theme-toggle"
          onClick={onToggleTheme}
          type="button"
        >
          {theme === "light" ? "Dark" : "Light"}
        </button>
      </nav>
    </header>
  );
}

function HomePage({
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

function NewCorpusPage({ onCreated }: { onCreated: (id: string) => void }) {
  return (
    <section className="single-page" aria-labelledby="new-corpus-title">
      <div className="page-heading">
        <p className="eyebrow">Create</p>
        <h2 id="new-corpus-title">Create Article Set</h2>
        <p className="muted">
          Start with an event name, then add article text files on the Articles
          page.
        </p>
      </div>
      <NewCorpusForm onCreated={onCreated} />
    </section>
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
        Create Article Set
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

function ArticleManagementPage({
  corpora,
  isLoadingCorpora,
  selectedCorpusId,
  selectedArticleId,
  onSelectCorpus,
  onSelectArticle,
}: {
  corpora: CorpusSummary[];
  isLoadingCorpora: boolean;
  selectedCorpusId: string | null;
  selectedArticleId: string | null;
  onSelectCorpus: (id: string) => void;
  onSelectArticle: (id: string | null) => void;
}) {
  const queryClient = useQueryClient();
  const corpus = useQuery({
    queryKey: ["corpus", selectedCorpusId],
    queryFn: () => getCorpus(selectedCorpusId ?? ""),
    enabled: selectedCorpusId !== null,
  });
  const uploadMutation = useMutation({
    mutationFn: (files: FileList) => uploadArticles(selectedCorpusId ?? "", files),
    onSuccess: async () => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ["corpora"] }),
        queryClient.invalidateQueries({ queryKey: ["corpus", selectedCorpusId] }),
      ]);
    },
  });
  const selectedCorpus = corpora.find((item) => item.id === selectedCorpusId);
  const articles = corpus.data?.articles ?? [];

  return (
    <section className="workspace" aria-label="Article management workspace">
      <aside className="sidebar">
        <CorpusList
          corpora={corpora}
          error={null}
          isLoading={isLoadingCorpora}
          onSelect={onSelectCorpus}
          selectedCorpusId={selectedCorpusId}
        />
      </aside>
      <section className="detail-panel" aria-labelledby="articles-title">
        <header className="detail-header">
          <div>
            <p className="eyebrow">Articles</p>
            <h2 id="articles-title">{selectedCorpus?.name ?? "Add Articles"}</h2>
            <p className="notes">
              Upload `.txt` files, then inspect each article body and structured
              decomposition.
            </p>
          </div>
        </header>
        {!selectedCorpusId ? (
          <EmptyWorkspace />
        ) : (
          <>
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
            {uploadMutation.isPending && <p className="muted">Uploading articles</p>}
            {corpus.isLoading && <p className="muted">Loading articles</p>}
            {corpus.error && <p className="error-line">{corpus.error.message}</p>}
            {corpus.data && (
              <div className="article-grid">
                <ArticleList
                  articles={articles}
                  onSelectArticle={onSelectArticle}
                  selectedArticleId={selectedArticleId}
                />
                <ArticleBody
                  articleId={selectedArticleId}
                  onDeleted={(corpusId) => {
                    onSelectArticle(null);
                    void queryClient.invalidateQueries({ queryKey: ["corpora"] });
                    void queryClient.invalidateQueries({
                      queryKey: ["corpus", corpusId],
                    });
                  }}
                />
              </div>
            )}
          </>
        )}
      </section>
    </section>
  );
}

type ExecutionFilters = {
  corpusId: string;
  kind: "" | ExecutionKind;
  status: "" | ExecutionStatus;
  profile: string;
  createdFrom: string;
  createdTo: string;
};

const emptyExecutionFilters: ExecutionFilters = {
  corpusId: "",
  kind: "",
  status: "",
  profile: "",
  createdFrom: "",
  createdTo: "",
};

function ExecutionsIndex({
  corpora,
  onClose,
  onOpenExecution,
}: {
  corpora: CorpusSummary[];
  onClose: () => void;
  onOpenExecution: (execution: ExecutionSummary) => void;
}) {
  const queryClient = useQueryClient();
  const [filters, setFilters] = useState<ExecutionFilters>(emptyExecutionFilters);
  const [offset, setOffset] = useState(0);
  const [compareTarget, setCompareTarget] = useState<ExecutionSummary | null>(null);
  const limit = 20;
  const executions = useQuery({
    queryKey: ["executions-index", filters, offset, limit],
    queryFn: () =>
      listExecutions({
        corpus_id: filters.corpusId || undefined,
        kind: filters.kind || undefined,
        status: filters.status || undefined,
        profile: filters.profile.trim() || undefined,
        created_from: dateStart(filters.createdFrom),
        created_to: dateEnd(filters.createdTo),
        limit,
        offset,
      }),
  });
  const deleteMutation = useMutation({
    mutationFn: deleteExecution,
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["executions-index"] });
      await queryClient.invalidateQueries({ queryKey: ["corpora"] });
    },
  });
  const replayMutation = useMutation({
    mutationFn: (executionId: string) => replayExecution(executionId),
    onSuccess: async ({ execution_id }, sourceId) => {
      const source = executions.data?.find((item) => item.id === sourceId);
      await queryClient.invalidateQueries({ queryKey: ["executions-index"] });
      if (source) {
        onOpenExecution({ ...source, id: execution_id, status: "pending" });
      }
    },
  });
  const rows = executions.data ?? [];
  const hasRows = rows.length > 0;

  function updateFilter<K extends keyof ExecutionFilters>(
    key: K,
    value: ExecutionFilters[K],
  ) {
    setFilters((current) => ({ ...current, [key]: value }));
    setOffset(0);
  }

  return (
    <section className="executions-index detail-panel" aria-labelledby="old-title">
      <header className="detail-header">
        <div>
          <p className="eyebrow">Old Executions</p>
          <h2 id="old-title">Execution History</h2>
        </div>
        <button onClick={onClose} type="button">
          Article Sets
        </button>
      </header>

      <div className="execution-filters">
        <label>
          Article Set
          <select
            onChange={(event) => updateFilter("corpusId", event.target.value)}
            value={filters.corpusId}
          >
            <option value="">All article sets</option>
            {corpora.map((corpus) => (
              <option key={corpus.id} value={corpus.id}>
                {corpus.name}
              </option>
            ))}
          </select>
        </label>
        <label>
          Kind
          <select
            onChange={(event) =>
              updateFilter("kind", event.target.value as ExecutionFilters["kind"])
            }
            value={filters.kind}
          >
            <option value="">All kinds</option>
            <option value="rank">rank</option>
            <option value="select">select</option>
            <option value="compare_profiles">compare_profiles</option>
          </select>
        </label>
        <label>
          Status
          <select
            onChange={(event) =>
              updateFilter(
                "status",
                event.target.value as ExecutionFilters["status"],
              )
            }
            value={filters.status}
          >
            <option value="">All statuses</option>
            <option value="pending">pending</option>
            <option value="running">running</option>
            <option value="succeeded">succeeded</option>
            <option value="failed">failed</option>
          </select>
        </label>
        <label>
          Profile
          <input
            onChange={(event) => updateFilter("profile", event.target.value)}
            placeholder="representative"
            value={filters.profile}
          />
        </label>
        <label>
          From
          <input
            onChange={(event) => updateFilter("createdFrom", event.target.value)}
            type="date"
            value={filters.createdFrom}
          />
        </label>
        <label>
          To
          <input
            onChange={(event) => updateFilter("createdTo", event.target.value)}
            type="date"
            value={filters.createdTo}
          />
        </label>
      </div>

      {executions.isLoading && <p className="muted">Loading executions</p>}
      {executions.error && <p className="error-line">{executions.error.message}</p>}
      {deleteMutation.error && (
        <p className="error-line">{deleteMutation.error.message}</p>
      )}
      {replayMutation.error && (
        <p className="error-line">{replayMutation.error.message}</p>
      )}
      {!executions.isLoading && !executions.error && !hasRows ? (
        <p className="muted">No executions match these filters.</p>
      ) : null}
      {hasRows ? (
        <div className="result-table-wrap">
          <table className="result-table executions-table">
            <thead>
              <tr>
                <th>Article Set</th>
                <th>Kind</th>
                <th>Profile</th>
                <th>Status</th>
                <th>Started</th>
                <th>Finished</th>
                <th>Eval</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((execution) => (
                <tr key={execution.id}>
                  <td>{execution.corpus_name || execution.corpus_id}</td>
                  <td>{formatGroupName(execution.kind)}</td>
                  <td>{execution.profile_summary}</td>
                  <td>
                    <span className={`status-pill ${execution.status}`}>
                      {execution.status}
                    </span>
                  </td>
                  <td>{formatDateTime(execution.started_at)}</td>
                  <td>{formatDateTime(execution.finished_at)}</td>
                  <td>{execution.has_evaluation_artifacts ? "yes" : "no"}</td>
                  <td>
                    <div className="row-actions">
                      <button onClick={() => onOpenExecution(execution)} type="button">
                        Open
                      </button>
                      <button
                        disabled={
                          execution.kind === "evaluate" || replayMutation.isPending
                        }
                        onClick={() => replayMutation.mutate(execution.id)}
                        type="button"
                      >
                        Replay
                      </button>
                      <button
                        className="danger"
                        disabled={deleteMutation.isPending}
                        onClick={() => deleteMutation.mutate(execution.id)}
                        type="button"
                      >
                        Delete
                      </button>
                      <button
                        disabled={!isComparableExecution(execution)}
                        onClick={() => setCompareTarget(execution)}
                        type="button"
                      >
                        Compare
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : null}

      {(hasRows || offset > 0) && (
        <div className="pagination-controls">
          <button
            disabled={offset === 0 || executions.isFetching}
            onClick={() => setOffset((current) => Math.max(0, current - limit))}
            type="button"
          >
            Previous
          </button>
          <span>{hasRows ? `${offset + 1}-${offset + rows.length}` : "0"}</span>
          <button
            disabled={rows.length < limit || executions.isFetching}
            onClick={() => setOffset((current) => current + limit)}
            type="button"
          >
            Next
          </button>
        </div>
      )}
      {compareTarget && (
        <CompareExecutionModal
          onClose={() => setCompareTarget(null)}
          target={compareTarget}
        />
      )}
    </section>
  );
}

function CompareExecutionModal({
  target,
  onClose,
}: {
  target: ExecutionSummary;
  onClose: () => void;
}) {
  const queryClient = useQueryClient();
  const [otherExecutionId, setOtherExecutionId] = useState("");
  const [topM, setTopM] = useState(target.m ?? 3);
  const [method, setMethod] = useState<"kendall" | "spearman">("kendall");
  const candidates = useQuery({
    queryKey: ["compare-execution-candidates"],
    queryFn: () => listExecutions({ status: "succeeded", limit: 100 }),
  });
  const options =
    candidates.data?.filter(
      (execution) =>
        execution.id !== target.id && isComparableExecution(execution),
    ) ?? [];
  const compareMutation = useMutation({
    mutationFn: async () => {
      const overlap = await createTopMOverlapArtifact(target.id, {
        other_execution_id: otherExecutionId,
        m: topM,
      });
      const correlation = await createRankCorrelationArtifact(target.id, {
        other_execution_id: otherExecutionId,
        method,
      });
      return [overlap, correlation];
    },
    onSuccess: async () => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ["executions-index"] }),
        queryClient.invalidateQueries({ queryKey: ["execution", target.id] }),
        queryClient.invalidateQueries({
          queryKey: ["evaluation-artifacts", target.id],
        }),
      ]);
      onClose();
    },
  });
  const selectedCandidate = options.find((item) => item.id === otherExecutionId);

  return (
    <div className="modal-backdrop" role="presentation">
      <section
        aria-labelledby="compare-title"
        aria-modal="true"
        className="compare-modal"
        role="dialog"
      >
        <header>
          <div>
            <p className="eyebrow">Compare With</p>
            <h3 id="compare-title">{target.profile_summary}</h3>
          </div>
          <button onClick={onClose} type="button">
            Close
          </button>
        </header>
        <div className="compare-summary">
          <Metric label="Target" value={formatGroupName(target.kind)} />
          <Metric
            label="Article Set"
            value={target.corpus_name || target.corpus_id}
          />
        </div>
        <div className="execution-filters">
          <label>
            Execution
            <select
              onChange={(event) => setOtherExecutionId(event.target.value)}
              value={otherExecutionId}
            >
              <option value="">Choose execution</option>
              {options.map((execution) => (
                <option key={execution.id} value={execution.id}>
                  {execution.corpus_name || execution.corpus_id} ·{" "}
                  {formatGroupName(execution.kind)} · {execution.profile_summary}
                </option>
              ))}
            </select>
          </label>
          <label>
            M
            <input
              min="1"
              onChange={(event) => setTopM(Number(event.target.value))}
              type="number"
              value={topM}
            />
          </label>
          <label>
            Correlation
            <select
              onChange={(event) =>
                setMethod(event.target.value as "kendall" | "spearman")
              }
              value={method}
            >
              <option value="kendall">kendall</option>
              <option value="spearman">spearman</option>
            </select>
          </label>
        </div>
        {candidates.isLoading && <p className="muted">Loading candidates</p>}
        {!candidates.isLoading && options.length === 0 && (
          <p className="muted">No compatible succeeded executions yet.</p>
        )}
        {selectedCandidate && (
          <p className="muted">
            Artifacts will be stored on {target.profile_summary} from{" "}
            {target.corpus_name || target.corpus_id}.
          </p>
        )}
        {candidates.error && <p className="error-line">{candidates.error.message}</p>}
        {compareMutation.error && (
          <p className="error-line">{compareMutation.error.message}</p>
        )}
        <div className="form-actions">
          <button
            disabled={!otherExecutionId || topM < 1 || compareMutation.isPending}
            onClick={() => compareMutation.mutate()}
            type="button"
          >
            {compareMutation.isPending ? "Comparing" : "Run Compare"}
          </button>
        </div>
      </section>
    </div>
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
  const [parameterDraft, setParameterDraft] = useState<ParameterDraft | null>(null);
  const corpus = useQuery({
    queryKey: ["corpus", corpusId],
    queryFn: () => getCorpus(corpusId),
  });
  const deleteMutation = useMutation({
    mutationFn: () => deleteCorpus(corpusId),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["corpora"] });
      onDeleted();
    },
  });

  const detail = corpus.data;
  const heading = detail?.name ?? fallbackCorpus?.name ?? "Article Set";

  return (
    <section className="detail-panel" aria-labelledby="corpus-title">
      <header className="detail-header">
        <div>
          <p className="eyebrow">Article Set</p>
          <h2 id="corpus-title">{heading}</h2>
          {detail?.notes && <p className="notes">{detail.notes}</p>}
        </div>
        <button
          className="danger"
          disabled={deleteMutation.isPending}
          onClick={() => {
            if (
              window.confirm(
                `Delete article set "${heading}" and all of its data?`,
              )
            ) {
              deleteMutation.mutate();
            }
          }}
          type="button"
        >
          Delete Article Set
        </button>
      </header>
      {deleteMutation.error && (
        <p className="error-line">{deleteMutation.error.message}</p>
      )}

      {corpus.isLoading && <p className="muted">Loading articles</p>}
      {corpus.error && <p className="error-line">{corpus.error.message}</p>}
      {detail && (
        <>
          <ExecutionControls
            articleCount={detail.articles.length}
            onCompare={() => {
              setParameterDraft({
                mode: "compare_profiles",
                profiles: ["representative", "comprehensive", "concise"],
              });
            }}
            onRank={() => {
              setParameterDraft({
                mode: "rank",
                profile: "representative",
              });
            }}
            onSelect={() => {
              setParameterDraft({
                mode: "select",
                m: Math.min(3, Math.max(1, detail.articles.length)),
                profile: "representative",
              });
            }}
          />
          {parameterDraft && (
            <ParameterForm
              articleCount={detail.articles.length}
              corpusId={corpusId}
              draft={parameterDraft}
              onCancel={() => setParameterDraft(null)}
              onSubmitted={(executionId) => {
                setParameterDraft(null);
                onSelectExecution(executionId);
              }}
            />
          )}
          <div className="article-grid">
            <ArticleList
              articles={detail.articles}
              selectedArticleId={selectedArticleId}
              onSelectArticle={onSelectArticle}
            />
            <ArticleBody articleId={selectedArticleId} />
          </div>
          <ExecutionPanel
            articles={detail.articles}
            executionId={selectedExecutionId}
            onReplay={(draft) => setParameterDraft(draft)}
          />
        </>
      )}
    </section>
  );
}

function ExecutionControls({
  articleCount,
  onRank,
  onSelect,
  onCompare,
}: {
  articleCount: number;
  onRank: () => void;
  onSelect: () => void;
  onCompare: () => void;
}) {
  return (
    <div className="execution-controls">
      <button disabled={articleCount === 0} onClick={onRank} type="button">
        Run Rank
      </button>
      <button
        disabled={articleCount === 0}
        onClick={onSelect}
        type="button"
      >
        Run Select
      </button>
      <button
        disabled={articleCount === 0}
        onClick={onCompare}
        type="button"
      >
        Compare Profiles
      </button>
    </div>
  );
}

function ParameterForm({
  articleCount,
  corpusId,
  draft,
  onCancel,
  onSubmitted,
}: {
  articleCount: number;
  corpusId: string;
  draft: ParameterDraft;
  onCancel: () => void;
  onSubmitted: (executionId: string) => void;
}) {
  const initialConfig = useMemo(() => normalizeConfigDraft(draft.config), [draft]);

  if (draft.mode === "rank") {
    return (
      <RankParameterForm
        corpusId={corpusId}
        draft={draft}
        initialConfig={initialConfig}
        onCancel={onCancel}
        onSubmitted={onSubmitted}
      />
    );
  }

  if (draft.mode === "select") {
    return (
      <SelectParameterForm
        articleCount={articleCount}
        corpusId={corpusId}
        draft={draft}
        initialConfig={initialConfig}
        onCancel={onCancel}
        onSubmitted={onSubmitted}
      />
    );
  }

  return (
    <CompareProfilesParameterForm
      articleCount={articleCount}
      corpusId={corpusId}
      draft={draft}
      initialConfig={initialConfig}
      onCancel={onCancel}
      onSubmitted={onSubmitted}
    />
  );
}

function RankParameterForm({
  corpusId,
  draft,
  initialConfig,
  onCancel,
  onSubmitted,
}: {
  corpusId: string;
  draft: ParameterDraft;
  initialConfig: RankerConfigPayload;
  onCancel: () => void;
  onSubmitted: (executionId: string) => void;
}) {
  const [config, setConfig] = useState<RankerConfigPayload>(initialConfig);
  const profileNames = Object.keys(config.profiles ?? {});
  const [profile, setProfile] = useState(draft.profile ?? profileNames[0]);
  const weightWarnings = profileWeightWarnings([profile], config);
  const canSubmit = Boolean(profile) && weightWarnings.length === 0;
  const mutation = useMutation({
    mutationFn: () =>
      runRankExecution({
        corpus_id: corpusId,
        profile,
        config,
      }),
    onSuccess: ({ execution_id }) => onSubmitted(execution_id),
  });

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (canSubmit) {
      mutation.mutate();
    }
  }

  function updateRankConfig<K extends keyof RankerConfigPayload>(
    key: K,
    value: RankerConfigPayload[K],
  ) {
    setConfig((current) => ({ ...current, [key]: value }));
  }

  return (
    <form className="parameter-form" onSubmit={handleSubmit}>
      <ParameterFormHeader
        mode="rank"
        onCancel={onCancel}
        subtitle="Locked execution"
      />

      <ProfileWeightsSection
        config={config}
        onSelectProfile={setProfile}
        onUpdateWeight={(profileName, component, value) =>
          updateProfileWeight(setConfig, profileName, component, value)
        }
        profileOptions={profileNames}
        profiles={[profile]}
        selectedProfile={profile}
      />

      <fieldset>
        <legend>Ranking Parameters</legend>
        <div className="parameter-grid">
          <label>
            Similarity
            <input
              max="1"
              min="-1"
              onChange={(event) =>
                updateRankConfig(
                  "similarity_threshold",
                  Number(event.target.value),
                )
              }
              step="0.01"
              type="number"
              value={config.similarity_threshold ?? 0.85}
            />
          </label>
          <label>
            Linkage
            <select
              onChange={(event) =>
                updateRankConfig(
                  "linkage",
                  event.target.value as "average" | "single",
                )
              }
              value={config.linkage ?? "average"}
            >
              <option value="average">average</option>
              <option value="single">single</option>
            </select>
          </label>
          <label>
            Coverage
            <select
              onChange={(event) =>
                updateRankConfig(
                  "coverage_weighting",
                  event.target.value as "consensus" | "rarity",
                )
              }
              value={config.coverage_weighting ?? "consensus"}
            >
              <option value="consensus">consensus</option>
              <option value="rarity">rarity</option>
            </select>
          </label>
        </div>
      </fieldset>

      <ParameterErrors errors={weightWarnings} mutationError={mutation.error} />
      <div className="form-actions">
        <button disabled={mutation.isPending || !canSubmit} type="submit">
          {mutation.isPending ? "Starting" : "Run Rank"}
        </button>
      </div>
    </form>
  );
}

function SelectParameterForm({
  articleCount,
  corpusId,
  draft,
  initialConfig,
  onCancel,
  onSubmitted,
}: {
  articleCount: number;
  corpusId: string;
  draft: ParameterDraft;
  initialConfig: RankerConfigPayload;
  onCancel: () => void;
  onSubmitted: (executionId: string) => void;
}) {
  const [config, setConfig] = useState<RankerConfigPayload>(initialConfig);
  const [selectionPreset, setSelectionPreset] = useState("custom");
  const profileNames = Object.keys(config.profiles ?? {});
  const [profile, setProfile] = useState(draft.profile ?? profileNames[0]);
  const [topM, setTopM] = useState(
    draft.m ?? config.top_m ?? Math.min(3, Math.max(1, articleCount)),
  );
  const weightWarnings = profileWeightWarnings([profile], config);
  const canSubmit =
    articleCount > 0 && Boolean(profile) && weightWarnings.length === 0 && topM >= 1;
  const mutation = useMutation({
    mutationFn: () =>
      runSelectExecution({
        corpus_id: corpusId,
        m: topM,
        profile,
        config: {
          ...config,
          top_m: topM,
        },
      }),
    onSuccess: ({ execution_id }) => onSubmitted(execution_id),
  });

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (canSubmit) {
      mutation.mutate();
    }
  }

  function loadSelectionPreset(value: string) {
    setSelectionPreset(value);
    if (value !== "defaults") {
      return;
    }
    const defaultTopM = defaultRankerConfig.top_m ?? 3;
    setTopM(Math.min(defaultTopM, Math.max(1, articleCount)));
    setConfig((current) => ({
      ...current,
      selection_lambda: defaultRankerConfig.selection_lambda,
      selection_mode: defaultRankerConfig.selection_mode,
      top_m: defaultTopM,
    }));
  }

  function updateSelectionConfig<K extends keyof RankerConfigPayload>(
    key: K,
    value: RankerConfigPayload[K],
  ) {
    setSelectionPreset("custom");
    setConfig((current) => ({ ...current, [key]: value }));
  }

  return (
    <form className="parameter-form" onSubmit={handleSubmit}>
      <ParameterFormHeader
        mode="select"
        onCancel={onCancel}
        subtitle="Locked execution"
      />

      <fieldset>
        <legend>Selection</legend>
        <div className="parameter-grid">
          <label>
            Defaults
            <select
              onChange={(event) => loadSelectionPreset(event.target.value)}
              value={selectionPreset}
            >
              <option value="custom">Custom values</option>
              <option value="defaults">Load default values</option>
            </select>
          </label>
          <label>
            Top M
            <input
              min="1"
              onChange={(event) => {
                setSelectionPreset("custom");
                setTopM(Number(event.target.value));
              }}
              step="1"
              type="number"
              value={topM}
            />
          </label>
          <label>
            Selection mode
            <select
              onChange={(event) =>
                updateSelectionConfig(
                  "selection_mode",
                  event.target.value as "top_score" | "mmr",
                )
              }
              value={config.selection_mode ?? "top_score"}
            >
              <option value="top_score">top_score</option>
              <option value="mmr">mmr</option>
            </select>
          </label>
          <label>
            Selection lambda
            <input
              max="1"
              min="0"
              onChange={(event) =>
                updateSelectionConfig(
                  "selection_lambda",
                  Number(event.target.value),
                )
              }
              step="0.05"
              type="number"
              value={config.selection_lambda ?? 0.8}
            />
          </label>
        </div>
      </fieldset>

      <ProfileWeightsSection
        config={config}
        onSelectProfile={setProfile}
        onUpdateWeight={(profileName, component, value) =>
          updateProfileWeight(setConfig, profileName, component, value)
        }
        profileOptions={profileNames}
        profiles={[profile]}
        selectedProfile={profile}
      />

      <ParameterErrors errors={weightWarnings} mutationError={mutation.error} />
      <div className="form-actions">
        <button disabled={mutation.isPending || !canSubmit} type="submit">
          {mutation.isPending ? "Starting" : "Run Select"}
        </button>
      </div>
    </form>
  );
}

function CompareProfilesParameterForm({
  articleCount,
  corpusId,
  draft,
  initialConfig,
  onCancel,
  onSubmitted,
}: {
  articleCount: number;
  corpusId: string;
  draft: ParameterDraft;
  initialConfig: RankerConfigPayload;
  onCancel: () => void;
  onSubmitted: (executionId: string) => void;
}) {
  const [config, setConfig] = useState<RankerConfigPayload>(initialConfig);
  const profileNames = Object.keys(config.profiles ?? {});
  const [profiles, setProfiles] = useState<string[]>(
    draft.profiles ?? profileNames.slice(0, 3),
  );
  const mutation = useMutation({
    mutationFn: () =>
      runCompareExecution({
        corpus_id: corpusId,
        profiles,
        config,
      }),
    onSuccess: ({ execution_id }) => onSubmitted(execution_id),
  });
  const weightWarnings = profileWeightWarnings(profiles, config);
  const canSubmit =
    articleCount > 0 && profiles.length > 0 && weightWarnings.length === 0;

  function toggleCompareProfile(profileName: string) {
    setProfiles((current) =>
      current.includes(profileName)
        ? current.filter((item) => item !== profileName)
        : [...current, profileName],
    );
  }

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (canSubmit) {
      mutation.mutate();
    }
  }

  return (
    <form className="parameter-form" onSubmit={handleSubmit}>
      <ParameterFormHeader
        mode="compare_profiles"
        onCancel={onCancel}
        subtitle="Locked execution"
      />

      <fieldset>
        <legend>Profiles</legend>
        <div className="checkbox-row">
          {profileNames.map((name) => {
            return (
              <label key={name}>
                <input
                  checked={profiles.includes(name)}
                  onChange={() => toggleCompareProfile(name)}
                  type="checkbox"
                />
                {name}
              </label>
            );
          })}
        </div>
      </fieldset>

      <ProfileWeightsSection
        config={config}
        onUpdateWeight={(profileName, component, value) =>
          updateProfileWeight(setConfig, profileName, component, value)
        }
        profileOptions={profileNames}
        profiles={profiles}
      />

      <ParameterErrors errors={weightWarnings} mutationError={mutation.error} />
      <div className="form-actions">
        <button disabled={mutation.isPending || !canSubmit} type="submit">
          {mutation.isPending ? "Starting" : "Compare Profiles"}
        </button>
      </div>
    </form>
  );
}

function ParameterFormHeader({
  mode,
  onCancel,
  subtitle,
}: {
  mode: RunMode;
  onCancel: () => void;
  subtitle: string;
}) {
  return (
    <header>
      <div>
        <p className="eyebrow">{subtitle}</p>
        <h3>{formatGroupName(mode)}</h3>
      </div>
      <button onClick={onCancel} type="button">
        Close
      </button>
    </header>
  );
}

const profileWeightComponents = [
  "centrality",
  "coverage",
  "density",
  "entity_coverage",
] as const satisfies readonly (keyof ProfileWeights)[];

function ProfileWeightsSection({
  config,
  onSelectProfile,
  onUpdateWeight,
  profileOptions,
  profiles,
  selectedProfile,
}: {
  config: RankerConfigPayload;
  onSelectProfile?: (profile: string) => void;
  onUpdateWeight: (
    profileName: string,
    component: keyof ProfileWeights,
    value: number,
  ) => void;
  profileOptions: string[];
  profiles: string[];
  selectedProfile?: string;
}) {
  return (
    <fieldset>
      <legend>Profile Weights</legend>
      {selectedProfile && onSelectProfile ? (
        <label>
          Profile
          <select
            onChange={(event) => onSelectProfile(event.target.value)}
            value={selectedProfile}
          >
            {profileOptions.map((name) => (
              <option key={name} value={name}>
                {name}
              </option>
            ))}
          </select>
        </label>
      ) : null}
      <div className="weights-grid">
        {profiles.map((name) => {
          const weights = config.profiles?.[name];
          if (!weights) {
            return null;
          }
          return (
            <div className="weight-group" key={name}>
              <strong>{name}</strong>
              {profileWeightComponents.map((component) => (
                <label key={component}>
                  {formatGroupName(component)}
                  <input
                    min="0"
                    onChange={(event) =>
                      onUpdateWeight(name, component, Number(event.target.value))
                    }
                    step="0.05"
                    type="number"
                    value={weights[component]}
                  />
                </label>
              ))}
            </div>
          );
        })}
      </div>
    </fieldset>
  );
}

function ParameterErrors({
  errors,
  mutationError,
}: {
  errors: string[];
  mutationError: Error | null;
}) {
  return (
    <>
      {errors.map((warning) => (
        <p className="error-line" key={warning}>
          {warning}
        </p>
      ))}
      {mutationError && <p className="error-line">{mutationError.message}</p>}
    </>
  );
}

function profileWeightWarnings(
  profiles: string[],
  config: RankerConfigPayload,
): string[] {
  return profiles
    .map((name) => {
      const weights = config.profiles?.[name];
      if (!weights) {
        return `${name} weights are missing`;
      }
      const total =
        weights.centrality +
        weights.coverage +
        weights.density +
        weights.entity_coverage;
      return Math.abs(total - 1) > 0.000001
        ? `${name} weights total ${total.toFixed(3)}`
        : null;
    })
    .filter((item): item is string => item !== null);
}

function updateProfileWeight(
  setConfig: React.Dispatch<React.SetStateAction<RankerConfigPayload>>,
  profileName: string,
  component: keyof ProfileWeights,
  value: number,
) {
  setConfig((current) => ({
    ...current,
    profiles: {
      ...(current.profiles ?? {}),
      [profileName]: {
        ...(current.profiles?.[profileName] ?? {
          centrality: 0,
          coverage: 0,
          density: 0,
          entity_coverage: 0,
        }),
        [component]: value,
      },
    },
  }));
}

function ExecutionPanel({
  articles,
  executionId,
  onReplay,
}: {
  articles: ArticleSummary[];
  executionId: string | null;
  onReplay: (draft: ParameterDraft) => void;
}) {
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
  const artifacts = useQuery({
    queryKey: ["evaluation-artifacts", executionId],
    queryFn: () => listEvaluationArtifacts(executionId ?? ""),
    enabled: executionId !== null && execution.data?.status === "succeeded",
    initialData: execution.data?.evaluation_artifacts,
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
        <div className="execution-header-actions">
          <button
            disabled={execution.data.kind === "evaluate"}
            onClick={() => onReplay(draftFromExecution(execution.data))}
            type="button"
          >
            Replay
          </button>
          <span className={`status-pill ${execution.data.status}`}>
            {execution.data.status}
          </span>
        </div>
      </header>
      {execution.data.error && <p className="error-line">{execution.data.error}</p>}
      {execution.data.status !== "succeeded" && (
        <p className="muted">Execution is {execution.data.status}.</p>
      )}
      <details>
        <summary>Parameters</summary>
        <pre>{JSON.stringify(execution.data.config_json, null, 2)}</pre>
      </details>
      {execution.data.results.length === 0 ? (
        <p className="muted">No persisted result rows yet.</p>
      ) : (
        execution.data.results.map((result) => (
          <ResultPayloadTable
            key={result.id}
            articles={articles}
            payload={result.result_json}
            selectedArticleIds={selectedArticleIds(result.result_json)}
          />
        ))
      )}
      {execution.data.status === "succeeded" && (
        <EvaluationPanel
          artifacts={artifacts.data ?? execution.data.evaluation_artifacts}
          articles={articles}
          execution={execution.data}
        />
      )}
    </section>
  );
}

function EvaluationPanel({
  artifacts,
  articles,
  execution,
}: {
  artifacts: EvaluationArtifact[];
  articles: ArticleSummary[];
  execution: ExecutionDetail;
}) {
  const queryClient = useQueryClient();
  const [baselineId, setBaselineId] = useState("");
  const [topM, setTopM] = useState(
    Math.min(execution.m ?? 3, Math.max(1, articles.length)),
  );
  const [method, setMethod] = useState<"kendall" | "spearman">("kendall");
  const [rareThreshold, setRareThreshold] = useState(1);
  const [includeScores, setIncludeScores] = useState(false);
  const baselines = useQuery({
    queryKey: ["baseline-executions", execution.corpus_id],
    queryFn: () =>
      listExecutions({
        corpus_id: execution.corpus_id,
        status: "succeeded",
        limit: 100,
      }),
  });
  const baselineOptions =
    baselines.data?.filter((item) => item.id !== execution.id) ?? [];
  const materials = useMemo(() => articleMaterials(articles), [articles]);
  const invalidateArtifacts = async () => {
    await Promise.all([
      queryClient.invalidateQueries({
        queryKey: ["evaluation-artifacts", execution.id],
      }),
      queryClient.invalidateQueries({ queryKey: ["execution", execution.id] }),
    ]);
  };
  const topOverlap = useMutation({
    mutationFn: () =>
      createTopMOverlapArtifact(execution.id, {
        other_execution_id: baselineId,
        m: topM,
      }),
    onSuccess: invalidateArtifacts,
  });
  const correlation = useMutation({
    mutationFn: () =>
      createRankCorrelationArtifact(execution.id, {
        other_execution_id: baselineId,
        method,
      }),
    onSuccess: invalidateArtifacts,
  });
  const componentTable = useMutation({
    mutationFn: () => createComponentTableArtifact(execution.id),
    onSuccess: invalidateArtifacts,
  });
  const clusterInspection = useMutation({
    mutationFn: () =>
      createClusterInspectionArtifact(execution.id, {
        rare_threshold: rareThreshold,
      }),
    onSuccess: invalidateArtifacts,
  });
  const userStudy = useMutation({
    mutationFn: () =>
      createUserStudyBundleArtifact(execution.id, {
        materials,
        include_scores: includeScores,
      }),
    onSuccess: invalidateArtifacts,
  });
  const fullSuite = useMutation({
    mutationFn: () =>
      runFullEvaluationSuite(execution.id, {
        baseline_execution_id: baselineId,
        m: topM,
        method,
        rare_threshold: rareThreshold,
        materials: execution.kind === "select" ? materials : {},
        include_scores: includeScores,
      }),
    onSuccess: invalidateArtifacts,
  });
  const needsBaseline = !baselineId;

  return (
    <section className="evaluation-panel" aria-labelledby="evaluation-title">
      <header>
        <div>
          <p className="eyebrow">Evaluation</p>
          <h3 id="evaluation-title">Artifacts</h3>
        </div>
        <span>{artifacts.length}</span>
      </header>
      <div className="evaluation-controls">
        <label>
          Baseline
          <select
            onChange={(event) => setBaselineId(event.target.value)}
            value={baselineId}
          >
            <option value="">Choose baseline</option>
            {baselineOptions.map((item) => (
              <option key={item.id} value={item.id}>
                {formatGroupName(item.kind)} · {item.profiles.join(", ")}
              </option>
            ))}
          </select>
        </label>
        <label>
          M
          <input
            min="1"
            onChange={(event) => setTopM(Number(event.target.value))}
            type="number"
            value={topM}
          />
        </label>
        <label>
          Correlation
          <select
            onChange={(event) =>
              setMethod(event.target.value as "kendall" | "spearman")
            }
            value={method}
          >
            <option value="kendall">kendall</option>
            <option value="spearman">spearman</option>
          </select>
        </label>
        <label>
          Rare threshold
          <input
            min="1"
            onChange={(event) => setRareThreshold(Number(event.target.value))}
            type="number"
            value={rareThreshold}
          />
        </label>
        <label className="inline-check">
          <input
            checked={includeScores}
            onChange={(event) => setIncludeScores(event.target.checked)}
            type="checkbox"
          />
          Include scores
        </label>
      </div>
      {baselines.error && <p className="error-line">{baselines.error.message}</p>}
      {baselines.isLoading && <p className="muted">Loading baselines</p>}
      {!baselines.isLoading && baselineOptions.length === 0 && (
        <p className="muted">Run another succeeded execution to compare against.</p>
      )}
      <div className="evaluation-actions">
        <button
          disabled={needsBaseline || topOverlap.isPending}
          onClick={() => topOverlap.mutate()}
          type="button"
        >
          Top-M Overlap
        </button>
        <button
          disabled={needsBaseline || correlation.isPending}
          onClick={() => correlation.mutate()}
          type="button"
        >
          Rank Correlation
        </button>
        <button
          disabled={componentTable.isPending}
          onClick={() => componentTable.mutate()}
          type="button"
        >
          Component Table
        </button>
        <button
          disabled={clusterInspection.isPending}
          onClick={() => clusterInspection.mutate()}
          type="button"
        >
          Cluster Inspection
        </button>
        <button
          disabled={execution.kind !== "select" || userStudy.isPending}
          onClick={() => userStudy.mutate()}
          type="button"
        >
          User-Study Bundle
        </button>
        <button
          disabled={needsBaseline || fullSuite.isPending}
          onClick={() => fullSuite.mutate()}
          type="button"
        >
          Run Full Test Suite
        </button>
      </div>
      {[
        topOverlap.error,
        correlation.error,
        componentTable.error,
        clusterInspection.error,
        userStudy.error,
        fullSuite.error,
      ].map((error) =>
        error ? (
          <p className="error-line" key={error.message}>
            {error.message}
          </p>
        ) : null,
      )}
      {artifacts.length === 0 ? (
        <p className="muted">No evaluation artifacts yet.</p>
      ) : (
        <div className="artifact-list">
          {artifacts.map((artifact) => (
            <ArtifactCard artifact={artifact} key={artifact.id} />
          ))}
        </div>
      )}
    </section>
  );
}

function ArtifactCard({ artifact }: { artifact: EvaluationArtifact }) {
  const payload = artifact.payload_json;
  return (
    <article className="artifact-card">
      <header>
        <div>
          <h4>{formatGroupName(artifact.helper)}</h4>
          <small>{new Date(artifact.created_at).toLocaleString()}</small>
        </div>
        {artifact.helper === "anonymized_user_study_bundle" && (
          <a
            download={`user-study-${artifact.id}.json`}
            href={`data:application/json;charset=utf-8,${encodeURIComponent(
              JSON.stringify(payload, null, 2),
            )}`}
          >
            JSON
          </a>
        )}
      </header>
      <ArtifactPayload artifact={artifact} />
    </article>
  );
}

function ArtifactPayload({ artifact }: { artifact: EvaluationArtifact }) {
  const payload = artifact.payload_json;
  if (artifact.helper === "top_m_overlap") {
    return (
      <div className="metric-grid">
        <Metric label="Overlap" value={payload.overlap_count} />
        <Metric label="Jaccard" value={formatUnknownScore(payload.jaccard)} />
        <Metric label="Left top" value={payload.left_top_count} />
        <Metric label="Right top" value={payload.right_top_count} />
        <p>{formatIdList(payload.overlap_article_ids)}</p>
      </div>
    );
  }
  if (artifact.helper === "rank_correlation") {
    return (
      <div className="metric-grid">
        <Metric label="Method" value={payload.method} />
        <Metric
          label="Coefficient"
          value={formatUnknownScore(payload.coefficient)}
        />
        <Metric label="Common" value={payload.common_count} />
        <p>Left-only: {formatIdList(payload.left_only_article_ids)}</p>
        <p>Right-only: {formatIdList(payload.right_only_article_ids)}</p>
      </div>
    );
  }
  if (artifact.helper === "component_score_table") {
    return <ArtifactRows rows={arrayPayload(payload.rows)} />;
  }
  if (artifact.helper === "cluster_inspection_rows") {
    return (
      <div className="cluster-artifacts">
        {arrayPayload(payload.rows).map((row, index) => (
          <details key={`${row.cluster_index}-${index}`}>
            <summary>
              {String(row.canonical_fact_text ?? "Cluster")} · support{" "}
              {String(row.support_count ?? "0")}{" "}
              {row.is_rare ? <span className="selected-badge">Rare</span> : null}
            </summary>
            <p>Articles: {formatIdList(row.support_article_ids)}</p>
            <p>Facts: {formatIdList(row.member_fact_ids)}</p>
            <p>{formatIdList(row.member_texts)}</p>
          </details>
        ))}
      </div>
    );
  }
  if (artifact.helper === "anonymized_user_study_bundle") {
    return (
      <div className="metric-grid">
        <Metric label="Profile" value={payload.profile} />
        <Metric label="M" value={payload.m} />
        <p>Labels: {formatIdList(payload.selected_article_labels)}</p>
        <pre>{JSON.stringify(payload.article_materials, null, 2)}</pre>
      </div>
    );
  }
  return <pre>{JSON.stringify(payload, null, 2)}</pre>;
}

function ArtifactRows({ rows }: { rows: Record<string, unknown>[] }) {
  const columns = rows.slice(0, 1).flatMap((row) => Object.keys(row));
  if (rows.length === 0) {
    return <p className="muted">No rows.</p>;
  }
  return (
    <div className="result-table-wrap">
      <table className="result-table compact">
        <thead>
          <tr>
            {columns.map((column) => (
              <th key={column}>{formatGroupName(column)}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, index) => (
            <tr key={index}>
              {columns.map((column) => (
                <td key={column}>{formatCell(row[column])}</td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function Metric({ label, value }: { label: string; value: unknown }) {
  return (
    <div className="metric">
      <span>{label}</span>
      <strong>{String(value ?? "n/a")}</strong>
    </div>
  );
}

function ResultPayloadTable({
  articles,
  payload,
  selectedArticleIds,
}: {
  articles: ArticleSummary[];
  payload: ExecutionResultJson;
  selectedArticleIds: Set<string>;
}) {
  const articleLookup = useMemo(() => {
    return new Map(articles.map((article) => [article.id, article]));
  }, [articles]);

  if (payload.__type__ === "profile_comparison") {
    return (
      <div className="comparison-grid">
        {Object.entries(payload.rankings).map(([profile, ranking]) => (
          <RankingTable
            articleLookup={articleLookup}
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
        articleLookup={articleLookup}
        entries={payload.ranking.entries}
        profile={`${payload.profile} · selected ${payload.m}`}
        selectedArticleIds={selectedArticleIds}
      />
    );
  }

  return (
    <RankingTable
      articleLookup={articleLookup}
      entries={payload.entries}
      profile={payload.profile}
      selectedArticleIds={selectedArticleIds}
    />
  );
}

function RankingTable({
  articleLookup,
  profile,
  entries,
  selectedArticleIds,
}: {
  articleLookup: Map<string, ArticleSummary>;
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
                <div className="article-cell">
                  <strong>
                    {articleLookup.get(entry.article_id)?.title ?? "Untitled article"}
                  </strong>
                  <span>{entry.article_id}</span>
                </div>
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

function articleMaterials(
  articles: ArticleSummary[],
): Record<string, { title: string; snippet: string }> {
  return Object.fromEntries(
    articles.map((article) => [
      article.id,
      {
        title: article.title,
        snippet: article.filename,
      },
    ]),
  );
}

function arrayPayload(value: unknown): Record<string, unknown>[] {
  return Array.isArray(value)
    ? value.filter((item): item is Record<string, unknown> => isRecord(item))
    : [];
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function formatCell(value: unknown): string {
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

function formatIdList(value: unknown): string {
  if (Array.isArray(value)) {
    return value.length ? value.map(String).join(", ") : "none";
  }
  return typeof value === "string" ? value : "none";
}

function formatUnknownScore(value: unknown): string {
  return typeof value === "number" ? formatScore(value) : String(value ?? "n/a");
}

function normalizeConfigDraft(config?: RankerConfigPayload): RankerConfigPayload {
  const source = config as (RankerConfigPayload & { m?: number | null }) | undefined;
  const normalized = {
    ...defaultRankerConfig,
    similarity_threshold:
      source?.similarity_threshold ?? defaultRankerConfig.similarity_threshold,
    linkage: source?.linkage ?? defaultRankerConfig.linkage,
    coverage_weighting:
      source?.coverage_weighting ?? defaultRankerConfig.coverage_weighting,
    profiles: {
      ...defaultRankerConfig.profiles,
      ...(source?.profiles ?? {}),
    },
    top_m: source?.top_m ?? defaultRankerConfig.top_m,
    selection_mode: source?.selection_mode ?? defaultRankerConfig.selection_mode,
    selection_lambda:
      source?.selection_lambda ?? defaultRankerConfig.selection_lambda,
    embedding_model_name:
      source?.embedding_model_name ?? defaultRankerConfig.embedding_model_name,
    llm_model_name: source?.llm_model_name ?? defaultRankerConfig.llm_model_name,
    prompt_version: source?.prompt_version ?? defaultRankerConfig.prompt_version,
    schema_version: source?.schema_version ?? defaultRankerConfig.schema_version,
    cache_dir: source?.cache_dir ?? defaultRankerConfig.cache_dir,
  };
  return JSON.parse(JSON.stringify(normalized)) as RankerConfigPayload;
}

function draftFromExecution(execution: ExecutionDetail): ParameterDraft {
  const config = normalizeConfigDraft(
    execution.config_json as RankerConfigPayload & { m?: number | null },
  );
  const storedM =
    typeof execution.config_json.m === "number"
      ? execution.config_json.m
      : execution.m;
  return {
    mode: execution.kind === "evaluate" ? "rank" : execution.kind,
    config,
    profile: execution.profiles[0] ?? "representative",
    profiles: execution.profiles.length
      ? execution.profiles
      : ["representative", "comprehensive", "concise"],
    m: storedM ?? config.top_m ?? 3,
  };
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

function ArticleBody({
  articleId,
  onDeleted,
}: {
  articleId: string | null;
  onDeleted?: (corpusId: string) => void;
}) {
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
  const deleteMutation = useMutation({
    mutationFn: () => deleteArticle(articleId ?? ""),
    onSuccess: async () => {
      const corpusId = article.data?.corpus_id;
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ["corpora"] }),
        queryClient.invalidateQueries({ queryKey: ["corpus", corpusId] }),
        queryClient.invalidateQueries({ queryKey: ["article", articleId] }),
      ]);
      if (corpusId) {
        onDeleted?.(corpusId);
      }
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
          <div className="row-actions">
            <button
              disabled={decomposeMutation.isPending || deleteMutation.isPending}
              onClick={() => decomposeMutation.mutate()}
              type="button"
            >
              {decomposeMutation.isPending ? "Running" : "Decompose"}
            </button>
            {onDeleted && (
              <button
                className="danger"
                disabled={deleteMutation.isPending}
                onClick={() => {
                  if (window.confirm(`Delete article "${article.data.title}"?`)) {
                    deleteMutation.mutate();
                  }
                }}
                type="button"
              >
                Delete Article
              </button>
            )}
          </div>
        </header>
        {decomposeMutation.error && (
          <p className="error-line">{decomposeMutation.error.message}</p>
        )}
        {deleteMutation.error && (
          <p className="error-line">{deleteMutation.error.message}</p>
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
  return group.replaceAll("_", " ");
}

function formatDateTime(value: string | null) {
  return value ? new Date(value).toLocaleString() : "n/a";
}

function isComparableExecution(execution: ExecutionSummary) {
  return (
    execution.status === "succeeded" &&
    (execution.kind === "rank" || execution.kind === "select")
  );
}

function dateStart(value: string) {
  return value ? `${value}T00:00:00` : undefined;
}

function dateEnd(value: string) {
  return value ? `${value}T23:59:59` : undefined;
}

function EmptyWorkspace() {
  return (
    <section
      className="detail-panel empty-state"
      aria-label="No article set selected"
    >
      <h2>Choose an Article Set</h2>
      <p className="muted">
        Create or select an article set to manage text articles.
      </p>
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
