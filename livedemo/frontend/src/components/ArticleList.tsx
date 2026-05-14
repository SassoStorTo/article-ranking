import { ArticleSummary } from "../api/client";

export function ArticleList({
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
      {articles.map((article) => {
        const isJsonUpload = article.filename.toLowerCase().endsWith(".json");
        const statusText = isJsonUpload
          ? "Precomputed decomposition"
          : article.decomposition_status === "decomposed"
            ? "Decomposed"
            : "Pending decomposition";

        return (
          <button
            className={article.id === selectedArticleId ? "selected" : ""}
            key={article.id}
            onClick={() => onSelectArticle(article.id)}
            type="button"
          >
            <strong>{article.title}</strong>
            <span>{article.filename}</span>
            <small>
              {article.body_length.toLocaleString()} chars · {statusText}
            </small>
          </button>
        );
      })}
    </div>
  );
}
