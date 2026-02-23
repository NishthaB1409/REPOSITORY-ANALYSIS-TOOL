import { useState } from "react";
import { analyzeRepo } from "../api/api";
import { Bar } from "react-chartjs-2";
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  BarElement,
  Tooltip,
  Legend,
} from "chart.js";
import "./analyzer.css";

ChartJS.register(CategoryScale, LinearScale, BarElement, Tooltip, Legend);

function Analyzer() {
  const [repoUrl, setRepoUrl] = useState("");
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);

  const handleAnalyze = async () => {
    if (!repoUrl) return alert("Please enter a GitLab repository URL");

    setLoading(true);
    try {
      const response = await analyzeRepo(repoUrl);
      setData(response.data);
    } catch (error) {
      alert("Error analyzing repository");
    }
    setLoading(false);
  };

  const forkDetails = data?.forks?.details || [];
  const mostActiveFork = data?.forks?.most_active;

  const chartData = {
    labels: forkDetails.map((f) => f.name),
    datasets: [
      {
        label: "Commits per Fork",
        data: forkDetails.map((f) => f.commits),
        backgroundColor: "#fc6d26",
        borderRadius: 6,
      },
    ],
  };

  return (
    <div className="page">
      <div className="container">

        {/* Header */}
        <header className="header">
          <h1>GitLab Repository Analysis Tool</h1>
          <p>Analyze GitLab repositories in seconds</p>
        </header>

        {/* Input Card */}
        <div className="card">
          <label className="label">Repository URL</label>
          <div className="input-row">
            <input
              type="text"
              placeholder="https://gitlab.com/username/repo"
              value={repoUrl}
              onChange={(e) => setRepoUrl(e.target.value)}
            />
            <button onClick={handleAnalyze} disabled={loading}>
              {loading ? "Analyzing..." : "Analyze"}
            </button>
          </div>
        </div>

        {/* Stats */}
        {data && (
          <div className="stats">
            <StatCard title="Total Commits" value={data.project.total_commits} />
            <StatCard title="Default Branch" value={data.project.default_branch} />
            <StatCard title="Total Forks" value={data.forks.count} />
            <StatCard title="Forks Analyzed" value={data.forks.analyzed_count ?? forkDetails.length} />
          </div>
        )}

        {/* Project Info */}
        {data && (
          <div className="card info">
            <p><strong>Project:</strong> {data.project.name}</p>
            <p><strong>License:</strong> {data.project.license || "No license detected"}</p>
          </div>
        )}

        {/* Most Active Fork */}
        {data && mostActiveFork && (
          <div className="card info">
            <p><strong>Most Active Fork:</strong> {mostActiveFork.name}</p>
            <p><strong>Commits:</strong> {mostActiveFork.commits}</p>
            <p><strong>License:</strong> {mostActiveFork.license || "No license detected"}</p>
          </div>
        )}

        {/* Chart */}
        {data && forkDetails.length > 0 && (
          <div className="card">
            <h3>Commits per Fork</h3>
            <Bar data={chartData} />
          </div>
        )}

        {/* Fork Details */}
        {data && forkDetails.length > 0 && (
          <div className="card">
            <h3>Fork Details</h3>
            <div className="fork-table-wrap">
              <table className="fork-table">
                <thead>
                  <tr>
                    <th>Fork</th>
                    <th>Commits</th>
                    <th>License</th>
                    <th>Last Updated</th>
                  </tr>
                </thead>
                <tbody>
                  {forkDetails.map((fork) => (
                    <tr key={fork.name}>
                      <td>{fork.name}</td>
                      <td>{fork.commits}</td>
                      <td>{fork.license || "No license detected"}</td>
                      <td>{new Date(fork.last_updated).toLocaleString()}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

function StatCard({ title, value }) {
  return (
    <div className="stat-card">
      <span>{title}</span>
      <h2>{value}</h2>
    </div>
  );
}

export default Analyzer;
