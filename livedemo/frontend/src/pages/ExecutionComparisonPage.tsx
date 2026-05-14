import { useQuery } from "@tanstack/react-query";

import {
  ExecutionComparisonMetadata,
  ExecutionComparisonMetrics,
  ExecutionComparisonWarning,
  ExecutionSummary,
  getExecutionComparison,
  listExecutions,
} from "../api/client";
import { ComparisonResultTables } from "../artifacts/ComparisonResultTables";
import { Metric } from "../components/Metric";
import { formatDateTime, formatGroupName, formatScore } from "../utils/format";

export function ExecutionComparisonPage({
  leftExecutionId,
  rightExecutionId,
  onBack,
  onSelectExecutions,
}: {
  leftExecutionId?: string;
  rightExecutionId?: string;
  onBack: () => void;
  onSelectExecutions: (leftExecutionId?: string, rightExecutionId?: string) => void;
}) {
  const candidates = useQuery({
    queryKey: ["execution-comparison-candidates"],
    queryFn: () => listExecutions({ status: "succeeded", limit: 100 }),
  });
  const comparison = useQuery({
    enabled: Boolean(leftExecutionId && rightExecutionId),
    queryKey: ["execution-comparison", leftExecutionId, rightExecutionId],
    queryFn: () =>
      getExecutionComparison({
        left_execution_id: leftExecutionId ?? "",
        right_execution_id: rightExecutionId ?? "",
      }),
  });
  const options = (candidates.data ?? []).filter(isComparableExecution);
  const hasBothIds = Boolean(leftExecutionId && rightExecutionId);

  return (
    <section className="comparison-page detail-panel" aria-labelledby="compare-title">
      <header className="detail-header">
        <div className="detail-header-copy">
          <p className="eyebrow">Execution Comparison</p>
          <h2 id="compare-title">Compare executions</h2>
          <p className="workspace-intro">
            Pick two succeeded rank, select, or compare_profiles executions. URL keeps
            selected ids for refresh and sharing.
          </p>
        </div>
        <button onClick={onBack} type="button">
          Execution History
        </button>
      </header>

      <div className="comparison-selectors">
        <ExecutionSelect
          label="Left execution"
          onChange={(value) => onSelectExecutions(value || undefined, rightExecutionId)}
          options={options}
          value={leftExecutionId ?? ""}
        />
        <ExecutionSelect
          label="Right execution"
          onChange={(value) => onSelectExecutions(leftExecutionId, value || undefined)}
          options={options}
          value={rightExecutionId ?? ""}
        />
      </div>

      {candidates.isLoading && <p className="muted">Loading executions</p>}
      {candidates.error && <p className="error-line">{candidates.error.message}</p>}
      {!candidates.isLoading && options.length === 0 ? (
        <p className="muted">No succeeded comparable executions yet.</p>
      ) : null}

      {!hasBothIds ? (
        <div className="empty-state">
          <p className="muted">Select two executions to load comparison.</p>
        </div>
      ) : null}

      {comparison.isLoading && <p className="muted">Loading comparison</p>}
      {comparison.error && <p className="error-line">{comparison.error.message}</p>}

      {comparison.data ? (
        <>
          <div className="comparison-metadata-grid">
            <MetadataCard metadata={comparison.data.left} title="Left" />
            <MetadataCard metadata={comparison.data.right} title="Right" />
          </div>
          <WarningList warnings={comparison.data.warnings} />
          <div className="comparison-pair-list">
            {comparison.data.section_pairs.map((pair) => (
              <section className="comparison-pair-card" key={pair.key}>
                <header>
                  <div>
                    <p className="eyebrow">Section Pair</p>
                    <h3>{formatGroupName(pair.label)}</h3>
                  </div>
                </header>
                <MetricsSummary metrics={pair.metrics} />
                <WarningList warnings={pair.warnings} />
                <ComparisonResultTables pair={pair} />
              </section>
            ))}
          </div>
        </>
      ) : null}
    </section>
  );
}

function ExecutionSelect({
  label,
  options,
  value,
  onChange,
}: {
  label: string;
  options: ExecutionSummary[];
  value: string;
  onChange: (value: string) => void;
}) {
  return (
    <label>
      {label}
      <select onChange={(event) => onChange(event.target.value)} value={value}>
        <option value="">Choose execution</option>
        {options.map((execution) => (
          <option key={execution.id} value={execution.id}>
            {execution.corpus_name || execution.corpus_id} · {formatGroupName(execution.kind)} · {execution.profile_summary}
          </option>
        ))}
      </select>
    </label>
  );
}

function MetadataCard({
  metadata,
  title,
}: {
  metadata: ExecutionComparisonMetadata;
  title: string;
}) {
  return (
    <section className="comparison-metadata-card">
      <header>
        <div>
          <p className="eyebrow">{title}</p>
          <h3>{metadata.profile_summary}</h3>
        </div>
        <span className={`status-pill ${metadata.status}`}>{metadata.status}</span>
      </header>
      <div className="metric-grid">
        <Metric label="Article Set" value={metadata.corpus_name || metadata.corpus_id} />
        <Metric label="Kind" value={formatGroupName(metadata.kind)} />
        <Metric label="Profiles" value={metadata.profiles.join(", ") || "none"} />
        <Metric label="M" value={metadata.m ?? "n/a"} />
        <Metric label="Created" value={formatDateTime(metadata.created_at)} />
        <Metric label="Started" value={formatDateTime(metadata.started_at)} />
        <Metric label="Finished" value={formatDateTime(metadata.finished_at)} />
        <Metric label="Eval Artifacts" value={metadata.has_evaluation_artifacts ? "yes" : "no"} />
      </div>
      <details>
        <summary>Effective config JSON</summary>
        <pre>{JSON.stringify(metadata.config_json, null, 2)}</pre>
      </details>
    </section>
  );
}

function MetricsSummary({ metrics }: { metrics: ExecutionComparisonMetrics | null }) {
  if (!metrics) {
    return <p className="muted">Metrics unavailable for this section pair.</p>;
  }
  const overlapCount = metricValue(metrics.top_m_overlap, "overlap_count");
  const overlapRatio = metricValue(metrics.top_m_overlap, "jaccard");
  const correlation = metricValue(metrics.rank_correlation, "coefficient");

  return (
    <div className="metric-grid">
      <Metric label="Top M" value={metrics.top_m ?? "n/a"} />
      <Metric label="Top-M Shared" value={overlapCount} />
      <Metric label="Top-M Overlap" value={formatMetricNumber(overlapRatio)} />
      <Metric label="Kendall" value={formatMetricNumber(correlation)} />
      <Metric label="Left Clusters" value={metrics.left_cluster_count ?? "n/a"} />
      <Metric label="Right Clusters" value={metrics.right_cluster_count ?? "n/a"} />
      <Metric label="Shared Clusters" value={metrics.shared_cluster_count ?? "n/a"} />
      <Metric
        label="Shared Cluster Texts"
        value={metrics.shared_canonical_cluster_texts.length}
      />
    </div>
  );
}

function WarningList({ warnings }: { warnings: ExecutionComparisonWarning[] }) {
  if (warnings.length === 0) {
    return null;
  }
  return (
    <div className="comparison-warnings">
      {warnings.map((warning, index) => (
        <p className="error-line" key={`${warning.code}-${index}`}>
          {warning.code}: {warning.message}
        </p>
      ))}
    </div>
  );
}

function metricValue(payload: Record<string, unknown> | null, key: string): unknown {
  return payload && key in payload ? payload[key] : "n/a";
}

function formatMetricNumber(value: unknown): string {
  return typeof value === "number" ? formatScore(value) : String(value ?? "n/a");
}

function isComparableExecution(execution: ExecutionSummary) {
  return (
    execution.status === "succeeded" &&
    (execution.kind === "rank" ||
      execution.kind === "select" ||
      execution.kind === "compare_profiles")
  );
}
