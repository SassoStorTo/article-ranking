export function ExecutionControls({
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
      <button disabled={articleCount === 0} onClick={onSelect} type="button">
        Run Select
      </button>
      <button disabled={articleCount === 0} onClick={onCompare} type="button">
        Compare Profiles
      </button>
    </div>
  );
}
