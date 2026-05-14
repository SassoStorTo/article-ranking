import { useMemo } from "react";

import {
  ArticleSummary,
  ExecutionResultJson,
  RankingEntry,
} from "../api/client";
import { formatGroupName, formatScore } from "../utils/format";

export function ResultPayloadTable({
  articles,
  payload,
}: {
  articles: ArticleSummary[];
  payload: ExecutionResultJson;
}) {
  const articleLookup = useMemo(() => {
    return new Map(articles.map((article) => [article.id, article]));
  }, [articles]);
  const selectedIds = selectedArticleIds(payload);

  if (payload.__type__ === "profile_comparison") {
    return (
      <div className="comparison-grid">
        {Object.entries(payload.rankings).map(([profile, ranking]) => (
          <RankingTable
            articleLookup={articleLookup}
            entries={ranking.entries}
            key={profile}
            profile={profile}
            selectedArticleIds={selectedIds}
          />
        ))}
      </div>
    );
  }

  if (payload.__type__ === "selection_result") {
    return (
      <RankingTable
        articleLookup={articleLookup}
        entries={payload.ranking.entries}
        profile={`${payload.profile} · selected ${payload.m}`}
        selectedArticleIds={selectedIds}
      />
    );
  }

  return (
    <RankingTable
      articleLookup={articleLookup}
      entries={payload.entries}
      profile={payload.profile}
      selectedArticleIds={selectedIds}
    />
  );
}

function RankingTable({
  articleLookup,
  profile,
  entries,
  selectedArticleIds,
}: {
  articleLookup: Map<string, ArticleSummary>;
  profile: string;
  entries: RankingEntry[];
  selectedArticleIds: Set<string>;
}) {
  return (
    <div className="result-table-wrap">
      <h4>{formatGroupName(profile)}</h4>
      <table className="result-table">
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
          {entries.map((entry) => (
            <tr key={entry.article_id}>
              <td>{entry.rank}</td>
              <td>
                <div className="article-cell">
                  <strong>
                    {articleLookup.get(entry.article_id)?.title ?? "Untitled article"}
                  </strong>
                  <span>{entry.article_id}</span>
                </div>
                {selectedArticleIds.has(entry.article_id) && (
                  <span className="selected-badge">Selected</span>
                )}
              </td>
              <td>{formatScore(entry.score)}</td>
              <td>{formatScore(entry.components.centrality)}</td>
              <td>{formatScore(entry.components.coverage)}</td>
              <td>{formatScore(entry.components.density)}</td>
              <td>{formatScore(entry.components.entity_coverage)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function selectedArticleIds(payload: ExecutionResultJson): Set<string> {
  if (payload.__type__ !== "selection_result") {
    return new Set();
  }
  return new Set(payload.selected.map((entry) => entry.article_id));
}
