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
  decomposition_status: "not_started" | "decomposed";
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
  decomposition_status: "not_started" | "decomposed";
  structured_article: StructuredArticleRecord | null;
  uploaded_at: string;
};

export type StructuredArticleRecord = {
  id: string;
  article_id: string;
  llm_model: string;
  prompt_version: string;
  schema_version: string;
  payload_json: StructuredArticlePayload;
  created_at: string;
};

export type StructuredArticlePayload = {
  article_id?: string | null;
  headline_neutral: string;
  topic: string;
  entities: {
    people: StructuredEntity[];
    organizations: StructuredEntity[];
    locations: StructuredEntity[];
  };
  events: StructuredEvent[];
  claims: StructuredClaim[];
  context: string[];
};

export type StructuredEntity = {
  name: string;
  role: string | null;
};

export type StructuredEvent = {
  id: string;
  when: string | null;
  who: string[];
  what: string;
  where: string | null;
  why: string | null;
  how: string | null;
  depends_on: string[];
};

export type StructuredClaim = {
  id: string;
  statement: string;
  type: "fact" | "quote" | "estimate" | "prediction";
  attributed_to: string | null;
};

export type ExecutionStatus = "pending" | "running" | "succeeded" | "failed";

export type ExecutionKind = "rank" | "select" | "compare_profiles" | "evaluate";

export type LinkageValue = "average" | "single";

export type CoverageWeightingValue = "consensus" | "rarity";

export type SelectionModeValue = "top_score" | "mmr";

export type ProfileWeights = {
  centrality: number;
  coverage: number;
  density: number;
  entity_coverage: number;
};

export type RankerConfigPayload = {
  similarity_threshold?: number | null;
  linkage?: LinkageValue | null;
  coverage_weighting?: CoverageWeightingValue | null;
  profiles?: Record<string, ProfileWeights> | null;
  top_m?: number | null;
  selection_mode?: SelectionModeValue | null;
  selection_lambda?: number | null;
  embedding_model_name?: string | null;
  llm_model_name?: string | null;
  prompt_version?: string | null;
  schema_version?: string | null;
  cache_dir?: string | null;
};

export const defaultRankerConfig: Required<
  Omit<RankerConfigPayload, "cache_dir">
> & {
  cache_dir: string | null;
} = {
  similarity_threshold: 0.85,
  linkage: "average",
  coverage_weighting: "consensus",
  profiles: {
    representative: {
      centrality: 0.4,
      coverage: 0.5,
      density: 0.1,
      entity_coverage: 0,
    },
    comprehensive: {
      centrality: 0.2,
      coverage: 0.7,
      density: 0.1,
      entity_coverage: 0,
    },
    concise: {
      centrality: 0.2,
      coverage: 0.4,
      density: 0.4,
      entity_coverage: 0,
    },
  },
  top_m: 3,
  selection_mode: "top_score",
  selection_lambda: 0.8,
  embedding_model_name: "all-MiniLM-L6-v2",
  llm_model_name: "mistral-small-latest",
  prompt_version: "v1",
  schema_version: "v1",
  cache_dir: null,
};

export type RankingEntry = {
  article_id: string;
  rank: number;
  score: number;
  components: Record<string, number>;
};

export type RankResultPayload = {
  __type__: "rank_result";
  profile: string;
  entries: RankingEntry[];
  diagnostics: Record<string, unknown>;
};

export type SelectionResultPayload = {
  __type__: "selection_result";
  profile: string;
  m: number;
  selected: RankingEntry[];
  ranking: RankResultPayload;
};

export type ProfileComparisonPayload = {
  __type__: "profile_comparison";
  rankings: Record<string, RankResultPayload>;
};

export type ExecutionResultJson =
  | RankResultPayload
  | SelectionResultPayload
  | ProfileComparisonPayload;

export type ExecutionResultRecord = {
  id: string;
  execution_id: string;
  profile: string | null;
  result_json: ExecutionResultJson;
  created_at: string;
};

export type ExecutionDetail = {
  id: string;
  corpus_id: string;
  kind: ExecutionKind;
  status: ExecutionStatus;
  profiles: string[];
  m: number | null;
  started_at: string | null;
  finished_at: string | null;
  error: string | null;
  created_at: string;
  config_json: Record<string, unknown>;
  results: ExecutionResultRecord[];
};

export type ExecutionAccepted = {
  execution_id: string;
  status: ExecutionStatus;
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

export async function decomposeArticle(
  articleId: string,
): Promise<StructuredArticleRecord> {
  const response = await fetch(`${apiBaseUrl}/api/articles/${articleId}/decompose`, {
    method: "POST",
  });
  return parseJson<StructuredArticleRecord>(response);
}

export async function runRankExecution(payload: {
  corpus_id: string;
  profile: string;
  config: RankerConfigPayload;
}): Promise<ExecutionAccepted> {
  const response = await fetch(`${apiBaseUrl}/api/executions/rank`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify(payload),
  });
  return parseJson<ExecutionAccepted>(response);
}

export async function runSelectExecution(payload: {
  corpus_id: string;
  m: number;
  profile: string;
  config: RankerConfigPayload;
}): Promise<ExecutionAccepted> {
  const response = await fetch(`${apiBaseUrl}/api/executions/select`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify(payload),
  });
  return parseJson<ExecutionAccepted>(response);
}

export async function runCompareExecution(payload: {
  corpus_id: string;
  profiles: string[];
  config: RankerConfigPayload;
}): Promise<ExecutionAccepted> {
  const response = await fetch(`${apiBaseUrl}/api/executions/compare`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify(payload),
  });
  return parseJson<ExecutionAccepted>(response);
}

export async function getExecution(
  executionId: string,
): Promise<ExecutionDetail> {
  const response = await fetch(`${apiBaseUrl}/api/executions/${executionId}`);
  return parseJson<ExecutionDetail>(response);
}
