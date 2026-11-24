import ReactMarkdown from "react-markdown";
import { useEffect, useState } from "react";
import { getCoordinatorAIInsights } from "../services/caseService";

export default function CoordinatorAIInsights() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  async function fetchInsights() {
    try {
      setLoading(true);
      setError("");

      const response = await getCoordinatorAIInsights();
      setData(response);
    } catch (err) {
      setError(err.message || "Unable to load AI insights.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    fetchInsights();
  }, []);

  return (
    <section className="coordinator-ai-insights">
      <div className="coordinator-ai-header">
        <div>
          <h2>AI-Powered Coordinator Insights</h2>
          <p>
            Evidence-based insights generated from anonymized dashboard
            statistics.
          </p>
        </div>

        <button
          type="button"
          onClick={fetchInsights}
          disabled={loading}
        >
          {loading ? "Generating..." : "Refresh Insights"}
        </button>
      </div>

      {loading && (
        <p>AI is analyzing coordinator statistics...</p>
      )}

      {error && (
        <div role="alert" className="coordinator-ai-error">
          {error}
        </div>
      )}

      {!loading && !error && data && (
        <div className="coordinator-ai-content">
          <div className="coordinator-ai-statistics">
            <div>
              <span>Total Cases</span>
              <strong>{data.statistics?.total_cases ?? 0}</strong>
            </div>

            <div>
              <span>Total Tasks</span>
              <strong>{data.statistics?.total_tasks ?? 0}</strong>
            </div>

            <div>
              <span>Overdue Tasks</span>
              <strong>{data.statistics?.overdue_tasks ?? 0}</strong>
            </div>
          </div>

          <div className="coordinator-ai-report">
            <h3>AI Analysis & Recommendations</h3>

            <ReactMarkdown>
                {data.insights}
            </ReactMarkdown>
            </div>
        
          <p className="coordinator-ai-disclaimer">
            AI-generated suggestions are advisory only. Final decisions
            remain with the coordinator.
          </p>
        </div>
      )}
    </section>
  );
}
