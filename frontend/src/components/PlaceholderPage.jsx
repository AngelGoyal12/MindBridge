
import { ArrowLeft, ArrowRight, HeartHandshake, ShieldCheck, BookOpen, Accessibility, Building2 } from "lucide-react";
import { Link } from "react-router-dom";

const pageContent = {
  "/help": {
    eyebrow: "HELP & SUPPORT",
    title: "You don't have to figure it out alone.",
    intro:
      "MindBridge helps students share a concern, follow its progress, and understand what happens next.",
    icon: HeartHandshake,
    sections: [
      {
        title: "How do I get started?",
        text: "Create a student account, verify your email, sign in, and choose Share a concern. Select the category that best describes your request and provide only the information needed to explain it.",
      },
      {
        title: "How can I track my concern?",
        text: "Open My Cases to review your submitted cases and permitted progress updates. A submitted case may need human review before it is routed to a coordinator or department.",
      },
      {
        title: "Who can see my information?",
        text: "Access depends on your role, the case assignment, and applicable consent and authorization rules. A department should receive only the information needed for its assigned task.",
      },
      {
        title: "Need urgent help?",
        text: "MindBridge is an academic prototype, not an emergency response service. If you are in immediate danger, contact local emergency services or your institution's designated support team.",
      },
    ],
  },
  "/about": {
    eyebrow: "ABOUT MINDBRIDGE",
    title: "Support with privacy at its centre.",
    intro:
      "MindBridge is a student-support and case-coordination project designed to make the journey from asking for help to receiving follow-up clearer and more accountable.",
    icon: HeartHandshake,
    sections: [
      {
        title: "The problem we address",
        text: "Student support can become fragmented across people and departments. Students may have to repeat sensitive details, follow-ups can become unclear, and information may be shared more widely than necessary.",
      },
      {
        title: "Our approach",
        text: "MindBridge brings case submission, human review, department task assignment, progress updates, and case closure into one coordinated workflow.",
      },
      {
        title: "Privacy by design",
        text: "The intended approach is need-to-know access, consent-aware disclosure, role-based permissions, and traceable actions. These protections must be enforced and tested by the backend, not just hidden in the interface.",
      },
      {
        title: "Responsible use",
        text: "This is an academic prototype. It does not replace professional counselling, institutional procedures, or emergency services. Demonstrations should use fictional test data.",
      },
    ],
  },
  "/departments": {
    eyebrow: "SUPPORT COORDINATION",
    title: "The right task, to the right team.",
    intro:
      "MindBridge helps authorized coordinators route specific support actions to the appropriate department without exposing an entire sensitive case unnecessarily.",
    icon: Building2,
    sections: [
      {
        title: "Academic support",
        text: "May help coordinate academic guidance or other approved learning-related assistance.",
      },
      {
        title: "Hostel and accommodation",
        text: "May receive a narrowly scoped task for an accommodation-related concern when authorized.",
      },
      {
        title: "Student wellbeing and safety",
        text: "Concerns involving wellbeing, bullying, or safety require careful human review and appropriate institutional handling.",
      },
      {
        title: "How department access works",
        text: "Department staff must sign in with an authorized account. They should see only tasks routed to their trusted department and the information permitted for that task.",
      },
    ],
    note:
      "These are illustrative support areas, not a claim that specific university departments are connected to this prototype.",
  },
  "/accessibility": {
    eyebrow: "ACCESSIBILITY",
    title: "Support should be easier to reach.",
    intro:
      "MindBridge aims to make its support journey clear, readable, and usable across devices and for students with different access needs.",
    icon: Accessibility,
    sections: [
      {
        title: "Clear language",
        text: "Forms and status labels should explain what is needed and what happens next without unnecessary technical language.",
      },
      {
        title: "Keyboard and assistive technology",
        text: "Interactive controls should be keyboard accessible, use meaningful labels, show visible focus, and communicate errors to assistive technologies.",
      },
      {
        title: "Readable interface",
        text: "Text should have sufficient contrast, layouts should work on smaller screens, and information should not rely on colour alone.",
      },
      {
        title: "Requesting assistance",
        text: "If the interface prevents you from completing a step, contact your institution's designated support team through an established channel.",
      },
    ],
    note:
      "These are accessibility goals and guidance, not a claim that a formal accessibility audit or full compliance assessment has been completed.",
  },
};

export default function PlaceholderPage({
  eyebrow,
  title,
  description,
  backTo = "/",
  backLabel = "Back to MindBridge",
}) {
  const path = window.location.pathname;
  const content = pageContent[path];
  const Icon = content?.icon || BookOpen;

  const pageEyebrow = content?.eyebrow || eyebrow || "MINDBRIDGE";
  const pageTitle = content?.title || title || "MindBridge information";
  const intro = content?.intro || description || "";

  return (
    <main className="page-container info-page">
      <Link to={backTo} className="placeholder-back">
        <ArrowLeft size={16} aria-hidden="true" />
        {backLabel}
      </Link>

      <header className="info-page-header">
        <div className="info-page-icon">
          <Icon size={27} aria-hidden="true" />
        </div>
        <p className="section-overline">{pageEyebrow}</p>
        <h1>{pageTitle}</h1>
        <p className="info-page-intro">{intro}</p>
      </header>

      {content && (
        <section className="info-card-grid" aria-label={pageTitle}>
          {content.sections.map((section) => (
            <article className="info-card" key={section.title}>
              <h2>{section.title}</h2>
              <p>{section.text}</p>
            </article>
          ))}
        </section>
      )}

      {content?.note && (
        <p className="info-page-note">
          <ShieldCheck size={18} aria-hidden="true" />
          <span>{content.note}</span>
        </p>
      )}

      <section className="info-next-step">
        <div>
          <span className="section-overline">YOUR NEXT STEP</span>
          <h2>Ready to continue?</h2>
          <p>
            Sign in to access your workspace or return to the MindBridge home
            page to learn more about the process.
          </p>
        </div>
        <Link to="/login" className="button-primary">
          Sign in <ArrowRight size={17} />
        </Link>
      </section>
    </main>
  );
}
