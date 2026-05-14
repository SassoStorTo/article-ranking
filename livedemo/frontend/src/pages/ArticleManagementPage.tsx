import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { CorpusSummary, getCorpus, uploadArticles } from "../api/client";
import { ArticleBody } from "../components/ArticleBody";
import { ArticleList } from "../components/ArticleList";
import { CorpusList } from "../components/CorpusList";
import { EmptyWorkspace } from "../components/EmptyWorkspace";

export function ArticleManagementPage({
  corpora,
  isLoadingCorpora,
  selectedCorpusId,
  selectedArticleId,
  onSelectCorpus,
  onSelectArticle,
}: {
  corpora: CorpusSummary[];
  isLoadingCorpora: boolean;
  selectedCorpusId: string | null;
  selectedArticleId: string | null;
  onSelectCorpus: (id: string) => void;
  onSelectArticle: (id: string | null) => void;
}) {
  const queryClient = useQueryClient();
  const corpus = useQuery({
    queryKey: ["corpus", selectedCorpusId],
    queryFn: () => getCorpus(selectedCorpusId ?? ""),
    enabled: selectedCorpusId !== null,
  });
  const uploadMutation = useMutation({
    mutationFn: (files: FileList) => uploadArticles(selectedCorpusId ?? "", files),
    onSuccess: async () => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ["corpora"] }),
        queryClient.invalidateQueries({ queryKey: ["corpus", selectedCorpusId] }),
      ]);
    },
  });
  const selectedCorpus = corpora.find((item) => item.id === selectedCorpusId);
  const articles = corpus.data?.articles ?? [];

  return (
    <section className="workspace" aria-label="Article management workspace">
      <aside className="sidebar">
        <CorpusList
          corpora={corpora}
          error={null}
          isLoading={isLoadingCorpora}
          onSelect={onSelectCorpus}
          selectedCorpusId={selectedCorpusId}
        />
      </aside>
      <section className="detail-panel" aria-labelledby="articles-title">
        <header className="detail-header">
          <div>
            <p className="eyebrow">Articles</p>
            <h2 id="articles-title">{selectedCorpus?.name ?? "Add Articles"}</h2>
            <p className="notes">
              Upload `.txt` files, then inspect each article body and structured
              decomposition.
            </p>
          </div>
        </header>
        {!selectedCorpusId ? (
          <EmptyWorkspace />
        ) : (
          <>
            <label className="upload-zone">
              <input
                accept=".txt,text/plain"
                multiple
                onChange={(event) => {
                  if (event.target.files?.length) {
                    uploadMutation.mutate(event.target.files);
                    event.target.value = "";
                  }
                }}
                type="file"
              />
              <span>Upload .txt Articles</span>
            </label>
            {uploadMutation.error && (
              <p className="error-line">{uploadMutation.error.message}</p>
            )}
            {uploadMutation.isPending && <p className="muted">Uploading articles</p>}
            {corpus.isLoading && <p className="muted">Loading articles</p>}
            {corpus.error && <p className="error-line">{corpus.error.message}</p>}
            {corpus.data && (
              <div className="article-grid">
                <ArticleList
                  articles={articles}
                  onSelectArticle={onSelectArticle}
                  selectedArticleId={selectedArticleId}
                />
                <ArticleBody
                  articleId={selectedArticleId}
                  onDeleted={(corpusId) => {
                    onSelectArticle(null);
                    void queryClient.invalidateQueries({ queryKey: ["corpora"] });
                    void queryClient.invalidateQueries({
                      queryKey: ["corpus", corpusId],
                    });
                  }}
                />
              </div>
            )}
          </>
        )}
      </section>
    </section>
  );
}
