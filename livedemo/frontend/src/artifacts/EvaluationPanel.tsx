import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useMemo, useState } from "react";

import {
  ArticleSummary,
  ExecutionDetail,
  EvaluationArtifact,
  createClusterInspectionArtifact,
  createComponentTableArtifact,
  createRankCorrelationArtifact,
  createTopMOverlapArtifact,
  createUserStudyBundleArtifact,
  listExecutions,
  runFullEvaluationSuite,
} from "../api/client";
import { formatGroupName } from "../utils/format";
import { ArtifactCard } from "./ArtifactCard";

export function EvaluationPanel({
  artifacts,
  articles,
  execution,
}: {
  artifacts: EvaluationArtifact[];
  articles: ArticleSummary[];
  execution: ExecutionDetail;
}) {
  const queryClient = useQueryClient();
  const [baselineId, setBaselineId] = useState("");
  const [topM, setTopM] = useState(
    Math.min(execution.m ?? 3, Math.max(1, articles.length)),
  );
  const [method, setMethod] = useState<"kendall" | "spearman">("kendall");
  const [rareThreshold, setRareThreshold] = useState(1);
  const [includeScores, setIncludeScores] = useState(false);
  const baselines = useQuery({
    queryKey: ["baseline-executions", execution.corpus_id],
    queryFn: () =>
      listExecutions({
        corpus_id: execution.corpus_id,
        status: "succeeded",
        limit: 100,
      }),
  });
  const baselineOptions =
    baselines.data?.filter((item) => item.id !== execution.id) ?? [];
  const materials = useMemo(() => articleMaterials(articles), [articles]);
  const invalidateArtifacts = async () => {
    await Promise.all([
      queryClient.invalidateQueries({
        queryKey: ["evaluation-artifacts", execution.id],
      }),
      queryClient.invalidateQueries({ queryKey: ["execution", execution.id] }),
    ]);
  };
  const topOverlap = useMutation({
    mutationFn: () =>
      createTopMOverlapArtifact(execution.id, {
        other_execution_id: baselineId,
        m: topM,
      }),
    onSuccess: invalidateArtifacts,
  });
  const correlation = useMutation({
    mutationFn: () =>
      createRankCorrelationArtifact(execution.id, {
        other_execution_id: baselineId,
        method,
      }),
    onSuccess: invalidateArtifacts,
  });
  const componentTable = useMutation({
    mutationFn: () => createComponentTableArtifact(execution.id),
    onSuccess: invalidateArtifacts,
  });
  const clusterInspection = useMutation({
    mutationFn: () =>
      createClusterInspectionArtifact(execution.id, {
        rare_threshold: rareThreshold,
      }),
    onSuccess: invalidateArtifacts,
  });
  const userStudy = useMutation({
    mutationFn: () =>
      createUserStudyBundleArtifact(execution.id, {
        materials,
        include_scores: includeScores,
      }),
    onSuccess: invalidateArtifacts,
  });
  const fullSuite = useMutation({
    mutationFn: () =>
      runFullEvaluationSuite(execution.id, {
        baseline_execution_id: baselineId,
        m: topM,
        method,
        rare_threshold: rareThreshold,
        materials: execution.kind === "select" ? materials : {},
        include_scores: includeScores,
      }),
    onSuccess: invalidateArtifacts,
  });
  const needsBaseline = !baselineId;

  return (
    <section className="evaluation-panel" aria-labelledby="evaluation-title">
      <header>
        <div>
          <p className="eyebrow">Evaluation</p>
          <h3 id="evaluation-title">Artifacts</h3>
        </div>
        <span>{artifacts.length}</span>
      </header>
      <div className="evaluation-controls">
        <label>
          Baseline
          <select
            onChange={(event) => setBaselineId(event.target.value)}
            value={baselineId}
          >
            <option value="">Choose baseline</option>
            {baselineOptions.map((item) => (
              <option key={item.id} value={item.id}>
                {formatGroupName(item.kind)} · {item.profiles.join(", ")}
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
        <label>
          Rare threshold
          <input
            min="1"
            onChange={(event) => setRareThreshold(Number(event.target.value))}
            type="number"
            value={rareThreshold}
          />
        </label>
        <label className="inline-check">
          <input
            checked={includeScores}
            onChange={(event) => setIncludeScores(event.target.checked)}
            type="checkbox"
          />
          Include scores
        </label>
      </div>
      {baselines.error && <p className="error-line">{baselines.error.message}</p>}
      {baselines.isLoading && <p className="muted">Loading baselines</p>}
      {!baselines.isLoading && baselineOptions.length === 0 && (
        <p className="muted">Run another succeeded execution to compare against.</p>
      )}
      <div className="evaluation-actions">
        <button
          disabled={needsBaseline || topOverlap.isPending}
          onClick={() => topOverlap.mutate()}
          type="button"
        >
          Top-M Overlap
        </button>
        <button
          disabled={needsBaseline || correlation.isPending}
          onClick={() => correlation.mutate()}
          type="button"
        >
          Rank Correlation
        </button>
        <button
          disabled={componentTable.isPending}
          onClick={() => componentTable.mutate()}
          type="button"
        >
          Component Table
        </button>
        <button
          disabled={clusterInspection.isPending}
          onClick={() => clusterInspection.mutate()}
          type="button"
        >
          Cluster Inspection
        </button>
        <button
          disabled={execution.kind !== "select" || userStudy.isPending}
          onClick={() => userStudy.mutate()}
          type="button"
        >
          User-Study Bundle
        </button>
        <button
          disabled={needsBaseline || fullSuite.isPending}
          onClick={() => fullSuite.mutate()}
          type="button"
        >
          Run Full Test Suite
        </button>
      </div>
      {[
        topOverlap.error,
        correlation.error,
        componentTable.error,
        clusterInspection.error,
        userStudy.error,
        fullSuite.error,
      ].map((error) =>
        error ? (
          <p className="error-line" key={error.message}>
            {error.message}
          </p>
        ) : null,
      )}
      {artifacts.length === 0 ? (
        <p className="muted">No evaluation artifacts yet.</p>
      ) : (
        <div className="artifact-list">
          {artifacts.map((artifact) => (
            <ArtifactCard artifact={artifact} key={artifact.id} />
          ))}
        </div>
      )}
    </section>
  );
}

function articleMaterials(
  articles: ArticleSummary[],
): Record<string, { title: string; snippet: string }> {
  return Object.fromEntries(
    articles.map((article) => [
      article.id,
      {
        title: article.title,
        snippet: article.filename,
      },
    ]),
  );
}
