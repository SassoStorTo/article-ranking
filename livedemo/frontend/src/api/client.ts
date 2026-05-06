export const apiBaseUrl =
  import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

export type CorpusSummary = {
  id: string;
  name: string;
  notes: string | null;
  created_at: string;
  article_count: number;
};

export type ArticleSummary = {
  id: string;
  corpus_id: string;
  filename: string;
  title: string;
  body_length: number;
  uploaded_at: string;
};

export type CorpusDetail = {
  id: string;
  name: string;
  notes: string | null;
  created_at: string;
  articles: ArticleSummary[];
};

export type ArticleDetail = {
  id: string;
  corpus_id: string;
  filename: string;
  title: string;
  body: string;
  uploaded_at: string;
};

type IdResponse = {
  id: string;
};

type UploadResponse = {
  article_ids: string[];
};

async function parseJson<T>(response: Response): Promise<T> {
  if (!response.ok) {
    let detail = `Request failed with ${response.status}`;
    try {
      const body = (await response.json()) as { detail?: unknown };
      if (typeof body.detail === "string") {
        detail = body.detail;
      }
    } catch {
      // Keep the status-based fallback when the response is not JSON.
    }
    throw new Error(detail);
  }
  return response.json() as Promise<T>;
}

export async function listCorpora(): Promise<CorpusSummary[]> {
  const response = await fetch(`${apiBaseUrl}/api/corpora`);
  return parseJson<CorpusSummary[]>(response);
}

export async function createCorpus(payload: {
  name: string;
  notes?: string;
}): Promise<IdResponse> {
  const response = await fetch(`${apiBaseUrl}/api/corpora`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify(payload),
  });
  return parseJson<IdResponse>(response);
}

export async function getCorpus(corpusId: string): Promise<CorpusDetail> {
  const response = await fetch(`${apiBaseUrl}/api/corpora/${corpusId}`);
  return parseJson<CorpusDetail>(response);
}

export async function deleteCorpus(corpusId: string): Promise<void> {
  const response = await fetch(`${apiBaseUrl}/api/corpora/${corpusId}`, {
    method: "DELETE",
  });
  if (!response.ok) {
    await parseJson<never>(response);
  }
}

export async function uploadArticles(
  corpusId: string,
  files: FileList,
): Promise<UploadResponse> {
  const formData = new FormData();
  Array.from(files).forEach((file) => formData.append("files", file));
  const response = await fetch(`${apiBaseUrl}/api/corpora/${corpusId}/articles`, {
    method: "POST",
    body: formData,
  });
  return parseJson<UploadResponse>(response);
}

export async function getArticle(articleId: string): Promise<ArticleDetail> {
  const response = await fetch(`${apiBaseUrl}/api/articles/${articleId}`);
  return parseJson<ArticleDetail>(response);
}
