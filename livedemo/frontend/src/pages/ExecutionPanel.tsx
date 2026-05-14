import { useQuery } from "@tanstack/react-query";

import {
  ArticleSummary,
  ExecutionDetail,
  getExecution,
  listEvaluationArtifacts,
} from "../api/client";
import { EvaluationPanel } from "../artifacts/EvaluationPanel";
import { ResultPayloadTable } from "../artifacts/ResultPayloadTable";
import { draftFromExecution, ParameterDraft } from "../forms/configDraft";
import { formatGroupName } from "../utils/format";

export function ExecutionPanel({
  articles,
  executionId,
  onReplay,
}: {
  articles: ArticleSummary[];
  executionId: string | null;
  onReplay: (draft: ParameterDraft) => void;
}) {
  const execution = useQuery({
    queryKey: ["execution", executionId],
    queryFn: () => getExecution(executionId ?? ""),
    enabled: executionId !== null,
    refetchInterval: (query) => {
      const data = query.state.data as ExecutionDetail | undefined;
      return data?.status === "pending" || data?.status === "running"
        ? 1000
        : false;
    },
  });
  const artifacts = useQuery({
    queryKey: ["evaluation-artifacts", executionId],
    queryFn: () => listEvaluationArtifacts(executionId ?? ""),
    enabled: executionId !== null && execution.data?.status === "succeeded",
    initialData: execution.data?.evaluation_artifacts,
  });

  if (!executionId) {
    return null;
  }
  if (execution.isLoading) {
    return <section className="execution-panel muted">Loading execution</section>;
  }
  if (execution.error) {
    return (
      <section className="execution-panel error-line">
        {execution.error.message}
      </section>
    );
  }
  if (!execution.data) {
    return null;
  }

  return (
    <section className="execution-panel" aria-labelledby="execution-title">
      <header>
        <div>
          <p className="eyebrow">Execution</p>
          <h3 id="execution-title">{formatGroupName(execution.data.kind)}</h3>
        </div>
        <div className="execution-header-actions">
          <button
            disabled={execution.data.kind === "evaluate"}
            onClick={() => onReplay(draftFromExecution(execution.data))}
            type="button"
          >
            Replay
          </button>
          <span className={`status-pill ${execution.data.status}`}>
            {execution.data.status}
          </span>
        </div>
      </header>
      {execution.data.error && <p className="error-line">{execution.data.error}</p>}
      {execution.data.status !== "succeeded" && (
        <p className="muted">Execution is {execution.data.status}.</p>
      )}
      <details>
        <summary>Parameters</summary>
        <pre>{JSON.stringify(execution.data.config_json, null, 2)}</pre>
      </details>
      {execution.data.results.length === 0 ? (
        <p className="muted">No persisted result rows yet.</p>
      ) : (
        execution.data.results.map((result) => (
          <ResultPayloadTable
            key={result.id}
            articles={articles}
            payload={result.result_json}
          />
        ))
      )}
      {execution.data.status === "succeeded" && (
        <EvaluationPanel
          artifacts={artifacts.data ?? execution.data.evaluation_artifacts}
          articles={articles}
          execution={execution.data}
        />
      )}
    </section>
  );
}
