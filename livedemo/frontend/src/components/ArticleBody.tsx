import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import {
  StructuredArticleRecord,
  decomposeArticle,
  deleteArticle,
  getArticle,
} from "../api/client";
import { formatGroupName } from "../utils/format";

export function ArticleBody({
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
  const isJsonUpload = article.data.filename.toLowerCase().endsWith(".json");

  return (
    <div className="article-inspector">
      <article className="article-body">
        <header>
          <div>
            <h3>{article.data.title}</h3>
            <p>{article.data.filename}</p>
            {isJsonUpload && (
              <span className="source-badge">Precomputed JSON decomposition</span>
            )}
          </div>
          <div className="row-actions">
            <button
              disabled={
                isJsonUpload || decomposeMutation.isPending || deleteMutation.isPending
              }
              onClick={() => decomposeMutation.mutate()}
              type="button"
            >
              {isJsonUpload
                ? "Precomputed"
                : decomposeMutation.isPending
                  ? "Running"
                  : "Decompose"}
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
