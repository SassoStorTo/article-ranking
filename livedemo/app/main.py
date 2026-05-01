from fastapi import FastAPI

app = FastAPI(title="News Ranker Live Demo")


@app.get("/api/health")
def health() -> dict[str, bool]:
    return {"ok": True}
