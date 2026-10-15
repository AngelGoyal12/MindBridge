import { ArrowLeft, Construction } from "lucide-react";
import { Link } from "react-router-dom";

function PlaceholderPage({
  eyebrow = "MIND BRIDGE",
  title,
  description,
  backTo = "/dashboard",
  backLabel = "Back to dashboard",
}) {
  return (
    <main className="page-shell">
      <section className="placeholder-page">
        <Link to={backTo} className="placeholder-back">
          <ArrowLeft size={16} />
          {backLabel}
        </Link>

        <div className="placeholder-content">
          <div className="placeholder-icon">
            <Construction size={25} />
          </div>

          <p className="eyebrow">{eyebrow}</p>
          <h1>{title}</h1>
          <p className="placeholder-description">{description}</p>

          <span className="placeholder-status">
            <span className="placeholder-status-dot" />
            Page under development
          </span>
        </div>

        <div className="placeholder-footer">
          <span>MindBridge</span>
          <span>Student support, with care and privacy.</span>
        </div>
      </section>
    </main>
  );
}

export default PlaceholderPage;