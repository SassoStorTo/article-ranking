# Iconographic GitHub Pages Plan

## Goal

Make the `infographic/` folder directly usable as a GitHub Pages static page.

## Steps

1. Add task context and plan artifacts describing the Pages hosting approach.
2. Add an HTML entrypoint in `infographic/` that mounts the React infographic without a
   repository-level JavaScript build.
3. Adjust `infographic/infographic.jsx` only as needed for browser-side mounting.
4. Add short hosting instructions near the infographic so the expected Pages URL is
   obvious.
5. Run `make check`, inspect the diff, and commit each completed point as work lands.
6. Add a root `index.html` and `.nojekyll` after deployed Pages shows the README at the
   site root.

## Acceptance Criteria

- `infographic/index.html` can be served statically.
- The existing infographic content renders from `infographic/infographic.jsx`.
- No new project dependencies are added.
- Python checks still pass with `make check`.
- The root Pages URL renders the infographic instead of the project README.
