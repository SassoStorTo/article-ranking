import { QueryClient, QueryClientProvider, useQuery } from "@tanstack/react-query";
import React from "react";
import ReactDOM from "react-dom/client";
import "./styles.css";

const queryClient = new QueryClient();
const apiBaseUrl = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

type HealthResponse = {
  ok: boolean;
};

function useBackendHealth() {
  return useQuery({
    queryKey: ["health"],
    queryFn: async (): Promise<HealthResponse> => {
      const response = await fetch(`${apiBaseUrl}/api/health`);
      if (!response.ok) {
        throw new Error(`Health check failed with ${response.status}`);
      }
      return response.json() as Promise<HealthResponse>;
    },
    refetchInterval: 5000,
  });
}

function App() {
  const health = useBackendHealth();
  const isHealthy = health.data?.ok === true;

  return (
    <main className="app-shell">
      <section className="status-panel" aria-labelledby="page-title">
        <p className="eyebrow">Live Demo</p>
        <h1 id="page-title">News Ranker</h1>
        <p className="summary">
          Backend and frontend skeleton are running from the local project.
        </p>
        <dl className="status-list">
          <div>
            <dt>Backend</dt>
            <dd className={isHealthy ? "status-ok" : "status-waiting"}>
              {health.isLoading && "Checking"}
              {health.isError && "Unavailable"}
              {isHealthy && "Healthy"}
            </dd>
          </div>
          <div>
            <dt>Health endpoint</dt>
            <dd>{apiBaseUrl}/api/health</dd>
          </div>
        </dl>
      </section>
    </main>
  );
}

ReactDOM.createRoot(document.getElementById("root") as HTMLElement).render(
  <React.StrictMode>
    <QueryClientProvider client={queryClient}>
      <App />
    </QueryClientProvider>
  </React.StrictMode>,
);
