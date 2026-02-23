import uvicorn
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from main import analyze_repository
from fastapi.middleware.cors import CORSMiddleware


app = FastAPI(title="GitLab Repository Analysis Tool")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class RepoRequest(BaseModel):
    repo_url: str

@app.post("/analyze")
def analyze(repo: RepoRequest):
    try:
        result = analyze_repository(repo.repo_url)
        return result
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
