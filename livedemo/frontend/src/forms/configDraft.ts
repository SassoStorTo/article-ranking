import {
  ExecutionDetail,
  ExecutionKind,
  RankerConfigPayload,
  defaultRankerConfig,
} from "../api/client";

export type RunMode = Exclude<ExecutionKind, "evaluate">;

export type ParameterDraft = {
  mode: RunMode;
  config?: RankerConfigPayload;
  profile?: string;
  profiles?: string[];
  m?: number | null;
};

export function normalizeConfigDraft(config?: RankerConfigPayload): RankerConfigPayload {
  const source = config as (RankerConfigPayload & { m?: number | null }) | undefined;
  const normalized = {
    ...defaultRankerConfig,
    similarity_threshold:
      source?.similarity_threshold ?? defaultRankerConfig.similarity_threshold,
    linkage: source?.linkage ?? defaultRankerConfig.linkage,
    coverage_weighting:
      source?.coverage_weighting ?? defaultRankerConfig.coverage_weighting,
    profiles: {
      ...defaultRankerConfig.profiles,
      ...(source?.profiles ?? {}),
    },
    top_m: source?.top_m ?? defaultRankerConfig.top_m,
    selection_mode: source?.selection_mode ?? defaultRankerConfig.selection_mode,
    selection_lambda:
      source?.selection_lambda ?? defaultRankerConfig.selection_lambda,
    embedding_model_name:
      source?.embedding_model_name ?? defaultRankerConfig.embedding_model_name,
    llm_model_name: source?.llm_model_name ?? defaultRankerConfig.llm_model_name,
    prompt_version: source?.prompt_version ?? defaultRankerConfig.prompt_version,
    schema_version: source?.schema_version ?? defaultRankerConfig.schema_version,
    cache_dir: source?.cache_dir ?? defaultRankerConfig.cache_dir,
  };
  return JSON.parse(JSON.stringify(normalized)) as RankerConfigPayload;
}

export function draftFromExecution(execution: ExecutionDetail): ParameterDraft {
  const config = normalizeConfigDraft(
    execution.config_json as RankerConfigPayload & { m?: number | null },
  );
  const storedM =
    typeof execution.config_json.m === "number"
      ? execution.config_json.m
      : execution.m;
  return {
    mode: execution.kind === "evaluate" ? "rank" : execution.kind,
    config,
    profile: execution.profiles[0] ?? "representative",
    profiles: execution.profiles.length
      ? execution.profiles
      : ["representative", "comprehensive", "concise"],
    m: storedM ?? config.top_m ?? 3,
  };
}
