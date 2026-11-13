from fastapi import FastAPI

app = FastAPI(title="G.E.R.A.L.D.O. API", version="0.1.0")


@app.get("/health", include_in_schema=False)
def health() -> dict:
    return {"status": "ok"}
