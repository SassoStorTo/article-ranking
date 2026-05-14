import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";

import {
  CorpusSummary,
  ExecutionKind,
  ExecutionStatus,
  ExecutionSummary,
  deleteExecution,
  listExecutions,
  replayExecution,
} from "../api/client";
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
  onCompareExecution,
}: {
  corpora: CorpusSummary[];
  onClose: () => void;
  onOpenExecution: (execution: ExecutionSummary) => void;
  onCompareExecution: (execution: ExecutionSummary) => void;
}) {
  const queryClient = useQueryClient();
  const [filters, setFilters] = useState<ExecutionFilters>(emptyExecutionFilters);
  const [offset, setOffset] = useState(0);
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
                        onClick={() => onCompareExecution(execution)}
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
    </section>
  );
}

function isComparableExecution(execution: ExecutionSummary) {
  return (
    execution.status === "succeeded" &&
    (execution.kind === "rank" ||
      execution.kind === "select" ||
      execution.kind === "compare_profiles")
  );
}
