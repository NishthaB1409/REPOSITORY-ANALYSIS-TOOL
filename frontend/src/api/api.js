import axios from "axios";

const API = axios.create({
  baseURL: "http://127.0.0.1:8000",  
});

export const analyzeRepo = (repoUrl) =>
  API.post("/analyze", { repo_url: repoUrl });