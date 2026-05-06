# Iconographic GitHub Pages Context

## Task

Make the newly added `infographic/` folder hostable through GitHub Pages.

## Relevant Files

- `infographic/infographic.jsx` currently contains a React component and all styling/data
  for the visual explanation of the ranking pipeline.
- The repository is a Python package with `uv`, `ruff`, `mypy`, and `pytest`; there is no
  existing JavaScript build system.
- GitHub Pages can serve static files directly when configured to publish from the
  repository root, which makes `/infographic/` a natural hosted path.

## Constraints

- Do not add new dependencies without asking.
- Do not add CI, deployment workflows, Docker, or other infrastructure unless required.
- Keep the change scoped to static hosting for the visual asset.
- Preserve the existing Python package checks.

## Current Behavior

`infographic/infographic.jsx` is not directly hostable by GitHub Pages because it is only
a JSX component file. A browser needs an HTML entrypoint and a way to load React/JSX.

## Hosting Shape

Use a static `infographic/index.html` entrypoint that loads React and Babel from CDNs,
then mounts the local JSX component. This avoids adding a package manager or build step
for the infographic while allowing GitHub Pages to serve it from:

`https://<owner>.github.io/<repo>/infographic/`
