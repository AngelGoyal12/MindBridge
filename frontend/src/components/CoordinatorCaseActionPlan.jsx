
import { useState } from "react";
import { generateCaseAIActionPlan } from "../services/caseService";

export default function CoordinatorCaseActionPlan({ caseItem }) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function handleGeneratePlan() {
    try {
      setLoading(true);
      setError("");
      setData(null);

      const response = await generateCaseAIActionPlan(caseItem.id);
      setData(response.action_plan);
    } catch (err) {
      setError(err.message || "Unable to generate action plan.");
    } finally {
      setLoading(false);
    }
  }

  const steps = data?.action_plan || [];
  const additionalInfo = data?.additional_information_needed || [];

  return (
    <section className="coordinator-ai-action-plan">
      <div>
        <h3>AI-Powered Case Action Plan</h3>
        <p>
          Generate suggested next steps for this case.
          Review all suggestions before taking action.
        </p>
      </div>

      <button
        type="button"
        onClick={handleGeneratePlan}
        disabled={loading}
      >
        {loading ? "Generating Plan..." : "Generate Action Plan"}
      </button>

      {error && (
        <div role="alert">
          {error}
        </div>
      )}

      {data && (
        <div>
          <h4>Suggested Actions</h4>

          {steps.length > 0 ? (
            steps.map((step, index) => (
              <article key={index}>
                <h5>{index + 1}. {step.title}</h5>
                <p>{step.description}</p>
                <p><strong>Reason:</strong> {step.reason}</p>
              </article>
            ))
          ) : (
            <p>No specific action steps could be generated.</p>
          )}

          {additionalInfo.length > 0 && (
            <div>
              <h4>Additional Information Needed</h4>
              <ul>
                {additionalInfo.map((item, index) => (
                  <li key={index}>{item}</li>
                ))}
              </ul>
            </div>
          )}

          <p>
            AI-generated suggestions are advisory only.
            Coordinator approval is required before taking action.
          </p>
        </div>
      )}
    </section>
  );
}
