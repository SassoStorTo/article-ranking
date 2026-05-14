from copy import deepcopy
from datetime import datetime
from typing import Any, Literal, Self
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from news_ranker.config import RankerConfig


class ApiSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class IdResponse(ApiSchema):
    id: UUID


class TimestampFields(ApiSchema):
    created_at: datetime


class HealthResponse(ApiSchema):
    ok: bool
    checks: dict[str, bool]


class ErrorDetail(ApiSchema):
    message: str


class ValidationErrorItem(ApiSchema):
    loc: list[str | int]
    msg: str
    type: str


class ErrorResponse(ApiSchema):
    detail: str | ErrorDetail | list[ValidationErrorItem]


class CorpusCreate(ApiSchema):
    name: str = Field(min_length=1, max_length=200)
    notes: str | None = None


DecompositionStatus = Literal["not_started", "decomposed"]


class StructuredArticleRecord(ApiSchema):
    id: UUID
    article_id: UUID
    llm_model: str
    prompt_version: str
    schema_version: str
    payload_json: dict[str, Any]
    created_at: datetime


class CorpusSummary(TimestampFields):
    id: UUID
    name: str
    notes: str | None
    article_count: int


class ArticleSummary(ApiSchema):
    id: UUID
    corpus_id: UUID
    filename: str
    title: str
    body_length: int
    decomposition_status: DecompositionStatus
    uploaded_at: datetime


class ArticleDetail(ApiSchema):
    id: UUID
    corpus_id: UUID
    filename: str
    title: str
    body: str
    decomposition_status: DecompositionStatus
    structured_article: StructuredArticleRecord | None
    uploaded_at: datetime


class ArticleUploadResponse(ApiSchema):
    article_ids: list[UUID]


class CorpusDetail(TimestampFields):
    id: UUID
    name: str
    notes: str | None
    articles: list[ArticleSummary]


ExecutionKindValue = Literal["rank", "select", "compare_profiles", "evaluate"]
ExecutionStatusValue = Literal["pending", "running", "succeeded", "failed"]
EvaluationHelperValue = Literal[
    "top_m_overlap",
    "rank_correlation",
    "component_score_table",
    "cluster_inspection_rows",
    "anonymized_user_study_bundle",
]
RankCorrelationMethodValue = Literal["kendall", "spearman"]
SelectionModeValue = Literal["top_score", "mmr"]
LinkageValue = Literal["average", "single"]
CoverageWeightingValue = Literal["consensus", "rarity"]


class ProfileWeights(ApiSchema):
    model_config = ConfigDict(from_attributes=True, extra="forbid")

    centrality: float = Field(ge=0.0)
    coverage: float = Field(ge=0.0)
    density: float = Field(ge=0.0)
    entity_coverage: float = Field(ge=0.0)

    @model_validator(mode="after")
    def validate_weight_sum(self) -> Self:
        total = self.centrality + self.coverage + self.density + self.entity_coverage
        if abs(total - 1.0) > 1e-6:
            msg = "profile weights must sum to 1.0"
            raise ValueError(msg)
        return self


class RankerConfigPayload(ApiSchema):
    model_config = ConfigDict(from_attributes=True, extra="forbid")

    similarity_threshold: float | None = Field(default=None, ge=-1.0, le=1.0)
    linkage: LinkageValue | None = None
    coverage_weighting: CoverageWeightingValue | None = None
    profiles: dict[str, ProfileWeights] | None = None
    top_m: int | None = Field(default=None, ge=1)
    selection_mode: SelectionModeValue | None = None
    selection_lambda: float | None = Field(default=None, ge=0.0, le=1.0)
    embedding_model_name: str | None = None
    llm_model_name: str | None = None
    prompt_version: str | None = None
    schema_version: str | None = None
    cache_dir: str | None = None

    @model_validator(mode="after")
    def validate_profiles(self) -> Self:
        if self.profiles is not None:
            if not self.profiles:
                msg = "profiles must not be empty"
                raise ValueError(msg)
            for profile_name in self.profiles:
                if not profile_name.strip():
                    msg = "profile name must be a non-empty string"
                    raise ValueError(msg)
        return self


class RankExecutionRequest(ApiSchema):
    corpus_id: UUID
    profile: str = "representative"
    config: RankerConfigPayload | None = None


class SelectExecutionRequest(ApiSchema):
    corpus_id: UUID
    m: int | None = None
    profile: str = "representative"
    config: RankerConfigPayload | None = None


class CompareProfilesExecutionRequest(ApiSchema):
    corpus_id: UUID
    profiles: list[str] | None = None
    config: RankerConfigPayload | None = None


class ReplayExecutionRequest(ApiSchema):
    corpus_id: UUID | None = None


class ExecutionAccepted(ApiSchema):
    execution_id: UUID
    status: ExecutionStatusValue


class ExecutionResultRecord(ApiSchema):
    id: UUID
    execution_id: UUID
    profile: str | None
    result_json: dict[str, Any]
    created_at: datetime


class EvaluationArtifactRecord(ApiSchema):
    id: UUID
    execution_id: UUID
    helper: EvaluationHelperValue
    params_json: dict[str, Any]
    payload_json: dict[str, Any]
    created_at: datetime


class ExecutionSummary(TimestampFields):
    id: UUID
    corpus_id: UUID
    corpus_name: str
    kind: ExecutionKindValue
    status: ExecutionStatusValue
    profiles: list[str]
    profile_summary: str
    m: int | None
    started_at: datetime | None
    finished_at: datetime | None
    error: str | None
    has_evaluation_artifacts: bool


class ExecutionDetail(ExecutionSummary):
    config_json: dict[str, Any]
    results: list[ExecutionResultRecord]
    evaluation_artifacts: list[EvaluationArtifactRecord]


class ExecutionComparisonMetadata(ExecutionSummary):
    config_json: dict[str, Any]


class ExecutionComparisonWarning(ApiSchema):
    code: str
    message: str
    left_section_key: str | None = None
    right_section_key: str | None = None


class ExecutionComparisonSection(ApiSchema):
    key: str
    label: str
    profile: str | None
    result_type: Literal["rank_result", "selection_result", "profile_comparison"]
    rank_result_json: dict[str, Any]
    result_json: dict[str, Any]
    entry_count: int
    selected_article_ids: list[str]
    cluster_count: int | None
    cluster_inspection_rows: list[dict[str, Any]]


class ExecutionComparisonMetrics(ApiSchema):
    top_m: int | None
    top_m_overlap: dict[str, Any] | None
    rank_correlation: dict[str, Any] | None
    left_cluster_count: int | None
    right_cluster_count: int | None
    shared_cluster_count: int | None
    shared_canonical_cluster_texts: list[str]


class ExecutionComparisonSectionPair(ApiSchema):
    key: str
    label: str
    left: ExecutionComparisonSection | None
    right: ExecutionComparisonSection | None
    metrics: ExecutionComparisonMetrics | None
    warnings: list[ExecutionComparisonWarning]


class ExecutionComparisonResponse(ApiSchema):
    left: ExecutionComparisonMetadata
    right: ExecutionComparisonMetadata
    section_pairs: list[ExecutionComparisonSectionPair]
    warnings: list[ExecutionComparisonWarning]


class TopMOverlapRequest(ApiSchema):
    other_execution_id: UUID
    m: int = Field(ge=1)


class RankCorrelationRequest(ApiSchema):
    other_execution_id: UUID
    method: RankCorrelationMethodValue = "kendall"


class ComponentTableRequest(ApiSchema):
    pass


class ClusterInspectionRequest(ApiSchema):
    rare_threshold: int = Field(default=1, ge=1)


class ArticleMaterialPayload(ApiSchema):
    model_config = ConfigDict(from_attributes=True, extra="forbid")

    title: str | None = None
    snippet: str | None = None
    summary: str | None = None


class UserStudyBundleRequest(ApiSchema):
    materials: dict[str, ArticleMaterialPayload] = Field(default_factory=dict)
    include_scores: bool = False


class FullEvaluationSuiteRequest(ApiSchema):
    baseline_execution_id: UUID
    m: int = Field(default=3, ge=1)
    method: RankCorrelationMethodValue = "kendall"
    rare_threshold: int = Field(default=1, ge=1)
    materials: dict[str, ArticleMaterialPayload] = Field(default_factory=dict)
    include_scores: bool = False


def normalize_ranker_config(
    payload: RankerConfigPayload | None,
    *,
    m: int | None = None,
) -> tuple[RankerConfig, dict[str, Any]]:
    values = payload.model_dump(exclude_none=True) if payload is not None else {}
    config = RankerConfig(**values)
    return config, ranker_config_json(config, m=m)


def ranker_config_from_json(config_json: dict[str, Any]) -> RankerConfig:
    payload_keys = set(RankerConfigPayload.model_fields)
    values = {
        key: deepcopy(value)
        for key, value in config_json.items()
        if key in payload_keys and value is not None
    }
    return RankerConfig(**values)


def ranker_config_json(config: RankerConfig, *, m: int | None = None) -> dict[str, Any]:
    return {
        "similarity_threshold": config.similarity_threshold,
        "linkage": config.linkage,
        "coverage_weighting": config.coverage_weighting,
        "profiles": {
            profile: dict(weights) for profile, weights in config.profiles.items()
        },
        "top_m": config.top_m,
        "selection_mode": config.selection_mode,
        "selection_lambda": config.selection_lambda,
        "embedding_model_name": config.embedding_model_name,
        "llm_model_name": config.llm_model_name,
        "prompt_version": config.prompt_version,
        "schema_version": config.schema_version,
        "cache_dir": str(config.cache_dir) if config.cache_dir is not None else None,
        "m": m,
    }
