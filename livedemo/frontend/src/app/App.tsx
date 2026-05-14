import { useQuery } from "@tanstack/react-query";
import { useCallback, useEffect, useMemo, useState } from "react";

import { getArticle, getExecution, listCorpora } from "../api/client";
import {
  AppRoute,
  pathForRoute,
  routeEquals,
  routeForPage,
  routeForPathname,
} from "./navigation";
import { CorpusPanel } from "../pages/CorpusPanel";
import { CorpusList } from "../components/CorpusList";
import { EmptyWorkspace } from "../components/EmptyWorkspace";
import { ThemeMode, TopNavigation } from "../components/TopNavigation";
import { ExecutionComparisonPage } from "../pages/ExecutionComparisonPage";
import { ExecutionsIndex } from "../pages/ExecutionsIndex";
import { HomePage } from "../pages/HomePage";
import { NewCorpusPage } from "../pages/NewCorpusPage";

export default function App() {
  const [route, setRoute] = useState<AppRoute>(() =>
    routeForPathname(window.location.pathname),
  );
  const page = route.page;
  const currentTopNavPage = page === "execution-comparison" ? "executions" : page;
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

      if (!route.corpusId || !route.articleId) {
        return () => {
          isCurrent = false;
        };
      }

      void getArticle(route.articleId)
        .then((article) => {
          if (!isCurrent) {
            return;
          }
          if (article.corpus_id === route.corpusId) {
            setSelectedArticleId(route.articleId ?? null);
            return;
          }
          navigate(
            {
              articleId: route.articleId,
              corpusId: article.corpus_id,
              page: "corpora",
            },
            { replace: true },
          );
        })
        .catch(() => {
          if (isCurrent) {
            navigate(
              { corpusId: route.corpusId, page: "corpora" },
              { replace: true },
            );
          }
        });
      return () => {
        isCurrent = false;
      };
    }

    if (route.page === "articles") {
      setSelectedArticleId(route.articleId ?? null);
      setSelectedExecutionId(null);
      if (!route.articleId) {
        navigate({ page: "corpora" }, { clearSelection: true, replace: true });
        return () => {
          isCurrent = false;
        };
      }

      setSelectedCorpusId(null);
      void getArticle(route.articleId)
        .then((article) => {
          if (isCurrent) {
            navigate(
              {
                articleId: route.articleId,
                corpusId: article.corpus_id,
                page: "corpora",
              },
              { replace: true },
            );
          }
        })
        .catch(() => {
          if (isCurrent) {
            navigate({ page: "corpora" }, { clearSelection: true, replace: true });
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
        currentPage={currentTopNavPage === "articles" ? "corpora" : currentTopNavPage}
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

      {page === "execution-comparison" ? (
        <section className="workspace single-pane" aria-label="Comparison workspace">
          <ExecutionComparisonPage
            leftExecutionId={route.leftExecutionId}
            onBack={() => navigate({ page: "executions" })}
            onSelectExecutions={(leftExecutionId, rightExecutionId) =>
              navigate({ leftExecutionId, page: "execution-comparison", rightExecutionId })
            }
            rightExecutionId={route.rightExecutionId}
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
                    id
                      ? {
                          articleId: id,
                          corpusId: selectedCorpusId,
                          page: "corpora",
                        }
                      : { corpusId: selectedCorpusId, page: "corpora" },
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
