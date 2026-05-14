export function EmptyWorkspace() {
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
