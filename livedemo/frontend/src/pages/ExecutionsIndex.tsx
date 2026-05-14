import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";

import {
  CorpusSummary,
  ExecutionKind,
  ExecutionStatus,
  ExecutionSummary,
  createRankCorrelationArtifact,
  createTopMOverlapArtifact,
  deleteExecution,
  listExecutions,
  replayExecution,
} from "../api/client";
import { Metric } from "../components/Metric";
import {
  dateEnd,
  dateStart,
  formatDateTime,
  formatGroupName,
} from "../utils/format";

type ExecutionFilters = {
  corpusId: string;
  kind: "" | ExecutionKind;
  status: "" | ExecutionStatus;
  profile: string;
  createdFrom: string;
  createdTo: string;
};

const emptyExecutionFilters: ExecutionFilters = {
  corpusId: "",
  kind: "",
  status: "",
  profile: "",
  createdFrom: "",
  createdTo: "",
};

export function ExecutionsIndex({
  corpora,
  onClose,
  onOpenExecution,
}: {
  corpora: CorpusSummary[];
  onClose: () => void;
  onOpenExecution: (execution: ExecutionSummary) => void;
}) {
  const queryClient = useQueryClient();
  const [filters, setFilters] = useState<ExecutionFilters>(emptyExecutionFilters);
  const [offset, setOffset] = useState(0);
  const [compareTarget, setCompareTarget] = useState<ExecutionSummary | null>(null);
  const limit = 20;
  const executions = useQuery({
    queryKey: ["executions-index", filters, offset, limit],
    queryFn: () =>
      listExecutions({
        corpus_id: filters.corpusId || undefined,
        kind: filters.kind || undefined,
        status: filters.status || undefined,
        profile: filters.profile.trim() || undefined,
        created_from: dateStart(filters.createdFrom),
        created_to: dateEnd(filters.createdTo),
        limit,
        offset,
      }),
  });
  const deleteMutation = useMutation({
    mutationFn: deleteExecution,
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["executions-index"] });
      await queryClient.invalidateQueries({ queryKey: ["corpora"] });
    },
  });
  const replayMutation = useMutation({
    mutationFn: (executionId: string) => replayExecution(executionId),
    onSuccess: async ({ execution_id }, sourceId) => {
      const source = executions.data?.find((item) => item.id === sourceId);
      await queryClient.invalidateQueries({ queryKey: ["executions-index"] });
      if (source) {
        onOpenExecution({ ...source, id: execution_id, status: "pending" });
      }
    },
  });
  const rows = executions.data ?? [];
  const hasRows = rows.length > 0;

  function updateFilter<K extends keyof ExecutionFilters>(
    key: K,
    value: ExecutionFilters[K],
  ) {
    setFilters((current) => ({ ...current, [key]: value }));
    setOffset(0);
  }

  return (
    <section className="executions-index detail-panel" aria-labelledby="old-title">
      <header className="detail-header">
        <div>
          <p className="eyebrow">Old Executions</p>
          <h2 id="old-title">Execution History</h2>
        </div>
        <button onClick={onClose} type="button">
          Article Sets
        </button>
      </header>

      <div className="execution-filters">
        <label>
          Article Set
          <select
            onChange={(event) => updateFilter("corpusId", event.target.value)}
            value={filters.corpusId}
          >
            <option value="">All article sets</option>
            {corpora.map((corpus) => (
              <option key={corpus.id} value={corpus.id}>
                {corpus.name}
              </option>
            ))}
          </select>
        </label>
        <label>
          Kind
          <select
            onChange={(event) =>
              updateFilter("kind", event.target.value as ExecutionFilters["kind"])
            }
            value={filters.kind}
          >
            <option value="">All kinds</option>
            <option value="rank">rank</option>
            <option value="select">select</option>
            <option value="compare_profiles">compare_profiles</option>
          </select>
        </label>
        <label>
          Status
          <select
            onChange={(event) =>
              updateFilter(
                "status",
                event.target.value as ExecutionFilters["status"],
              )
            }
            value={filters.status}
          >
            <option value="">All statuses</option>
            <option value="pending">pending</option>
            <option value="running">running</option>
            <option value="succeeded">succeeded</option>
            <option value="failed">failed</option>
          </select>
        </label>
        <label>
          Profile
          <input
            onChange={(event) => updateFilter("profile", event.target.value)}
            placeholder="representative"
            value={filters.profile}
          />
        </label>
        <label>
          From
          <input
            onChange={(event) => updateFilter("createdFrom", event.target.value)}
            type="date"
            value={filters.createdFrom}
          />
        </label>
        <label>
          To
          <input
            onChange={(event) => updateFilter("createdTo", event.target.value)}
            type="date"
            value={filters.createdTo}
          />
        </label>
      </div>

      {executions.isLoading && <p className="muted">Loading executions</p>}
      {executions.error && <p className="error-line">{executions.error.message}</p>}
      {deleteMutation.error && (
        <p className="error-line">{deleteMutation.error.message}</p>
      )}
      {replayMutation.error && (
        <p className="error-line">{replayMutation.error.message}</p>
      )}
      {!executions.isLoading && !executions.error && !hasRows ? (
        <p className="muted">No executions match these filters.</p>
      ) : null}
      {hasRows ? (
        <div className="result-table-wrap">
          <table className="result-table executions-table">
            <thead>
              <tr>
                <th>Article Set</th>
                <th>Kind</th>
                <th>Profile</th>
                <th>Status</th>
                <th>Started</th>
                <th>Finished</th>
                <th>Eval</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((execution) => (
                <tr key={execution.id}>
                  <td>{execution.corpus_name || execution.corpus_id}</td>
                  <td>{formatGroupName(execution.kind)}</td>
                  <td>{execution.profile_summary}</td>
                  <td>
                    <span className={`status-pill ${execution.status}`}>
                      {execution.status}
                    </span>
                  </td>
                  <td>{formatDateTime(execution.started_at)}</td>
                  <td>{formatDateTime(execution.finished_at)}</td>
                  <td>{execution.has_evaluation_artifacts ? "yes" : "no"}</td>
                  <td>
                    <div className="row-actions">
                      <button onClick={() => onOpenExecution(execution)} type="button">
                        Open
                      </button>
                      <button
                        disabled={
                          execution.kind === "evaluate" || replayMutation.isPending
                        }
                        onClick={() => replayMutation.mutate(execution.id)}
                        type="button"
                      >
                        Replay
                      </button>
                      <button
                        className="danger"
                        disabled={deleteMutation.isPending}
                        onClick={() => deleteMutation.mutate(execution.id)}
                        type="button"
                      >
                        Delete
                      </button>
                      <button
                        disabled={!isComparableExecution(execution)}
                        onClick={() => setCompareTarget(execution)}
                        type="button"
                      >
                        Compare
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : null}

      {(hasRows || offset > 0) && (
        <div className="pagination-controls">
          <button
            disabled={offset === 0 || executions.isFetching}
            onClick={() => setOffset((current) => Math.max(0, current - limit))}
            type="button"
          >
            Previous
          </button>
          <span>{hasRows ? `${offset + 1}-${offset + rows.length}` : "0"}</span>
          <button
            disabled={rows.length < limit || executions.isFetching}
            onClick={() => setOffset((current) => current + limit)}
            type="button"
          >
            Next
          </button>
        </div>
      )}
      {compareTarget && (
        <CompareExecutionModal
          onClose={() => setCompareTarget(null)}
          target={compareTarget}
        />
      )}
    </section>
  );
}

function CompareExecutionModal({
  target,
  onClose,
}: {
  target: ExecutionSummary;
  onClose: () => void;
}) {
  const queryClient = useQueryClient();
  const [otherExecutionId, setOtherExecutionId] = useState("");
  const [topM, setTopM] = useState(target.m ?? 3);
  const [method, setMethod] = useState<"kendall" | "spearman">("kendall");
  const candidates = useQuery({
    queryKey: ["compare-execution-candidates"],
    queryFn: () => listExecutions({ status: "succeeded", limit: 100 }),
  });
  const options =
    candidates.data?.filter(
      (execution) =>
        execution.id !== target.id && isComparableExecution(execution),
    ) ?? [];
  const compareMutation = useMutation({
    mutationFn: async () => {
      const overlap = await createTopMOverlapArtifact(target.id, {
        other_execution_id: otherExecutionId,
        m: topM,
      });
      const correlation = await createRankCorrelationArtifact(target.id, {
        other_execution_id: otherExecutionId,
        method,
      });
      return [overlap, correlation];
    },
    onSuccess: async () => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ["executions-index"] }),
        queryClient.invalidateQueries({ queryKey: ["execution", target.id] }),
        queryClient.invalidateQueries({
          queryKey: ["evaluation-artifacts", target.id],
        }),
      ]);
      onClose();
    },
  });
  const selectedCandidate = options.find((item) => item.id === otherExecutionId);

  return (
    <div className="modal-backdrop" role="presentation">
      <section
        aria-labelledby="compare-title"
        aria-modal="true"
        className="compare-modal"
        role="dialog"
      >
        <header>
          <div>
            <p className="eyebrow">Compare With</p>
            <h3 id="compare-title">{target.profile_summary}</h3>
          </div>
          <button onClick={onClose} type="button">
            Close
          </button>
        </header>
        <div className="compare-summary">
          <Metric label="Target" value={formatGroupName(target.kind)} />
          <Metric
            label="Article Set"
            value={target.corpus_name || target.corpus_id}
          />
        </div>
        <div className="execution-filters">
          <label>
            Execution
            <select
              onChange={(event) => setOtherExecutionId(event.target.value)}
              value={otherExecutionId}
            >
              <option value="">Choose execution</option>
              {options.map((execution) => (
                <option key={execution.id} value={execution.id}>
                  {execution.corpus_name || execution.corpus_id} ·{" "}
                  {formatGroupName(execution.kind)} · {execution.profile_summary}
                </option>
              ))}
            </select>
          </label>
          <label>
            M
            <input
              min="1"
              onChange={(event) => setTopM(Number(event.target.value))}
              type="number"
              value={topM}
            />
          </label>
          <label>
            Correlation
            <select
              onChange={(event) =>
                setMethod(event.target.value as "kendall" | "spearman")
              }
              value={method}
            >
              <option value="kendall">kendall</option>
              <option value="spearman">spearman</option>
            </select>
          </label>
        </div>
        {candidates.isLoading && <p className="muted">Loading candidates</p>}
        {!candidates.isLoading && options.length === 0 && (
          <p className="muted">No compatible succeeded executions yet.</p>
        )}
        {selectedCandidate && (
          <p className="muted">
            Artifacts will be stored on {target.profile_summary} from{" "}
            {target.corpus_name || target.corpus_id}.
          </p>
        )}
        {candidates.error && <p className="error-line">{candidates.error.message}</p>}
        {compareMutation.error && (
          <p className="error-line">{compareMutation.error.message}</p>
        )}
        <div className="form-actions">
          <button
            disabled={!otherExecutionId || topM < 1 || compareMutation.isPending}
            onClick={() => compareMutation.mutate()}
            type="button"
          >
            {compareMutation.isPending ? "Comparing" : "Run Compare"}
          </button>
        </div>
      </section>
    </div>
  );
}

function isComparableExecution(execution: ExecutionSummary) {
  return (
    execution.status === "succeeded" &&
    (execution.kind === "rank" || execution.kind === "select")
  );
}
