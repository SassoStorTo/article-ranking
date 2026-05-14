import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useCallback, useEffect, useMemo, useState } from "react";

import {
  ArticleSummary,
  CorpusSummary,
  ExecutionDetail,
  deleteCorpus,
  getArticle,
  getCorpus,
  getExecution,
  listEvaluationArtifacts,
  listCorpora,
} from "../api/client";
import {
  AppRoute,
  pathForRoute,
  routeEquals,
  routeForPage,
  routeForPathname,
} from "./navigation";
import { formatGroupName } from "../utils/format";
import { EvaluationPanel } from "../artifacts/EvaluationPanel";
import { ResultPayloadTable } from "../artifacts/ResultPayloadTable";
import { ArticleBody } from "../components/ArticleBody";
import { ArticleList } from "../components/ArticleList";
import { CorpusList } from "../components/CorpusList";
import { EmptyWorkspace } from "../components/EmptyWorkspace";
import { ThemeMode, TopNavigation } from "../components/TopNavigation";
import { ParameterForm } from "../forms/ParameterForm";
import { draftFromExecution, ParameterDraft } from "../forms/configDraft";
import { ArticleManagementPage } from "../pages/ArticleManagementPage";
import { ExecutionsIndex } from "../pages/ExecutionsIndex";
import { HomePage } from "../pages/HomePage";
import { NewCorpusPage } from "../pages/NewCorpusPage";

export default function App() {
  const [route, setRoute] = useState<AppRoute>(() =>
    routeForPathname(window.location.pathname),
  );
  const page = route.page;
  const [theme, setTheme] = useState<ThemeMode>("light");
  const [selectedCorpusId, setSelectedCorpusId] = useState<string | null>(null);
  const [selectedArticleId, setSelectedArticleId] = useState<string | null>(null);
  const [selectedExecutionId, setSelectedExecutionId] = useState<string | null>(
    null,
  );
  const corpora = useQuery({ queryKey: ["corpora"], queryFn: listCorpora });
  const navigate = useCallback(
    (
      nextRoute: AppRoute,
      options?: { clearSelection?: boolean; replace?: boolean },
    ) => {
      const nextPath = pathForRoute(nextRoute);
      const currentPath = pathForRoute(routeForPathname(window.location.pathname));
      if (nextPath !== currentPath) {
        if (options?.replace) {
          window.history.replaceState(null, "", nextPath);
        } else {
          window.history.pushState(null, "", nextPath);
        }
      }
      if (options?.clearSelection) {
        setSelectedCorpusId(null);
        setSelectedArticleId(null);
        setSelectedExecutionId(null);
      }
      setRoute((currentRoute) =>
        routeEquals(currentRoute, nextRoute) ? currentRoute : nextRoute,
      );
    },
    [],
  );

  useEffect(() => {
    const currentPath = window.location.pathname;
    const currentRoute = routeForPathname(currentPath);
    const normalizedPath = pathForRoute(currentRoute);
    if (normalizedPath !== currentPath) {
      window.history.replaceState(null, "", normalizedPath);
    }

    function handlePopState() {
      const nextRoute = routeForPathname(window.location.pathname);
      setRoute((currentRoute) =>
        routeEquals(currentRoute, nextRoute) ? currentRoute : nextRoute,
      );
    }

    window.addEventListener("popstate", handlePopState);
    return () => window.removeEventListener("popstate", handlePopState);
  }, []);

  useEffect(() => {
    let isCurrent = true;

    if (route.page === "corpora") {
      setSelectedCorpusId(route.corpusId ?? null);
      setSelectedArticleId(null);
      setSelectedExecutionId(null);
      return () => {
        isCurrent = false;
      };
    }

    if (route.page === "articles") {
      setSelectedArticleId(route.articleId ?? null);
      setSelectedExecutionId(null);
      setSelectedCorpusId(null);
      if (!route.articleId) {
        setSelectedCorpusId(null);
        return () => {
          isCurrent = false;
        };
      }

      void getArticle(route.articleId)
        .then((article) => {
          if (isCurrent) {
            setSelectedCorpusId(article.corpus_id);
          }
        })
        .catch(() => {
          if (isCurrent) {
            navigate({ page: "articles" }, { replace: true });
          }
        });
      return () => {
        isCurrent = false;
      };
    }

    if (route.page === "executions") {
      setSelectedArticleId(null);
      setSelectedExecutionId(route.executionId ?? null);
      setSelectedCorpusId(null);
      if (!route.executionId) {
        setSelectedCorpusId(null);
        return () => {
          isCurrent = false;
        };
      }

      void getExecution(route.executionId)
        .then((execution) => {
          if (isCurrent) {
            setSelectedCorpusId(execution.corpus_id);
          }
        })
        .catch(() => {
          if (isCurrent) {
            navigate({ page: "executions" }, { replace: true });
          }
        });
      return () => {
        isCurrent = false;
      };
    }

    setSelectedCorpusId(null);
    setSelectedArticleId(null);
    setSelectedExecutionId(null);
    return () => {
      isCurrent = false;
    };
  }, [navigate, route]);

  const selectedCorpus = useMemo(() => {
    return corpora.data?.find((corpus) => corpus.id === selectedCorpusId) ?? null;
  }, [corpora.data, selectedCorpusId]);

  return (
    <main className="app-shell" data-theme={theme}>
      <TopNavigation
        currentPage={page}
        onNavigate={(nextPage) =>
          navigate(routeForPage(nextPage), { clearSelection: true })
        }
        onToggleTheme={() =>
          setTheme((current) => (current === "light" ? "dark" : "light"))
        }
        theme={theme}
      />

      {page === "home" ? (
        <HomePage
          corpora={corpora.data ?? []}
          isLoading={corpora.isLoading}
          onCreateCorpus={() => navigate({ page: "new-corpus" })}
          onOpenCorpus={(id) => navigate({ corpusId: id, page: "corpora" })}
          onOpenExecutions={() => navigate({ page: "executions" })}
        />
      ) : null}

      {page === "new-corpus" ? (
        <NewCorpusPage
          onCreated={(id) => navigate({ corpusId: id, page: "corpora" })}
        />
      ) : null}

      {page === "articles" ? (
        <ArticleManagementPage
          corpora={corpora.data ?? []}
          isLoadingCorpora={corpora.isLoading}
          selectedArticleId={selectedArticleId}
          selectedCorpusId={selectedCorpusId}
          onSelectArticle={(id) =>
            navigate(
              id ? { articleId: id, page: "articles" } : { page: "articles" },
            )
          }
          onSelectCorpus={(id) => {
            setSelectedCorpusId(id);
            setSelectedArticleId(null);
            setSelectedExecutionId(null);
          }}
        />
      ) : null}

      {page === "executions" && !route.executionId ? (
        <section className="workspace single-pane" aria-label="Executions workspace">
          <ExecutionsIndex
            corpora={corpora.data ?? []}
            onClose={() => navigate({ page: "corpora" })}
            onOpenExecution={(execution) =>
              navigate({ executionId: execution.id, page: "executions" })
            }
          />
        </section>
      ) : null}

      {page === "corpora" || (page === "executions" && route.executionId) ? (
        <section className="workspace" aria-label="Article set workspace">
          <aside className="sidebar">
            <CorpusList
              corpora={corpora.data ?? []}
              isLoading={corpora.isLoading}
              error={corpora.error}
              selectedCorpusId={selectedCorpusId}
              onSelect={(id) => navigate({ corpusId: id, page: "corpora" })}
            />
          </aside>
          <div className="corpus-workspace">
            {selectedCorpusId ? (
              <CorpusPanel
                corpusId={selectedCorpusId}
                fallbackCorpus={selectedCorpus}
                selectedArticleId={selectedArticleId}
                onSelectArticle={(id) =>
                  navigate(
                    id ? { articleId: id, page: "articles" } : { page: "corpora" },
                  )
                }
                selectedExecutionId={selectedExecutionId}
                onSelectExecution={(id) =>
                  navigate(
                    id ? { executionId: id, page: "executions" } : { page: "corpora" },
                  )
                }
                onDeleted={() => navigate({ page: "corpora" }, { replace: true })}
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
