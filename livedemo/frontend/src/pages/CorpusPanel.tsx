import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";

import {
  CorpusSummary,
  deleteCorpus,
  getCorpus,
  uploadArticles,
} from "../api/client";
import { ArticleBody } from "../components/ArticleBody";
import { ArticleList } from "../components/ArticleList";
import { ExecutionControls } from "../components/ExecutionControls";
import { ParameterForm } from "../forms/ParameterForm";
import { ParameterDraft } from "../forms/configDraft";
import { ExecutionPanel } from "./ExecutionPanel";

export function CorpusPanel({
  corpusId,
  fallbackCorpus,
  selectedArticleId,
  onSelectArticle,
  selectedExecutionId,
  onSelectExecution,
  onDeleted,
}: {
  corpusId: string;
  fallbackCorpus: CorpusSummary | null;
  selectedArticleId: string | null;
  onSelectArticle: (id: string | null) => void;
  selectedExecutionId: string | null;
  onSelectExecution: (id: string | null) => void;
  onDeleted: () => void;
}) {
  const queryClient = useQueryClient();
  const [parameterDraft, setParameterDraft] = useState<ParameterDraft | null>(null);
  const corpus = useQuery({
    queryKey: ["corpus", corpusId],
    queryFn: () => getCorpus(corpusId),
  });
  const deleteMutation = useMutation({
    mutationFn: () => deleteCorpus(corpusId),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["corpora"] });
      onDeleted();
    },
  });
  const uploadMutation = useMutation({
    mutationFn: (files: FileList) => uploadArticles(corpusId, files),
    onSuccess: async () => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ["corpora"] }),
        queryClient.invalidateQueries({ queryKey: ["corpus", corpusId] }),
      ]);
    },
  });

  const detail = corpus.data;
  const heading = detail?.name ?? fallbackCorpus?.name ?? "Article Set";

  return (
    <section className="detail-panel" aria-labelledby="corpus-title">
      <header className="detail-header">
        <div>
          <p className="eyebrow">Article Set</p>
          <h2 id="corpus-title">{heading}</h2>
          {detail?.notes && <p className="notes">{detail.notes}</p>}
        </div>
        <div className="detail-header-actions">
          <label className="upload-zone compact">
            <input
              accept=".txt,.json,text/plain,application/json"
              disabled={uploadMutation.isPending}
              multiple
              onChange={(event) => {
                if (event.target.files?.length) {
                  uploadMutation.mutate(event.target.files);
                  event.target.value = "";
                }
              }}
              type="file"
            />
            <span>Add articles</span>
          </label>
          <button
            className="danger"
            disabled={deleteMutation.isPending}
            onClick={() => {
              if (
                window.confirm(
                  `Delete article set "${heading}" and all of its data?`,
                )
              ) {
                deleteMutation.mutate();
              }
            }}
            type="button"
          >
            Delete Article Set
          </button>
        </div>
      </header>
      {deleteMutation.error && (
        <p className="error-line">{deleteMutation.error.message}</p>
      )}
      {uploadMutation.error && (
        <p className="error-line">{uploadMutation.error.message}</p>
      )}
      {uploadMutation.isPending && (
        <p className="muted">Uploading articles and decompositions</p>
      )}

      {corpus.isLoading && <p className="muted">Loading articles</p>}
      {corpus.error && <p className="error-line">{corpus.error.message}</p>}
      {detail && (
        <>
          <ExecutionControls
            articleCount={detail.articles.length}
            onCompare={() => {
              setParameterDraft({
                mode: "compare_profiles",
                profiles: ["representative", "comprehensive", "concise"],
              });
            }}
            onRank={() => {
              setParameterDraft({
                mode: "rank",
                profile: "representative",
              });
            }}
            onSelect={() => {
              setParameterDraft({
                mode: "select",
                m: Math.min(3, Math.max(1, detail.articles.length)),
                profile: "representative",
              });
            }}
          />
          {parameterDraft && (
            <ParameterForm
              articleCount={detail.articles.length}
              corpusId={corpusId}
              draft={parameterDraft}
              onCancel={() => setParameterDraft(null)}
              onSubmitted={(executionId) => {
                setParameterDraft(null);
                onSelectExecution(executionId);
              }}
            />
          )}
          <div className="article-grid">
            <ArticleList
              articles={detail.articles}
              selectedArticleId={selectedArticleId}
              onSelectArticle={onSelectArticle}
            />
            <ArticleBody articleId={selectedArticleId} />
          </div>
          <ExecutionPanel
            articles={detail.articles}
            executionId={selectedExecutionId}
            onReplay={(draft) => setParameterDraft(draft)}
          />
        </>
      )}
    </section>
  );
}
