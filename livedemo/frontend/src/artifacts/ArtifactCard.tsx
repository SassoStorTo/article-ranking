import { EvaluationArtifact } from "../api/client";
import {
  formatCell,
  formatGroupName,
  formatIdList,
  formatUnknownScore,
} from "../utils/format";
import { arrayPayload } from "../utils/payload";
import { Metric } from "../components/Metric";

export function ArtifactCard({ artifact }: { artifact: EvaluationArtifact }) {
  const payload = artifact.payload_json;
  return (
    <article className="artifact-card">
      <header>
        <div>
          <h4>{formatGroupName(artifact.helper)}</h4>
          <small>{new Date(artifact.created_at).toLocaleString()}</small>
        </div>
        {artifact.helper === "anonymized_user_study_bundle" && (
          <a
            download={`user-study-${artifact.id}.json`}
            href={`data:application/json;charset=utf-8,${encodeURIComponent(
              JSON.stringify(payload, null, 2),
            )}`}
          >
            JSON
          </a>
        )}
      </header>
      <ArtifactPayload artifact={artifact} />
    </article>
  );
}

function ArtifactPayload({ artifact }: { artifact: EvaluationArtifact }) {
  const payload = artifact.payload_json;
  if (artifact.helper === "top_m_overlap") {
    return (
      <div className="metric-grid">
        <Metric label="Overlap" value={payload.overlap_count} />
        <Metric label="Jaccard" value={formatUnknownScore(payload.jaccard)} />
        <Metric label="Left top" value={payload.left_top_count} />
        <Metric label="Right top" value={payload.right_top_count} />
        <p>{formatIdList(payload.overlap_article_ids)}</p>
      </div>
    );
  }
  if (artifact.helper === "rank_correlation") {
    return (
      <div className="metric-grid">
        <Metric label="Method" value={payload.method} />
        <Metric
          label="Coefficient"
          value={formatUnknownScore(payload.coefficient)}
        />
        <Metric label="Common" value={payload.common_count} />
        <p>Left-only: {formatIdList(payload.left_only_article_ids)}</p>
        <p>Right-only: {formatIdList(payload.right_only_article_ids)}</p>
      </div>
    );
  }
  if (artifact.helper === "component_score_table") {
    return <ArtifactRows rows={arrayPayload(payload.rows)} />;
  }
  if (artifact.helper === "cluster_inspection_rows") {
    return (
      <div className="cluster-artifacts">
        {arrayPayload(payload.rows).map((row, index) => (
          <details key={`${row.cluster_index}-${index}`}>
            <summary>
              {String(row.canonical_fact_text ?? "Cluster")} · support{" "}
              {String(row.support_count ?? "0")}{" "}
              {row.is_rare ? <span className="selected-badge">Rare</span> : null}
            </summary>
            <p>Articles: {formatIdList(row.support_article_ids)}</p>
            <p>Facts: {formatIdList(row.member_fact_ids)}</p>
            <p>{formatIdList(row.member_texts)}</p>
          </details>
        ))}
      </div>
    );
  }
  if (artifact.helper === "anonymized_user_study_bundle") {
    return (
      <div className="metric-grid">
        <Metric label="Profile" value={payload.profile} />
        <Metric label="M" value={payload.m} />
        <p>Labels: {formatIdList(payload.selected_article_labels)}</p>
        <pre>{JSON.stringify(payload.article_materials, null, 2)}</pre>
      </div>
    );
  }
  return <pre>{JSON.stringify(payload, null, 2)}</pre>;
}

function ArtifactRows({ rows }: { rows: Record<string, unknown>[] }) {
  const columns = rows.slice(0, 1).flatMap((row) => Object.keys(row));
  if (rows.length === 0) {
    return <p className="muted">No rows.</p>;
  }
  return (
    <div className="result-table-wrap">
      <table className="result-table compact">
        <thead>
          <tr>
            {columns.map((column) => (
              <th key={column}>{formatGroupName(column)}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, index) => (
            <tr key={index}>
              {columns.map((column) => (
                <td key={column}>{formatCell(row[column])}</td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
