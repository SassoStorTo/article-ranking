const theme = {
  bg: "#0a0c12",
  surface: "#111420",
  border: "#1e2235",
  accent1: "#4f9cf9",   // blue
  accent2: "#f97b4f",   // orange
  accent3: "#63e6be",   // teal
  accent4: "#f9c84f",   // gold
  accent5: "#c084fc",   // purple
  text: "#e8eaf0",
  muted: "#6b7280",
  dim: "#374151",
};

const style = `
  @import url('https://fonts.googleapis.com/css2?family=DM+Mono:ital,wght@0,300;0,400;0,500;1,400&family=Syne:wght@400;600;700;800&display=swap');

  * { box-sizing: border-box; margin: 0; padding: 0; }

  body {
    background: ${theme.bg};
    color: ${theme.text};
    font-family: 'Syne', sans-serif;
  }

  .root {
    min-height: 100vh;
    background: ${theme.bg};
    padding: 40px 24px 60px;
    max-width: 960px;
    margin: 0 auto;
  }

  /* HEADER */
  .header {
    margin-bottom: 52px;
    text-align: center;
    position: relative;
  }
  .header-eyebrow {
    font-family: 'DM Mono', monospace;
    font-size: 11px;
    letter-spacing: 0.2em;
    color: ${theme.accent1};
    text-transform: uppercase;
    margin-bottom: 12px;
  }
  .header-title {
    font-size: clamp(28px, 5vw, 48px);
    font-weight: 800;
    line-height: 1.05;
    letter-spacing: -0.02em;
    color: ${theme.text};
  }
  .header-title span { color: ${theme.accent1}; }
  .header-sub {
    margin-top: 14px;
    color: ${theme.muted};
    font-size: 14px;
    font-weight: 400;
    max-width: 520px;
    margin-left: auto;
    margin-right: auto;
    line-height: 1.6;
    font-family: 'DM Mono', monospace;
  }
  .header-line {
    width: 60px;
    height: 2px;
    background: ${theme.accent1};
    margin: 20px auto 0;
  }

  /* SECTION TITLES */
  .section-title {
    font-family: 'DM Mono', monospace;
    font-size: 10px;
    letter-spacing: 0.22em;
    text-transform: uppercase;
    color: ${theme.muted};
    margin-bottom: 20px;
    display: flex;
    align-items: center;
    gap: 10px;
  }
  .section-title::after {
    content: '';
    flex: 1;
    height: 1px;
    background: ${theme.border};
  }

  /* PIPELINE */
  .pipeline {
    display: flex;
    flex-direction: column;
    gap: 0;
    margin-bottom: 52px;
  }
  .pipe-step {
    display: grid;
    grid-template-columns: 40px 1fr;
    gap: 0 16px;
    align-items: start;
  }
  .pipe-connector {
    display: flex;
    flex-direction: column;
    align-items: center;
  }
  .pipe-num {
    width: 36px;
    height: 36px;
    border-radius: 50%;
    background: ${theme.surface};
    border: 2px solid ${theme.border};
    display: flex;
    align-items: center;
    justify-content: center;
    font-family: 'DM Mono', monospace;
    font-size: 12px;
    font-weight: 500;
    color: ${theme.accent1};
    flex-shrink: 0;
    position: relative;
    z-index: 1;
  }
  .pipe-line {
    width: 2px;
    flex: 1;
    min-height: 20px;
    background: linear-gradient(to bottom, ${theme.accent1}40, ${theme.border});
    margin: 2px 0;
  }
  .pipe-content {
    background: ${theme.surface};
    border: 1px solid ${theme.border};
    border-radius: 10px;
    padding: 16px 18px;
    margin-bottom: 8px;
    position: relative;
    overflow: hidden;
  }
  .pipe-content::before {
    content: '';
    position: absolute;
    top: 0; left: 0; right: 0;
    height: 2px;
  }
  .pipe-content.c1::before { background: ${theme.accent1}; }
  .pipe-content.c2::before { background: ${theme.accent3}; }
  .pipe-content.c3::before { background: ${theme.accent2}; }
  .pipe-content.c4::before { background: ${theme.accent4}; }
  .pipe-content.c5::before { background: ${theme.accent5}; }
  .pipe-content.c6::before { background: ${theme.accent1}; }

  .pipe-header {
    display: flex;
    align-items: center;
    gap: 10px;
    margin-bottom: 8px;
  }
  .pipe-icon {
    font-size: 16px;
  }
  .pipe-name {
    font-weight: 700;
    font-size: 14px;
    letter-spacing: 0.01em;
  }
  .pipe-name.c1 { color: ${theme.accent1}; }
  .pipe-name.c2 { color: ${theme.accent3}; }
  .pipe-name.c3 { color: ${theme.accent2}; }
  .pipe-name.c4 { color: ${theme.accent4}; }
  .pipe-name.c5 { color: ${theme.accent5}; }
  .pipe-name.c6 { color: ${theme.accent1}; }

  .pipe-desc {
    font-size: 13px;
    color: ${theme.muted};
    line-height: 1.55;
    font-family: 'DM Mono', monospace;
    font-weight: 300;
  }
  .pipe-tag {
    display: inline-block;
    font-family: 'DM Mono', monospace;
    font-size: 10px;
    padding: 2px 8px;
    border-radius: 4px;
    margin-top: 8px;
    background: #1a1f30;
    color: ${theme.muted};
    border: 1px solid ${theme.border};
  }

  /* OUTPUT ROW */
  .pipe-output {
    display: flex;
    gap: 6px;
    flex-wrap: wrap;
    margin-top: 10px;
  }
  .pipe-badge {
    font-family: 'DM Mono', monospace;
    font-size: 10px;
    padding: 3px 8px;
    border-radius: 4px;
    background: #1a2030;
    border: 1px solid;
  }

  /* COMPONENTS */
  .components-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
    gap: 16px;
    margin-bottom: 52px;
  }
  .comp-card {
    background: ${theme.surface};
    border: 1px solid ${theme.border};
    border-radius: 12px;
    padding: 20px;
    position: relative;
    overflow: hidden;
  }
  .comp-card::after {
    content: '';
    position: absolute;
    bottom: 0; right: 0;
    width: 80px; height: 80px;
    border-radius: 50%;
    opacity: 0.04;
  }
  .comp-card.cent::after { background: ${theme.accent1}; }
  .comp-card.cov::after { background: ${theme.accent2}; }
  .comp-card.dens::after { background: ${theme.accent3}; }

  .comp-accent {
    width: 28px; height: 3px;
    border-radius: 2px;
    margin-bottom: 12px;
  }
  .comp-card.cent .comp-accent { background: ${theme.accent1}; }
  .comp-card.cov .comp-accent { background: ${theme.accent2}; }
  .comp-card.dens .comp-accent { background: ${theme.accent3}; }

  .comp-name {
    font-size: 16px;
    font-weight: 700;
    margin-bottom: 6px;
    letter-spacing: -0.01em;
  }
  .comp-card.cent .comp-name { color: ${theme.accent1}; }
  .comp-card.cov .comp-name { color: ${theme.accent2}; }
  .comp-card.dens .comp-name { color: ${theme.accent3}; }

  .comp-question {
    font-size: 11px;
    font-family: 'DM Mono', monospace;
    color: ${theme.muted};
    margin-bottom: 12px;
    font-style: italic;
  }
  .comp-body {
    font-size: 12.5px;
    color: #9ca3af;
    line-height: 1.6;
    font-family: 'DM Mono', monospace;
    font-weight: 300;
  }
  .comp-formula {
    margin-top: 14px;
    background: #0d1018;
    border: 1px solid ${theme.border};
    border-radius: 6px;
    padding: 10px 12px;
    font-family: 'DM Mono', monospace;
    font-size: 11px;
    color: ${theme.dim};
  }
  .comp-formula span { color: ${theme.text}; }
  .comp-weight {
    margin-top: 12px;
    display: flex;
    align-items: center;
    gap: 8px;
  }
  .comp-weight-bar {
    flex: 1;
    height: 4px;
    background: ${theme.border};
    border-radius: 2px;
    overflow: hidden;
  }
  .comp-weight-fill {
    height: 100%;
    border-radius: 2px;
    transition: width 0.6s ease;
  }
  .comp-weight-label {
    font-family: 'DM Mono', monospace;
    font-size: 11px;
    color: ${theme.muted};
    width: 32px;
    text-align: right;
  }

  /* SCORE FORMULA BLOCK */
  .score-block {
    background: ${theme.surface};
    border: 1px solid ${theme.border};
    border-radius: 12px;
    padding: 28px 28px;
    margin-bottom: 52px;
    position: relative;
    overflow: hidden;
  }
  .score-block::before {
    content: '';
    position: absolute;
    top: 0; left: 0; right: 0;
    height: 2px;
    background: linear-gradient(to right, ${theme.accent1}, ${theme.accent2}, ${theme.accent3});
  }
  .score-equation {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 6px;
    font-family: 'DM Mono', monospace;
    font-size: 13px;
    margin: 16px 0 20px;
  }
  .eq-label {
    color: ${theme.text};
    font-weight: 500;
  }
  .eq-equals { color: ${theme.muted}; margin: 0 4px; }
  .eq-term {
    display: flex;
    align-items: center;
    gap: 2px;
    background: #0d1018;
    border: 1px solid ${theme.border};
    border-radius: 6px;
    padding: 6px 10px;
  }
  .eq-alpha { color: ${theme.accent1}; }
  .eq-beta  { color: ${theme.accent2}; }
  .eq-gamma { color: ${theme.accent3}; }
  .eq-dot   { color: ${theme.muted}; margin: 0 3px; }
  .eq-plus  { color: ${theme.muted}; padding: 0 2px; }

  .score-legend {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
    gap: 10px;
    margin-top: 8px;
  }
  .legend-item {
    display: flex;
    align-items: flex-start;
    gap: 8px;
    font-family: 'DM Mono', monospace;
    font-size: 11px;
  }
  .legend-dot {
    width: 8px; height: 8px;
    border-radius: 50%;
    flex-shrink: 0;
    margin-top: 3px;
  }
  .legend-key { color: ${theme.muted}; }
  .legend-val { color: #9ca3af; margin-top: 2px; }

  /* NORMALIZATION */
  .norm-block {
    background: ${theme.surface};
    border: 1px solid ${theme.border};
    border-radius: 12px;
    padding: 24px 24px;
    margin-bottom: 52px;
  }
  .norm-visual {
    display: grid;
    grid-template-columns: 1fr auto 1fr;
    gap: 16px;
    align-items: center;
    margin-top: 16px;
  }
  .norm-before, .norm-after {
    background: #0d1018;
    border: 1px solid ${theme.border};
    border-radius: 8px;
    padding: 14px;
  }
  .norm-label {
    font-family: 'DM Mono', monospace;
    font-size: 10px;
    color: ${theme.muted};
    text-transform: uppercase;
    letter-spacing: 0.1em;
    margin-bottom: 10px;
  }
  .norm-bar-row {
    display: flex;
    align-items: center;
    gap: 8px;
    margin-bottom: 6px;
  }
  .norm-bar-name {
    font-family: 'DM Mono', monospace;
    font-size: 10px;
    color: ${theme.muted};
    width: 60px;
    flex-shrink: 0;
  }
  .norm-bar-track {
    flex: 1;
    height: 6px;
    background: ${theme.border};
    border-radius: 3px;
    overflow: hidden;
  }
  .norm-bar-fill {
    height: 100%;
    border-radius: 3px;
  }
  .norm-val {
    font-family: 'DM Mono', monospace;
    font-size: 10px;
    color: ${theme.dim};
    width: 36px;
    text-align: right;
  }
  .norm-arrow {
    font-size: 20px;
    color: ${theme.muted};
    text-align: center;
  }
  .norm-why {
    margin-top: 14px;
    font-family: 'DM Mono', monospace;
    font-size: 12px;
    color: ${theme.muted};
    line-height: 1.6;
    font-weight: 300;
  }
  .norm-why strong { color: ${theme.text}; font-weight: 500; }

  /* MMR */
  .mmr-block {
    background: ${theme.surface};
    border: 1px solid ${theme.border};
    border-radius: 12px;
    padding: 24px;
    margin-bottom: 52px;
  }
  .mmr-steps {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
    gap: 12px;
    margin-top: 16px;
  }
  .mmr-step {
    border: 1px solid ${theme.border};
    border-radius: 8px;
    padding: 14px;
    background: #0d1018;
    position: relative;
  }
  .mmr-step-num {
    font-family: 'DM Mono', monospace;
    font-size: 10px;
    color: ${theme.accent5};
    letter-spacing: 0.12em;
    text-transform: uppercase;
    margin-bottom: 8px;
  }
  .mmr-step-title {
    font-size: 13px;
    font-weight: 600;
    color: ${theme.text};
    margin-bottom: 6px;
  }
  .mmr-step-body {
    font-family: 'DM Mono', monospace;
    font-size: 11px;
    color: ${theme.muted};
    line-height: 1.55;
    font-weight: 300;
  }
  .mmr-formula-row {
    margin-top: 18px;
    background: #0d1018;
    border: 1px solid ${theme.border};
    border-radius: 8px;
    padding: 14px 16px;
    font-family: 'DM Mono', monospace;
    font-size: 11.5px;
    line-height: 1.7;
    color: ${theme.muted};
  }
  .mmr-formula-row .hl { color: ${theme.accent5}; }
  .mmr-formula-row .hl2 { color: ${theme.accent4}; }
  .mmr-formula-row .hl3 { color: ${theme.accent3}; }

  .lambda-vis {
    margin-top: 16px;
    display: flex;
    align-items: center;
    gap: 12px;
    font-family: 'DM Mono', monospace;
    font-size: 11px;
    color: ${theme.muted};
  }
  .lambda-track {
    flex: 1;
    height: 8px;
    border-radius: 4px;
    background: linear-gradient(to right, ${theme.accent3}80, ${theme.accent5}80);
    position: relative;
  }
  .lambda-thumb {
    position: absolute;
    top: -4px;
    width: 16px; height: 16px;
    border-radius: 50%;
    background: ${theme.text};
    border: 2px solid ${theme.accent5};
    left: calc(80% - 8px);
  }
  .lambda-labels {
    display: flex;
    justify-content: space-between;
    margin-top: 4px;
    font-family: 'DM Mono', monospace;
    font-size: 9px;
    color: ${theme.muted};
  }

  /* PROFILES */
  .profiles-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
    gap: 12px;
    margin-bottom: 52px;
  }
  .profile-card {
    border: 1px solid ${theme.border};
    border-radius: 10px;
    padding: 16px;
    background: ${theme.surface};
  }
  .profile-name {
    font-weight: 700;
    font-size: 13px;
    margin-bottom: 12px;
    text-transform: uppercase;
    letter-spacing: 0.06em;
  }
  .profile-bar-row {
    margin-bottom: 7px;
  }
  .profile-bar-label {
    display: flex;
    justify-content: space-between;
    font-family: 'DM Mono', monospace;
    font-size: 10px;
    color: ${theme.muted};
    margin-bottom: 3px;
  }
  .profile-bar-track {
    height: 5px;
    background: ${theme.border};
    border-radius: 3px;
    overflow: hidden;
  }
  .profile-bar-fill {
    height: 100%;
    border-radius: 3px;
    transition: width 0.4s ease;
  }

  /* FOOTER */
  .footer {
    text-align: center;
    font-family: 'DM Mono', monospace;
    font-size: 10px;
    color: ${theme.dim};
    letter-spacing: 0.1em;
    padding-top: 20px;
    border-top: 1px solid ${theme.border};
    text-transform: uppercase;
  }
`;

const pipelineSteps = [
  {
    c: "c1", icon: "◈", name: "DECOMPOSITION",
    desc: "Each article is sent to an LLM with a strict prompt. The output is a structured document: a list of atomic events and claims, written neutrally and stripped of style. This isolates content from prose.",
    badge: "StructuredArticle", badgeColor: theme.accent1,
    tags: ["LLM → JSON", "cached", "retry on fail"],
  },
  {
    c: "c2", icon: "⟨⟩", name: "FACT EMBEDDINGS",
    desc: "Each extracted event or claim becomes a numeric vector. Semantically similar sentences land near each other in vector space, regardless of how they are written.",
    badge: "ℝᵈ per fact",
    tags: ["sentence-transformers", "batch API", "disk cache"],
  },
  {
    c: "c3", icon: "⬡", name: "CLUSTERING",
    desc: "All facts from all articles are grouped by cosine similarity. Each cluster is one unique canonical fact. The result is the fact universe F and the matrix C ∈ {0,1}^(k×n).",
    badge: "Fact Universe F",
    tags: ["agglomerative", "avg-linkage", "τ = 0.85"],
  },
  {
    c: "c4", icon: "⊞", name: "ARTICLE VECTORS",
    desc: "Each article vector is the mean of the unique cluster vectors it covers, not its raw entries. This removes repetition noise: each fact counts only once.",
    badge: "êᵢ ∈ ℝᵈ (L2-norm)",
    tags: ["mean of unique clusters", "L2-normalize"],
  },
  {
    c: "c5", icon: "≋", name: "SCORING",
    desc: "Four raw components: centrality (distance from centroid), coverage (weighted recall), density (unique facts / total entries), and optional entity coverage. Then min-max normalization to [0, 1].",
    badge: "cᵢ, covᵢ, densᵢ ∈ [0,1]",
    tags: ["4 components", "min-max norm", "relative to corpus"],
  },
  {
    c: "c6", icon: "↑", name: "RANK / SELECT",
    desc: "The final score is a weighted sum. Articles are ranked by descending score. Top-M selection can use a simple cutoff or MMR to balance quality and diversity in the selected set.",
    badge: "score(i) ∈ [0,1]",
    tags: ["weighted sum", "top_score / mmr"],
  },
];

const components = [
  {
    cls: "cent",
    name: "Centrality",
    question: "Does this article resemble the others?",
    body: "Computes the centroid of all article vectors. An article is central when its content vector is close to the corpus's geometric average, meaning it tells the same things everyone else tells.",
    formula: "c̃ᵢ = −‖êᵢ − μ‖",
    weight: 0.40,
    color: theme.accent1,
    why: "A proxy for semantic representativeness. It still works when fact extraction is imperfect.",
  },
  {
    cls: "cov",
    name: "Coverage",
    question: "How much of the story does it cover?",
    body: "Weighted recall against the fact universe. Each fact has a weight equal to the fraction of articles that mention it. Coverage = sum of covered fact weights / total fact weights.",
    formula: "coṽᵢ = Σ wⱼ·Cᵢⱼ / Σ wⱼ",
    weight: 0.50,
    color: theme.accent2,
    why: "The most direct signal: how much of the news event does this article tell me?",
  },
  {
    cls: "dens",
    name: "Density",
    question: "Is it dense or repetitive?",
    body: "The ratio between unique covered facts and total extracted entries. An article with 30 entries but only 8 unique clusters has density ≈ 0.27. It penalizes padding without penalizing completeness.",
    formula: "dens̃ᵢ = Uᵢ / (Eᵢ + Lᵢ)",
    weight: 0.10,
    color: theme.accent3,
    why: "A corrective term: it prevents redundant articles from ranking high just because they are long.",
  },
];

const profiles = [
  {
    name: "Representative",
    color: theme.accent1,
    alpha: 0.40, beta: 0.50, gamma: 0.10,
    desc: "Balances consensus and completeness",
  },
  {
    name: "Comprehensive",
    color: theme.accent2,
    alpha: 0.20, beta: 0.70, gamma: 0.10,
    desc: "Maximizes fact coverage",
  },
  {
    name: "Concise",
    color: theme.accent3,
    alpha: 0.20, beta: 0.40, gamma: 0.40,
    desc: "Prefers dense, compact articles",
  },
];

const mmrSteps = [
  {
    n: "Step 0",
    title: "Start",
    body: "The selected set S is empty. There is no diversity penalty, so the best article by score is selected first.",
  },
  {
    n: "Step t",
    title: "Next choice",
    body: "For each candidate: weighted score λ minus its maximum similarity to articles already selected.",
  },
  {
    n: "Iteration",
    title: "Repeat",
    body: "Add the winner to the selected set. Recompute the penalty against the new set. Continue until M articles are selected.",
  },
];

const beforeBars = [
  { name: "central.", val: -0.32, pct: 85, color: theme.accent1 },
  { name: "coverage", val: 0.78, pct: 78, color: theme.accent2 },
  { name: "density", val: 0.91, pct: 91, color: theme.accent3 },
];
const afterBars = [
  { name: "central.", val: "0.81", pct: 81, color: theme.accent1 },
  { name: "coverage", val: "0.78", pct: 78, color: theme.accent2 },
  { name: "density", val: "1.00", pct: 100, color: theme.accent3 },
];

function Infographic() {
  return (
    <>
      <style>{style}</style>
      <div className="root">

        {/* HEADER */}
        <div className="header">
          <div className="header-eyebrow">News Ranking System · Design Document</div>
          <h1 className="header-title">How article <span>ranking</span><br/>works</h1>
          <p className="header-sub">
            From raw text to final score: a complete pipeline for selecting the best articles with structured decomposition, semantic clustering, and multi-criteria scoring.
          </p>
          <div className="header-line" />
        </div>

        {/* PIPELINE */}
        <div className="section-title">01 · Processing pipeline</div>
        <div className="pipeline">
          {pipelineSteps.map((step, i) => (
            <div className="pipe-step" key={i}>
              <div className="pipe-connector">
                <div className="pipe-num">{i + 1}</div>
                {i < pipelineSteps.length - 1 && <div className="pipe-line" />}
              </div>
              <div className={`pipe-content ${step.c}`}>
                <div className="pipe-header">
                  <span className="pipe-icon">{step.icon}</span>
                  <span className={`pipe-name ${step.c}`}>{step.name}</span>
                </div>
                <div className="pipe-desc">{step.desc}</div>
                <div className="pipe-output">
                  {step.tags.map((t, j) => (
                    <span className="pipe-badge" key={j}
                      style={{ color: theme.muted, borderColor: theme.border }}>
                      {t}
                    </span>
                  ))}
                </div>
              </div>
            </div>
          ))}
        </div>

        {/* SCORING COMPONENTS */}
        <div className="section-title">02 · The three scoring components</div>
        <div className="components-grid">
          {components.map((c, i) => (
            <div className={`comp-card ${c.cls}`} key={i}>
              <div className="comp-accent" />
              <div className="comp-name">{c.name}</div>
              <div className="comp-question">{c.question}</div>
              <div className="comp-body">{c.body}</div>
              <div className="comp-formula">
                <span style={{ color: theme.muted }}>formula: </span>
                <span>{c.formula}</span>
              </div>
              <div className="comp-weight">
                <div style={{ fontFamily: "'DM Mono', monospace", fontSize: 10, color: theme.muted, width: 50 }}>
                  default weight
                </div>
                <div className="comp-weight-bar">
                  <div className="comp-weight-fill"
                    style={{ width: `${c.weight * 100}%`, background: c.color }} />
                </div>
                <div className="comp-weight-label">{Math.round(c.weight * 100)}%</div>
              </div>
              <div style={{ marginTop: 10, fontFamily: "'DM Mono', monospace", fontSize: 10.5, color: theme.dim, lineHeight: 1.5 }}>
                → {c.why}
              </div>
            </div>
          ))}
        </div>

        {/* NORMALIZATION */}
        <div className="section-title">03 · Min-max normalization</div>
        <div className="norm-block">
          <div style={{ fontFamily: "'DM Mono', monospace", fontSize: 12.5, color: theme.muted, lineHeight: 1.6, fontWeight: 300 }}>
            The three components live on <strong style={{ color: theme.text }}>very different scales</strong>: centrality is a negative distance (−0.3 → −1.2), while coverage and density are fractions. Without normalization, the weighted sum would be dominated by the component with the highest absolute variance, regardless of the chosen weights.
          </div>
          <div className="norm-visual">
            <div className="norm-before">
              <div className="norm-label">before — different scales</div>
              {beforeBars.map((b, i) => (
                <div className="norm-bar-row" key={i}>
                  <div className="norm-bar-name">{b.name}</div>
                  <div className="norm-bar-track">
                    <div className="norm-bar-fill" style={{ width: `${b.pct}%`, background: b.color + "80" }} />
                  </div>
                  <div className="norm-val" style={{ color: theme.dim }}>{b.val}</div>
                </div>
              ))}
            </div>
            <div className="norm-arrow">→</div>
            <div className="norm-after">
              <div className="norm-label">after — [0, 1]</div>
              {afterBars.map((b, i) => (
                <div className="norm-bar-row" key={i}>
                  <div className="norm-bar-name">{b.name}</div>
                  <div className="norm-bar-track">
                    <div className="norm-bar-fill" style={{ width: `${b.pct}%`, background: b.color }} />
                  </div>
                  <div className="norm-val" style={{ color: theme.text }}>{b.val}</div>
                </div>
              ))}
            </div>
          </div>
          <div className="norm-why">
            <strong>Tie rule:</strong> if every article has the same value for a component (range ≈ 0), that component is non-discriminating → everyone receives <strong>1.0</strong>, not 0. Mapping to 0 is reserved for undefined components (for example, no extracted entities).
          </div>
        </div>

        {/* SCORE FORMULA */}
        <div className="section-title">04 · Composite final score</div>
        <div className="score-block">
          <div style={{ fontFamily: "'DM Mono', monospace", fontSize: 12, color: theme.muted }}>
            Once normalized, components are combined into a <strong style={{ color: theme.text }}>weighted sum</strong>. The weights express an explicit definition of "best"; changing them changes the criterion, not the logic.
          </div>
          <div className="score-equation">
            <span className="eq-label">score(i)</span>
            <span className="eq-equals">=</span>
            <div className="eq-term">
              <span className="eq-alpha">α</span>
              <span className="eq-dot">·</span>
              <span className="eq-alpha">c</span>
            </div>
            <span className="eq-plus">+</span>
            <div className="eq-term">
              <span className="eq-beta">β</span>
              <span className="eq-dot">·</span>
              <span className="eq-beta">cov</span>
            </div>
            <span className="eq-plus">+</span>
            <div className="eq-term">
              <span className="eq-gamma">γ</span>
              <span className="eq-dot">·</span>
              <span className="eq-gamma">dens</span>
            </div>
            <span className="eq-plus">&nbsp;&nbsp;with&nbsp;</span>
            <span style={{ fontFamily: "'DM Mono', monospace", fontSize: 12, color: theme.dim }}>α + β + γ = 1</span>
          </div>
          <div className="score-legend">
            <div className="legend-item">
              <div className="legend-dot" style={{ background: theme.accent1 }} />
              <div>
                <div className="legend-key">α = 0.40 · centrality</div>
                <div className="legend-val">semantic representativeness</div>
              </div>
            </div>
            <div className="legend-item">
              <div className="legend-dot" style={{ background: theme.accent2 }} />
              <div>
                <div className="legend-key">β = 0.50 · coverage</div>
                <div className="legend-val">main signal — weighted recall</div>
              </div>
            </div>
            <div className="legend-item">
              <div className="legend-dot" style={{ background: theme.accent3 }} />
              <div>
                <div className="legend-key">γ = 0.10 · density</div>
                <div className="legend-val">anti-padding corrective term</div>
              </div>
            </div>
          </div>
        </div>

        {/* PROFILES */}
        <div className="section-title">05 · Scoring profiles</div>
        <div className="profiles-grid">
          {profiles.map((p, i) => (
            <div className="profile-card" key={i}
              style={{ borderColor: p.color + "40" }}>
              <div className="profile-name" style={{ color: p.color }}>{p.name}</div>
              {[["α · centrality", p.alpha], ["β · coverage", p.beta], ["γ · density", p.gamma]].map(([label, val], j) => (
                <div className="profile-bar-row" key={j}>
                  <div className="profile-bar-label">
                    <span>{label}</span>
                    <span style={{ color: theme.text }}>{Math.round(val * 100)}%</span>
                  </div>
                  <div className="profile-bar-track">
                    <div className="profile-bar-fill"
                      style={{ width: `${val * 100}%`, background: p.color }} />
                  </div>
                </div>
              ))}
              <div style={{ marginTop: 10, fontFamily: "'DM Mono', monospace", fontSize: 10.5, color: theme.muted }}>
                {p.desc}
              </div>
            </div>
          ))}
        </div>

        {/* MMR */}
        <div className="section-title">06 · Top-M selection with MMR</div>
        <div className="mmr-block">
          <div style={{ fontFamily: "'DM Mono', monospace", fontSize: 12.5, color: theme.muted, lineHeight: 1.6, fontWeight: 300, marginBottom: 16 }}>
            The top-M articles by score can be nearly identical rewrites of the same wire report. <strong style={{ color: theme.text }}>MMR balances quality and diversity</strong>: at each step it chooses the article that maximizes score after discounting similarity to articles already selected.
          </div>
          <div className="mmr-steps">
            {mmrSteps.map((s, i) => (
              <div className="mmr-step" key={i}>
                <div className="mmr-step-num">{s.n}</div>
                <div className="mmr-step-title">{s.title}</div>
                <div className="mmr-step-body">{s.body}</div>
              </div>
            ))}
          </div>

          <div className="mmr-formula-row">
            <span className="hl">iₜ</span> = <span style={{ color: theme.muted }}>argmax</span><sub style={{ fontSize: 9 }}>i∉S</sub> [&nbsp;
            <span className="hl2">λ · score(i)</span>
            &nbsp;−&nbsp;
            <span className="hl3">(1−λ) · max<sub style={{ fontSize: 9 }}>s∈S</sub> max(0, ⟨êᵢ, êₛ⟩)</span>
            &nbsp;]<br />
            <span style={{ color: theme.dim, fontSize: 10 }}>
              ↑ article quality &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;
              ↑ redundancy penalty with the most similar selected article
            </span>
          </div>

          <div style={{ marginTop: 18 }}>
            <div style={{ fontFamily: "'DM Mono', monospace", fontSize: 10, color: theme.muted, marginBottom: 6 }}>
              λ = 0.8 (default) · quality ↔ diversity dial
            </div>
            <div className="lambda-track">
              <div className="lambda-thumb" />
            </div>
            <div className="lambda-labels">
              <span>λ=0 · diversity only</span>
              <span style={{ color: theme.accent5 }}>λ=0.8 default</span>
              <span>λ=1 · score only</span>
            </div>
          </div>

          <div style={{ marginTop: 16, display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10 }}>
            <div style={{ background: '#0d1018', border: `1px solid ${theme.border}`, borderRadius: 8, padding: 12 }}>
              <div style={{ fontFamily: "'DM Mono', monospace", fontSize: 10, color: theme.accent5, marginBottom: 6 }}>GUARANTEED PROPERTIES</div>
              <div style={{ fontFamily: "'DM Mono', monospace", fontSize: 11, color: theme.muted, lineHeight: 1.6, fontWeight: 300 }}>
                → The 1st article is always the top by score<br />
                → max(0, sim) avoids rewarding anti-correlations<br />
                → Greedy O(M·k), not combinatorial
              </div>
            </div>
            <div style={{ background: '#0d1018', border: `1px solid ${theme.border}`, borderRadius: 8, padding: 12 }}>
              <div style={{ fontFamily: "'DM Mono', monospace", fontSize: 10, color: theme.accent4, marginBottom: 6 }}>WHEN TO USE IT</div>
              <div style={{ fontFamily: "'DM Mono', monospace", fontSize: 11, color: theme.muted, lineHeight: 1.6, fontWeight: 300 }}>
                → Multi-source press reviews<br />
                → Balanced training datasets<br />
                → Corpora with many wire-service duplicates
              </div>
            </div>
          </div>
        </div>

        {/* FOOTER */}
        <div className="footer">
          News Ranking Library · Unbubble Hub · H-Farm · Design Document v1
        </div>
      </div>
    </>
  );
}

window.Infographic = Infographic;
