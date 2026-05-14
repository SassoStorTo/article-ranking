import {
  ExecutionComparisonSection,
  ExecutionComparisonSectionPair,
  RankingEntry,
} from "../api/client";
import { formatGroupName, formatScore } from "../utils/format";

export function ComparisonResultTables({
  pair,
}: {
  pair: ExecutionComparisonSectionPair;
}) {
  return (
    <div className="comparison-section-tables">
      <ComparisonSectionTable section={pair.left} side="Left" />
      <ComparisonSectionTable section={pair.right} side="Right" />
    </div>
  );
}

function ComparisonSectionTable({
  section,
  side,
}: {
  section: ExecutionComparisonSection | null;
  side: string;
}) {
  if (!section) {
    return (
      <div className="comparison-table-card empty-state">
        <h4>{side}</h4>
        <p className="muted">Section unavailable.</p>
      </div>
    );
  }

  return (
    <div className="comparison-table-card result-table-wrap">
      <h4>
        {side}: {formatGroupName(section.label)}
      </h4>
      <p className="muted">
        {formatGroupName(section.result_type)} · {section.entry_count} entries
      </p>
      <table className="result-table compact">
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
          {section.rank_result_json.entries.map((entry) => (
            <ComparisonRow
              entry={entry}
              key={entry.article_id}
              selectedArticleIds={section.selected_article_ids}
            />
          ))}
        </tbody>
      </table>
    </div>
  );
}

function ComparisonRow({
  entry,
  selectedArticleIds,
}: {
  entry: RankingEntry;
  selectedArticleIds: string[];
}) {
  return (
    <tr>
      <td>{entry.rank}</td>
      <td>
        <div className="article-cell">
          <strong>{entry.article_id}</strong>
        </div>
        {selectedArticleIds.includes(entry.article_id) && (
          <span className="selected-badge">Selected</span>
        )}
      </td>
      <td>{formatScore(entry.score)}</td>
      <td>{formatScore(entry.components.centrality)}</td>
      <td>{formatScore(entry.components.coverage)}</td>
      <td>{formatScore(entry.components.density)}</td>
      <td>{formatScore(entry.components.entity_coverage)}</td>
    </tr>
  );
}
