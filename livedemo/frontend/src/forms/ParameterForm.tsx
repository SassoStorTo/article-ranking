import { useMutation } from "@tanstack/react-query";
import { Dispatch, FormEvent, SetStateAction, useMemo, useState } from "react";

import {
  ProfileWeights,
  RankerConfigPayload,
  defaultRankerConfig,
  runCompareExecution,
  runRankExecution,
  runSelectExecution,
} from "../api/client";
import { formatGroupName } from "../utils/format";
import {
  ParameterDraft,
  RunMode,
  normalizeConfigDraft,
} from "./configDraft";

export function ParameterForm({
  articleCount,
  corpusId,
  draft,
  onCancel,
  onSubmitted,
}: {
  articleCount: number;
  corpusId: string;
  draft: ParameterDraft;
  onCancel: () => void;
  onSubmitted: (executionId: string) => void;
}) {
  const initialConfig = useMemo(() => normalizeConfigDraft(draft.config), [draft]);

  if (draft.mode === "rank") {
    return (
      <RankParameterForm
        corpusId={corpusId}
        draft={draft}
        initialConfig={initialConfig}
        onCancel={onCancel}
        onSubmitted={onSubmitted}
      />
    );
  }

  if (draft.mode === "select") {
    return (
      <SelectParameterForm
        articleCount={articleCount}
        corpusId={corpusId}
        draft={draft}
        initialConfig={initialConfig}
        onCancel={onCancel}
        onSubmitted={onSubmitted}
      />
    );
  }

  return (
    <CompareProfilesParameterForm
      articleCount={articleCount}
      corpusId={corpusId}
      draft={draft}
      initialConfig={initialConfig}
      onCancel={onCancel}
      onSubmitted={onSubmitted}
    />
  );
}

function RankParameterForm({
  corpusId,
  draft,
  initialConfig,
  onCancel,
  onSubmitted,
}: {
  corpusId: string;
  draft: ParameterDraft;
  initialConfig: RankerConfigPayload;
  onCancel: () => void;
  onSubmitted: (executionId: string) => void;
}) {
  const [config, setConfig] = useState<RankerConfigPayload>(initialConfig);
  const profileNames = Object.keys(config.profiles ?? {});
  const [profile, setProfile] = useState(draft.profile ?? profileNames[0]);
  const [topM] = useState(draft.m ?? initialConfig.top_m ?? 3);
  const weightWarnings = profileWeightWarnings([profile], config);
  const canSubmit = Boolean(profile) && weightWarnings.length === 0 && topM >= 1;
  const mutation = useMutation({
    mutationFn: () =>
      runRankExecution({
        corpus_id: corpusId,
        profile,
        config: {
          ...config,
          top_m: topM,
        },
      }),
    onSuccess: ({ execution_id }) => onSubmitted(execution_id),
  });

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (canSubmit) {
      mutation.mutate();
    }
  }

  function updateRankConfig<K extends keyof RankerConfigPayload>(
    key: K,
    value: RankerConfigPayload[K],
  ) {
    setConfig((current) => ({ ...current, [key]: value }));
  }

  return (
    <form className="parameter-form" onSubmit={handleSubmit}>
      <ParameterFormHeader
        mode="rank"
        onCancel={onCancel}
        subtitle="Locked execution"
      />

      <ProfileWeightsSection
        config={config}
        onSelectProfile={setProfile}
        onUpdateWeight={(profileName, component, value) =>
          updateProfileWeight(setConfig, profileName, component, value)
        }
        profileOptions={profileNames}
        profiles={[profile]}
        selectedProfile={profile}
      />

      <RankingParametersSection
        config={config}
        onUpdateConfig={updateRankConfig}
      />

      <MetadataSection config={config} />

      <ParameterErrors errors={weightWarnings} mutationError={mutation.error} />
      <div className="form-actions">
        <button disabled={mutation.isPending || !canSubmit} type="submit">
          {mutation.isPending ? "Starting" : "Run Rank"}
        </button>
      </div>
    </form>
  );
}

function SelectParameterForm({
  articleCount,
  corpusId,
  draft,
  initialConfig,
  onCancel,
  onSubmitted,
}: {
  articleCount: number;
  corpusId: string;
  draft: ParameterDraft;
  initialConfig: RankerConfigPayload;
  onCancel: () => void;
  onSubmitted: (executionId: string) => void;
}) {
  const [config, setConfig] = useState<RankerConfigPayload>(initialConfig);
  const [selectionPreset, setSelectionPreset] = useState("custom");
  const profileNames = Object.keys(config.profiles ?? {});
  const [profile, setProfile] = useState(draft.profile ?? profileNames[0]);
  const [topM, setTopM] = useState(
    draft.m ?? config.top_m ?? Math.min(3, Math.max(1, articleCount)),
  );
  const weightWarnings = profileWeightWarnings([profile], config);
  const canSubmit =
    articleCount > 0 && Boolean(profile) && weightWarnings.length === 0 && topM >= 1;
  const mutation = useMutation({
    mutationFn: () =>
      runSelectExecution({
        corpus_id: corpusId,
        m: topM,
        profile,
        config: {
          ...config,
          top_m: topM,
        },
      }),
    onSuccess: ({ execution_id }) => onSubmitted(execution_id),
  });

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (canSubmit) {
      mutation.mutate();
    }
  }

  function loadSelectionPreset(value: string) {
    setSelectionPreset(value);
    if (value !== "defaults") {
      return;
    }
    const defaultTopM = defaultRankerConfig.top_m ?? 3;
    setTopM(Math.min(defaultTopM, Math.max(1, articleCount)));
    setConfig((current) => ({
      ...current,
      selection_lambda: defaultRankerConfig.selection_lambda,
      selection_mode: defaultRankerConfig.selection_mode,
      top_m: defaultTopM,
    }));
  }

  function updateSelectionConfig<K extends keyof RankerConfigPayload>(
    key: K,
    value: RankerConfigPayload[K],
  ) {
    setSelectionPreset("custom");
    setConfig((current) => ({ ...current, [key]: value }));
  }

  function updateRankConfig<K extends RankingParameterKey>(
    key: K,
    value: RankerConfigPayload[K],
  ) {
    setConfig((current) => ({ ...current, [key]: value }));
  }

  return (
    <form className="parameter-form" onSubmit={handleSubmit}>
      <ParameterFormHeader
        mode="select"
        onCancel={onCancel}
        subtitle="Locked execution"
      />

      <fieldset>
        <legend>Selection</legend>
        <div className="parameter-grid">
          <label>
            Defaults
            <select
              onChange={(event) => loadSelectionPreset(event.target.value)}
              value={selectionPreset}
            >
              <option value="custom">Custom values</option>
              <option value="defaults">Load default values</option>
            </select>
          </label>
          <label>
            Top M
            <input
              min="1"
              onChange={(event) => {
                setSelectionPreset("custom");
                setTopM(Number(event.target.value));
              }}
              step="1"
              type="number"
              value={topM}
            />
          </label>
          <label>
            Selection mode
            <select
              onChange={(event) =>
                updateSelectionConfig(
                  "selection_mode",
                  event.target.value as "top_score" | "mmr",
                )
              }
              value={config.selection_mode ?? "top_score"}
            >
              <option value="top_score">top_score</option>
              <option value="mmr">mmr</option>
            </select>
          </label>
          <label>
            Selection lambda
            <input
              max="1"
              min="0"
              onChange={(event) =>
                updateSelectionConfig(
                  "selection_lambda",
                  Number(event.target.value),
                )
              }
              step="0.05"
              type="number"
              value={config.selection_lambda ?? 0.8}
            />
          </label>
        </div>
      </fieldset>

      <ProfileWeightsSection
        config={config}
        onSelectProfile={setProfile}
        onUpdateWeight={(profileName, component, value) =>
          updateProfileWeight(setConfig, profileName, component, value)
        }
        profileOptions={profileNames}
        profiles={[profile]}
        selectedProfile={profile}
      />

      <RankingParametersSection
        config={config}
        onUpdateConfig={updateRankConfig}
      />

      <MetadataSection config={config} />

      <ParameterErrors errors={weightWarnings} mutationError={mutation.error} />
      <div className="form-actions">
        <button disabled={mutation.isPending || !canSubmit} type="submit">
          {mutation.isPending ? "Starting" : "Run Select"}
        </button>
      </div>
    </form>
  );
}

function CompareProfilesParameterForm({
  articleCount,
  corpusId,
  draft,
  initialConfig,
  onCancel,
  onSubmitted,
}: {
  articleCount: number;
  corpusId: string;
  draft: ParameterDraft;
  initialConfig: RankerConfigPayload;
  onCancel: () => void;
  onSubmitted: (executionId: string) => void;
}) {
  const [config, setConfig] = useState<RankerConfigPayload>(initialConfig);
  const profileNames = Object.keys(config.profiles ?? {});
  const [profiles, setProfiles] = useState<string[]>(
    draft.profiles ?? profileNames.slice(0, 3),
  );
  const mutation = useMutation({
    mutationFn: () =>
      runCompareExecution({
        corpus_id: corpusId,
        profiles,
        config,
      }),
    onSuccess: ({ execution_id }) => onSubmitted(execution_id),
  });
  const weightWarnings = profileWeightWarnings(profiles, config);
  const canSubmit =
    articleCount > 0 && profiles.length > 0 && weightWarnings.length === 0;

  function toggleCompareProfile(profileName: string) {
    setProfiles((current) =>
      current.includes(profileName)
        ? current.filter((item) => item !== profileName)
        : [...current, profileName],
    );
  }

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (canSubmit) {
      mutation.mutate();
    }
  }

  function updateRankConfig<K extends RankingParameterKey>(
    key: K,
    value: RankerConfigPayload[K],
  ) {
    setConfig((current) => ({ ...current, [key]: value }));
  }

  return (
    <form className="parameter-form" onSubmit={handleSubmit}>
      <ParameterFormHeader
        mode="compare_profiles"
        onCancel={onCancel}
        subtitle="Locked execution"
      />

      <fieldset>
        <legend>Profiles</legend>
        <div className="checkbox-row">
          {profileNames.map((name) => {
            return (
              <label key={name}>
                <input
                  checked={profiles.includes(name)}
                  onChange={() => toggleCompareProfile(name)}
                  type="checkbox"
                />
                {name}
              </label>
            );
          })}
        </div>
      </fieldset>

      <ProfileWeightsSection
        config={config}
        onUpdateWeight={(profileName, component, value) =>
          updateProfileWeight(setConfig, profileName, component, value)
        }
        profileOptions={profileNames}
        profiles={profiles}
      />

      <RankingParametersSection
        config={config}
        onUpdateConfig={updateRankConfig}
      />

      <MetadataSection config={config} />

      <ParameterErrors errors={weightWarnings} mutationError={mutation.error} />
      <div className="form-actions">
        <button disabled={mutation.isPending || !canSubmit} type="submit">
          {mutation.isPending ? "Starting" : "Compare Profiles"}
        </button>
      </div>
    </form>
  );
}

function ParameterFormHeader({
  mode,
  onCancel,
  subtitle,
}: {
  mode: RunMode;
  onCancel: () => void;
  subtitle: string;
}) {
  return (
    <header>
      <div>
        <p className="eyebrow">{subtitle}</p>
        <h3>{formatGroupName(mode)}</h3>
      </div>
      <button onClick={onCancel} type="button">
        Close
      </button>
    </header>
  );
}

const profileWeightComponents = [
  "centrality",
  "coverage",
  "density",
  "entity_coverage",
] as const satisfies readonly (keyof ProfileWeights)[];

const metadataFields = [
  "llm_model_name",
  "prompt_version",
  "schema_version",
  "embedding_model_name",
] as const satisfies readonly (keyof RankerConfigPayload)[];

type RankingParameterKey =
  | "similarity_threshold"
  | "linkage"
  | "coverage_weighting";

function RankingParametersSection({
  config,
  onUpdateConfig,
}: {
  config: RankerConfigPayload;
  onUpdateConfig: <K extends RankingParameterKey>(
    key: K,
    value: RankerConfigPayload[K],
  ) => void;
}) {
  return (
    <fieldset>
      <legend>Ranking Parameters</legend>
      <div className="parameter-grid">
        <label>
          Similarity
          <input
            max="1"
            min="-1"
            onChange={(event) =>
              onUpdateConfig(
                "similarity_threshold",
                Number(event.target.value),
              )
            }
            step="0.01"
            type="number"
            value={config.similarity_threshold ?? 0.85}
          />
        </label>
        <label>
          Linkage
          <select
            onChange={(event) =>
              onUpdateConfig(
                "linkage",
                event.target.value as "average" | "single",
              )
            }
            value={config.linkage ?? "average"}
          >
            <option value="average">average</option>
            <option value="single">single</option>
          </select>
        </label>
        <label>
          Coverage
          <select
            onChange={(event) =>
              onUpdateConfig(
                "coverage_weighting",
                event.target.value as "consensus" | "rarity",
              )
            }
            value={config.coverage_weighting ?? "consensus"}
          >
            <option value="consensus">consensus</option>
            <option value="rarity">rarity</option>
          </select>
        </label>
      </div>
    </fieldset>
  );
}

function MetadataSection({ config }: { config: RankerConfigPayload }) {
  return (
    <fieldset>
      <legend>Metadata</legend>
      <div className="parameter-grid">
        {metadataFields.map((field) => (
          <label key={field}>
            {formatGroupName(field)}
            <input readOnly value={String(config[field] ?? "")} />
          </label>
        ))}
      </div>
    </fieldset>
  );
}

function ProfileWeightsSection({
  config,
  onSelectProfile,
  onUpdateWeight,
  profileOptions,
  profiles,
  selectedProfile,
}: {
  config: RankerConfigPayload;
  onSelectProfile?: (profile: string) => void;
  onUpdateWeight: (
    profileName: string,
    component: keyof ProfileWeights,
    value: number,
  ) => void;
  profileOptions: string[];
  profiles: string[];
  selectedProfile?: string;
}) {
  return (
    <fieldset>
      <legend>Profile Weights</legend>
      {selectedProfile && onSelectProfile ? (
        <label>
          Profile
          <select
            onChange={(event) => onSelectProfile(event.target.value)}
            value={selectedProfile}
          >
            {profileOptions.map((name) => (
              <option key={name} value={name}>
                {name}
              </option>
            ))}
          </select>
        </label>
      ) : null}
      <div className="weights-grid">
        {profiles.map((name) => {
          const weights = config.profiles?.[name];
          if (!weights) {
            return null;
          }
          return (
            <div className="weight-group" key={name}>
              <strong>{name}</strong>
              {profileWeightComponents.map((component) => (
                <label key={component}>
                  {formatGroupName(component)}
                  <input
                    min="0"
                    onChange={(event) =>
                      onUpdateWeight(name, component, Number(event.target.value))
                    }
                    step="0.05"
                    type="number"
                    value={weights[component]}
                  />
                </label>
              ))}
            </div>
          );
        })}
      </div>
    </fieldset>
  );
}

function ParameterErrors({
  errors,
  mutationError,
}: {
  errors: string[];
  mutationError: Error | null;
}) {
  return (
    <>
      {errors.map((warning) => (
        <p className="error-line" key={warning}>
          {warning}
        </p>
      ))}
      {mutationError && <p className="error-line">{mutationError.message}</p>}
    </>
  );
}

function profileWeightWarnings(
  profiles: string[],
  config: RankerConfigPayload,
): string[] {
  return profiles
    .map((name) => {
      const weights = config.profiles?.[name];
      if (!weights) {
        return `${name} weights are missing`;
      }
      const total =
        weights.centrality +
        weights.coverage +
        weights.density +
        weights.entity_coverage;
      return Math.abs(total - 1) > 0.000001
        ? `${name} weights total ${total.toFixed(3)}`
        : null;
    })
    .filter((item): item is string => item !== null);
}

function updateProfileWeight(
  setConfig: Dispatch<SetStateAction<RankerConfigPayload>>,
  profileName: string,
  component: keyof ProfileWeights,
  value: number,
) {
  setConfig((current) => ({
    ...current,
    profiles: {
      ...(current.profiles ?? {}),
      [profileName]: {
        ...(current.profiles?.[profileName] ?? {
          centrality: 0,
          coverage: 0,
          density: 0,
          entity_coverage: 0,
        }),
        [component]: value,
      },
    },
  }));
}
