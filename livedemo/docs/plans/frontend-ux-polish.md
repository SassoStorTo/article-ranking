# Frontend UX Polish Plan

## Goal

Turn the single-screen demo into a clearer app shell with a home page, top
navigation, section pages for corpus creation/article management/executions, safe
delete affordances, constrained large-content panes, and a light/dark theme
toggle.

## Steps

1. Add a top app navigation shell with page state and a home page summarizing the
   current corpus/execution state.
2. Move corpus creation into its own page while preserving automatic selection
   of newly created corpora.
3. Add an article management page for uploading and browsing articles within the
   selected corpus.
4. Add article deletion API/client support and frontend delete controls for
   articles; improve corpus deletion affordance on the corpus page.
5. Constrain article, structured payload, table, and workspace overflow so large
   articles or sections scroll internally instead of stretching the app.
6. Add a light/dark theme toggle in the top navigation.
7. Run the relevant Python and frontend checks after each committed step; run a
   final verification pass and inspect the diff.
