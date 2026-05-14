import { AppPage } from "../app/navigation";

export type ThemeMode = "light" | "dark";

export function TopNavigation({
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
