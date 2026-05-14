import { formatIdList } from "../utils/format";

export function ClusterInspectionRows({
  articleFilenameById = {},
  rows,
}: {
  articleFilenameById?: Record<string, string>;
  rows: readonly Record<string, unknown>[];
}) {
  if (rows.length === 0) {
    return <p className="muted">No cluster inspection rows.</p>;
  }

  const stats = clusterStats(rows);

  return (
    <>
      <div className="cluster-summary">
        <div>
          <span>Total points</span>
          <strong>{stats.totalPoints}</strong>
        </div>
        <div>
          <span>Cluster sizes</span>
          <ul>
            {stats.sizeDistribution.map((item) => (
              <li key={item}>{item}</li>
            ))}
          </ul>
        </div>
      </div>
      <details className="cluster-list-toggle">
        <summary>Cluster list ({rows.length})</summary>
        <div className="cluster-artifacts">
          {rows.map((row, index) => (
            <details key={`${String(row.cluster_index ?? "cluster")}-${index}`}>
              <summary>
                {String(row.canonical_fact_text ?? "Cluster")} · support{" "}
                {String(row.support_count ?? "0")}{" "}
                {row.is_rare ? <span className="selected-badge">Rare</span> : null}
              </summary>
              <p>Files: {formatIdList(articleNames(row, articleFilenameById))}</p>
              <ClusterPointList row={row} />
            </details>
          ))}
        </div>
      </details>
    </>
  );
}

function ClusterPointList({ row }: { row: Record<string, unknown> }) {
  const factIds = arrayValues(row.member_fact_ids);
  const filenames = arrayValues(row.member_article_filenames);
  const texts = arrayValues(row.member_texts);
  const pointCount = Math.max(factIds.length, filenames.length, texts.length);

  if (pointCount === 0) {
    return <p>Facts: none</p>;
  }

  return (
    <div className="cluster-points">
      {Array.from({ length: pointCount }, (_, index) => (
        <div className="cluster-point" key={`${factIds[index] ?? "point"}-${index}`}>
          <span>Point {index + 1}</span>
          <strong>{texts[index] ?? "No text available"}</strong>
          <small>{filenames[index] ?? factIds[index] ?? "Unknown file"}</small>
        </div>
      ))}
    </div>
  );
}

function clusterStats(rows: readonly Record<string, unknown>[]) {
  const sizes = rows.map(clusterSize);
  const totalPoints = sizes.reduce((total, size) => total + size, 0);
  const counts = new Map<number, number>();
  sizes.forEach((size) => counts.set(size, (counts.get(size) ?? 0) + 1));
  const sizeDistribution = Array.from(counts)
    .sort(([left], [right]) => left - right)
    .map(([size, count]) => {
      const pointLabel = size === 1 ? "point" : "points";
      const clusterLabel = count === 1 ? "cluster" : "clusters";
      return `${size} ${pointLabel}: ${count} ${clusterLabel}`;
    });
  return { totalPoints, sizeDistribution };
}

function clusterSize(row: Record<string, unknown>): number {
  if (Array.isArray(row.member_fact_ids)) {
    return row.member_fact_ids.length;
  }
  if (Array.isArray(row.member_texts)) {
    return row.member_texts.length;
  }
  return 0;
}

function arrayValues(value: unknown): string[] {
  return Array.isArray(value) ? value.map(String) : [];
}

function articleNames(
  row: Record<string, unknown>,
  articleFilenameById: Record<string, string>,
): string[] {
  const filenames = arrayValues(row.support_article_filenames);
  if (filenames.length > 0) {
    return filenames;
  }
  return arrayValues(row.support_article_ids).map(
    (articleId) => articleFilenameById[articleId] ?? articleId,
  );
}
