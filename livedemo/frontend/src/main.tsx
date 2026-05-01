import { StrictMode } from "react";
import { createRoot } from "react-dom/client";

function App() {
  return (
    <main>
      <h1>News Ranker Live Demo</h1>
      <p>Upload corpora, run ranking experiments, and compare executions.</p>
    </main>
  );
}

const root = document.getElementById("root");

if (root === null) {
  throw new Error("Root element not found");
}

createRoot(root).render(
  <StrictMode>
    <App />
  </StrictMode>,
);
