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
  CorpusDetail,
  CorpusSummary,
  createCorpus,
  deleteCorpus,
  getArticle,
  getCorpus,
  listCorpora,
  uploadArticles,
} from "./api/client";

const queryClient = new QueryClient();

function App() {
  const [selectedCorpusId, setSelectedCorpusId] = useState<string | null>(null);
  const [selectedArticleId, setSelectedArticleId] = useState<string | null>(null);
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
          }}
        />
        {selectedCorpusId ? (
          <CorpusPanel
            corpusId={selectedCorpusId}
            fallbackCorpus={selectedCorpus}
            selectedArticleId={selectedArticleId}
            onSelectArticle={setSelectedArticleId}
            onDeleted={() => {
              setSelectedCorpusId(null);
              setSelectedArticleId(null);
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
  onDeleted,
}: {
  corpusId: string;
  fallbackCorpus: CorpusSummary | null;
  selectedArticleId: string | null;
  onSelectArticle: (id: string | null) => void;
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
        <div className="article-grid">
          <ArticleList
            articles={detail.articles}
            selectedArticleId={selectedArticleId}
            onSelectArticle={onSelectArticle}
          />
          <ArticleBody articleId={selectedArticleId} />
        </div>
      )}
    </section>
  );
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
          <small>{article.body_length.toLocaleString()} chars</small>
        </button>
      ))}
    </div>
  );
}

function ArticleBody({ articleId }: { articleId: string | null }) {
  const article = useQuery({
    queryKey: ["article", articleId],
    queryFn: () => getArticle(articleId ?? ""),
    enabled: articleId !== null,
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
    <article className="article-body">
      <header>
        <h3>{article.data.title}</h3>
        <p>{article.data.filename}</p>
      </header>
      <pre>{article.data.body}</pre>
    </article>
  );
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
