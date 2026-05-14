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
