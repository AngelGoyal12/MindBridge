
import { useEffect } from 'react';
import {
  BrowserRouter,
  NavLink,
  Route,
  Routes,
  useNavigate,
  useLocation,
} from 'react-router-dom';
import {
  ArrowUpRight,
  Bell,
  HeartHandshake,
  Menu,
  ShieldCheck,
} from 'lucide-react';

import './App.css';
import SubmitCase from './pages/SubmitCase.jsx';
import MyCases from './pages/MyCases.jsx';
import CaseDetails from './pages/CaseDetails.jsx';
import Notifications from "./pages/Notifications.jsx";
import PrivacyPreferences from "./pages/PrivacyPreferences.jsx";
import { getCases } from "./services/mockCaseService";

import PlaceholderPage from "./components/PlaceholderPage.jsx";

function Navbar() {

  const navigate = useNavigate();
  const location = useLocation();

  const handleHomeClick = (event) => {
    if (location.pathname === '/') {
      event.preventDefault();

      if (location.hash) {
        navigate('/', { replace: true });
      }

      window.scrollTo({
        top: 0,
        behavior: 'smooth',
      });
    }
  };
  return (
    <header className="site-header">
      <nav className="navbar page-container" aria-label="Main navigation">
        <NavLink to="/" className="brand" aria-label="MindBridge home">
          <span className="brand-monogram" aria-hidden="true">
            <span className="monogram-m">m</span>
            <span className="monogram-b">b</span>
          </span>
          <span className="brand-lockup">
            <span className="brand-name">mindbridge<span>.</span></span>
            <span className="brand-descriptor">STUDENT SUPPORT, REIMAGINED</span>
          </span>
        </NavLink>

        <div className="nav-links">
          <NavLink to="/" end className="nav-link" onClick={handleHomeClick}>
            <span className="nav-index">01</span> Home
          </NavLink>
          <a href="/#how-it-works" className="nav-link">
            <span className="nav-index">02</span> The process
          </a>
          <a href="/#privacy" className="nav-link">
            <span className="nav-index">03</span> Your privacy
          </a>
        </div>

        <div className="nav-actions">
          <NavLink
            to="/notifications"
            className="nav-notifications"
            aria-label="Notifications"
            title="Notifications"
          >
            <Bell size={19} />
            <span>Notifications</span>
          </NavLink>

          <NavLink to="/dashboard" className="nav-action">
            <span className="portal-dot" />
            <span>Open your space</span>
            <ArrowUpRight size={16} />
          </NavLink>
        </div>

        <button
          className="mobile-menu"
          type="button"
          aria-label="Toggle navigation"
          aria-expanded="false"
          onClick={(event) => {
            const links = document.querySelector('.nav-links');
            const isOpen = links?.classList.toggle('nav-links-open');
            event.currentTarget.setAttribute(
              'aria-expanded',
              String(Boolean(isOpen))
            );
          }}
        >
          <Menu size={22} />
        </button>
      </nav>
    </header>
  );
}

function Reveal({ children, className = '' }) {
  useEffect(() => {
    const elements = document.querySelectorAll('.reveal');

    if (!('IntersectionObserver' in window)) {
      elements.forEach((element) => element.classList.add('is-visible'));
      return;
    }

    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            entry.target.classList.add('is-visible');
            observer.unobserve(entry.target);
          }
        });
      },
      { threshold: 0.12 }
    );

    elements.forEach((element) => observer.observe(element));

    return () => observer.disconnect();
  }, []);

  return <div className={`reveal ${className}`}>{children}</div>;
}

function Home() {
  return (
    <>
      <main>
        <section className="hero page-container">
          <div className="hero-copy">
            <div className="eyebrow">
              <span className="eyebrow-dot" />
              A little more support, when you need it
            </div>

            <h1>
              You don't have to
              <br />
              figure it all out <em>alone.</em>
            </h1>

            <p className="hero-description">
              College life can bring challenges that are difficult to
              talk about. MindBridge gives you a private, structured
              way to reach the right support and follow what happens next.
            </p>

            <div className="hero-actions">
              <NavLink to="/dashboard" className="button-primary">
                Explore student portal
                <ArrowUpRight size={18} />
              </NavLink>

              <a href="#how-it-works" className="text-link">
                How it works <span>↓</span>
              </a>
            </div>

            <div className="hero-note">
              <ShieldCheck size={18} />
              <span>Your concern deserves thoughtful human review.</span>
            </div>
          </div>

          <div className="hero-art" aria-label="Illustration of a supportive connection">
            <div className="art-orbit orbit-one" />
            <div className="art-orbit orbit-two" />

            <div className="art-note note-top">
              <span className="note-icon">✳</span>
              <span>Space to speak</span>
            </div>

            <div className="art-center">
              <div className="art-sun" />
              <div className="art-line line-one" />
              <div className="art-line line-two" />
              <div className="art-leaf leaf-one" />
              <div className="art-leaf leaf-two" />
              <div className="art-stem" />
              <span className="art-center-label">a place to begin</span>
            </div>

            <div className="art-note note-bottom">
              <span className="note-check">✓</span>
              <span>One step at a time</span>
            </div>

            <span className="art-spark spark-one">✳</span>
            <span className="art-spark spark-two">·</span>
          </div>
        </section>

        <section className="trust-strip" id="trust-strip">
          <div className="page-container trust-inner">
            <div className="trust-intro">Built around what matters</div>
            <div className="trust-item">
              <ShieldCheck size={19} />
              <span>Clear privacy choices</span>
            </div>
            <div className="trust-item">
              <HeartHandshake size={19} />
              <span>Human-led support</span>
            </div>
            <div className="trust-item">
              <span className="trust-star">✳</span>
              <span>Updates you can follow</span>
            </div>
          </div>
        </section>

        <section className="how-section page-container" id="how-it-works">
          <Reveal>
            <div className="section-heading">
              <div>
                <div className="eyebrow">A clearer way forward</div>
                <h2>Start where you are.</h2>
              </div>
              <p>
                You don't need to have everything figured out before
                asking for support.
              </p>
            </div>
          </Reveal>

          <div className="steps-grid">
            <Reveal className="step-card">
              <span className="step-number">01 / SHARE</span>
              <div className="step-illustration step-one-art">↗</div>
              <h3>Tell us what's happening</h3>
              <p>
                Share the details you're comfortable providing and
                choose how your identity should be handled.
              </p>
            </Reveal>

            <Reveal className="step-card">
              <span className="step-number">02 / REVIEW</span>
              <div className="step-illustration step-two-art">◎</div>
              <h3>Reach the right people</h3>
              <p>
                An authorized coordinator reviews your concern and
                determines the appropriate next steps.
              </p>
            </Reveal>

            <Reveal className="step-card">
              <span className="step-number">03 / FOLLOW</span>
              <div className="step-illustration step-three-art">↗</div>
              <h3>Follow your case</h3>
              <p>
                Check permitted updates and understand where your
                concern stands without starting from scratch.
              </p>
            </Reveal>
          </div>
        </section>

        <section className="home-privacy-section page-container" id="privacy">
          <Reveal>
            <div className="section-heading">
              <div>
                <div className="eyebrow">Your privacy, your choices</div>
                <h2>Support should feel safe.</h2>
              </div>
              <p>
                You decide what identifying information you provide.
                Access to sensitive case details should be limited to
                authorized people who need that information to help.
              </p>
            </div>
          </Reveal>

          <div className="steps-grid">
            <Reveal className="step-card">
              <span className="step-number">01 / CHOICE</span>
              <h3>Your identity preference</h3>
              <p>
                Choose an available identity-sharing preference when
                submitting a concern.
              </p>
            </Reveal>

            <Reveal className="step-card">
              <span className="step-number">02 / ACCESS</span>
              <h3>Need-to-know access</h3>
              <p>
                Sensitive information should only be available to
                authorized staff according to their permissions.
              </p>
            </Reveal>

            <Reveal className="step-card">
              <span className="step-number">03 / CONTROL</span>
              <h3>Human-led support</h3>
              <p>
                Authorized people review concerns and coordinate
                support. This prototype does not guarantee complete
                confidentiality or secure backend access.
              </p>
            </Reveal>
          </div>
        </section>

        <section className="closing-section page-container">
          <Reveal className="closing-panel">
            <div>
              <span className="closing-kicker">Whenever you're ready</span>
              <h2>A small first step is still a first step.</h2>
              <p>
                Start a concern or explore how the student portal works.
                You can take things one step at a time.
              </p>
            </div>
            <NavLink to="/dashboard" className="button-light">
              Enter MindBridge <ArrowUpRight size={18} />
            </NavLink>
          </Reveal>
        </section>
      </main>


      <footer className="site-footer">
        <div className="footer-main page-container">
          <div className="footer-message">
            <span className="footer-eyebrow">
              <span className="footer-spark">✳</span>
              A note to take with you
            </span>
            <h2>
              Asking for support
              <br />
              is a form of <em>strength.</em>
            </h2>
            <p>
              You don't need the perfect words.
              You just need a place to begin.
            </p>
          </div>

          <div className="footer-side">
            <div className="footer-brand-lockup">
              <span className="footer-monogram">mb</span>
              <span className="footer-brand-name">mindbridge.</span>
            </div>

            <p className="footer-side-copy">
              A more thoughtful way to connect student concerns with
              the people who can help.
            </p>

            <NavLink to="/dashboard" className="footer-link">
              Explore the student portal <ArrowUpRight size={16} />
            </NavLink>


            <div className="footer-page-links">
              <NavLink to="/help">Help & Support</NavLink>
              <NavLink to="/about">About</NavLink>
              <NavLink to="/departments">Departments</NavLink>
              <NavLink to="/accessibility">Accessibility</NavLink>
            </div>

          </div>
        </div>

        <div className="footer-bottom page-container">
          <span>MINDBRIDGE <span className="footer-separator">/</span> STUDENT SUPPORT CONCEPT</span>
          <a href="/#privacy">Privacy is part of the design <span>↗</span></a>
          <span>Built with care, one step at a time.</span>
        </div>
      </footer>

    </>
  );
}


function DashboardPlaceholder() {
  const statusLabels = {
    awaiting_review: "Awaiting review",
    under_review: "Under review",
    in_progress: "In progress",
    resolved: "Resolved",
    closed: "Closed",
  };

  const categoryLabels = {
    ragging_bullying: "Ragging & bullying",
    emotional_support: "Emotional support",
    academic_support: "Academic support",
    hostel_issue: "Hostel & accommodation",
    financial_assistance: "Financial assistance",
    other: "Other support",
  };

  const cases = getCases()
    .map((item) => {
      const status = item.status ?? "awaiting_review";

      return {
        ...item,
        status,
        statusLabel: statusLabels[status] ?? status,
        categoryLabel: categoryLabels[item.category] ?? item.category,
        date: item.createdAt
          ? new Date(item.createdAt).toLocaleDateString("en-IN", {
            day: "2-digit",
            month: "short",
            year: "numeric",
          })
          : item.date ?? "",
        statusClass: status.replaceAll("_", "-"),
        progress:
          status === "resolved" || status === "closed"
            ? 100
            : status === "in_progress"
              ? 66
              : status === "under_review"
                ? 33
                : 0,
      };
    })
    .sort((a, b) => {
      const dateA = new Date(a.createdAt ?? a.date).getTime();
      const dateB = new Date(b.createdAt ?? b.date).getTime();
      return dateB - dateA;
    });

  const totalCases = cases.length;

  const inProgressCount = cases.filter(
    (item) => item.status === "in_progress"
  ).length;

  const awaitingReviewCount = cases.filter(
    (item) => item.status === "awaiting_review"
  ).length;

  return (
    <main className="dashboard page-container">
      <section className="dashboard-welcome">
        <div className="dashboard-welcome-copy">
          <div className="eyebrow">
            <span className="eyebrow-dot" />
            YOUR STUDENT SPACE
          </div>

          <h1>
            A place to take
            <br />
            things <em>one step at a time.</em>
          </h1>

          <p>
            Whatever is on your mind, you can start here.
            Your concerns and their progress, all in one place.
          </p>
        </div>

        <div className="welcome-side-note">
          <span className="welcome-note-symbol">✳</span>
          <span>There's no perfect way<br />to ask for support.</span>
        </div>
      </section>

      <section className="dashboard-action-row">
        <div>
          <span className="section-overline">NEED A HAND?</span>
          <h2>Something on your mind?</h2>
          <p>Share what's happening when you're ready.</p>
        </div>

        <NavLink to="/submit" className="button-primary">
          Share a concern <ArrowUpRight size={18} />
        </NavLink>
      </section>

      <section className="dashboard-overview reveal is-visible">
        <div className="dashboard-section-heading">
          <div>
            <span className="section-overline">YOUR OVERVIEW</span>
            <h2>Where things stand.</h2>
          </div>
          <span className="overview-caption">A quick look at your cases</span>
        </div>

        <div className="overview-grid">
          <article className="overview-card">
            <span className="overview-label">Total cases</span>
            <div className="overview-value-row">
              <span className="overview-number">
                {String(totalCases).padStart(2, "0")}
              </span>
              <span className="overview-symbol symbol-green">↗</span>
            </div>
            <span className="overview-footnote">All your submitted concerns</span>
          </article>

          <article className="overview-card">
            <span className="overview-label">In progress</span>
            <div className="overview-value-row">
              <span className="overview-number">
                {String(inProgressCount).padStart(2, "0")}
              </span>
              <span className="overview-symbol symbol-amber">◷</span>
            </div>
            <span className="overview-footnote">Currently being addressed</span>
          </article>

          <article className="overview-card">
            <span className="overview-label">Awaiting review</span>
            <div className="overview-value-row">
              <span className="overview-number">
                {String(awaitingReviewCount).padStart(2, "0")}
              </span>
              <span className="overview-symbol symbol-coral">◎</span>
            </div>
            <span className="overview-footnote">Waiting for coordinator review</span>
          </article>
        </div>
      </section>

      <section className="dashboard-lower-grid">
        <div className="case-list-panel">
          <div className="dashboard-section-heading case-heading">
            <div>
              <span className="section-overline">YOUR ACTIVITY</span>
              <h2>Recent cases.</h2>
            </div>
            <NavLink to="/cases" className="subtle-link">
              View all <ArrowUpRight size={15} />
            </NavLink>
          </div>

          <div className="case-list">
            {cases.slice(0, 3).map((item) => (
              <article className="dashboard-case" key={item.id}>
                <div className="case-marker" />

                <div className="case-main">
                  <div className="case-id">{item.id}</div>
                  <h3>{item.title}</h3>
                  <p>{item.categoryLabel} <span>·</span> {item.date}</p>
                </div>

                <div className="case-end">
                  <span className={`status-badge case-status-${item.status}`}>
                    <span className="status-dot" />
                    {item.statusLabel}
                  </span>
                  <span className="case-progress-label">
                    {item.progress === 100 ? 'Completed' : 'Status update'}
                  </span>
                </div>
              </article>
            ))}
          </div>
        </div>

        <aside className="privacy-panel">
          <div className="privacy-icon">
            <ShieldCheck size={23} strokeWidth={1.6} />
          </div>

          <span className="section-overline">YOUR PRIVACY MATTERS</span>
          <h2>Your story.<br /><em>Your choices.</em></h2>

          <p>
            Your identity-sharing preference helps determine who can
            see identifying information. Access is controlled by
            permissions, not just what appears on this screen.
          </p>

          <div className="privacy-divider" />

          <div className="privacy-promise">
            <span className="privacy-check">✓</span>
            <span>Review your sharing preference when submitting a concern.</span>
          </div>

          <div className="privacy-panel-links">
            <NavLink
              to="/privacy-preferences"
              className="privacy-learn-link"
            >
              Privacy & Preferences <span>↗</span>
            </NavLink>

            <NavLink
              to="/#privacy"
              className="privacy-learn-link"
            >
              Understand our approach <span>↗</span>
            </NavLink>
          </div>
        </aside>
      </section>

      <div className="dashboard-footnote">
        <span className="footnote-star">✳</span>
        <span>
          MindBridge is a student-support prototype. For urgent danger,
          contact local emergency services or your institution's designated support team.
        </span>
      </div>
    </main>
  );
}


function NotFound() {
  return (
    <main className="placeholder page-container">
      <h1>Let's find your way back.</h1>
      <NavLink to="/" className="button-primary">Back to home</NavLink>
    </main>
  );
}

export default function App() {
  return (
    <BrowserRouter>
      <Navbar />
      <Routes>
        <Route path="/" element={<Home />} />
        <Route path="/dashboard" element={<DashboardPlaceholder />} />
        <Route path="/submit" element={<SubmitCase />} />
        <Route path="/cases" element={<MyCases />} />
        <Route path="/cases/:caseId" element={<CaseDetails />} />
        <Route
          path="/notifications"
          element={<Notifications />}
        />
        <Route
          path="/privacy-preferences"
          element={<PrivacyPreferences />}
        />
        <Route path="*" element={<NotFound />} />

        <Route
          path="/help"
          element={
            <PlaceholderPage
              eyebrow="SUPPORT"
              title="We're here to help."
              description="Find guidance on using MindBridge, understanding the support process, and getting help when you need it."
            />
          }
        />

        <Route
          path="/about"
          element={
            <PlaceholderPage
              eyebrow="OUR PURPOSE"
              title="Support that puts students first."
              description="MindBridge helps coordinate student support through a privacy-conscious, human-centred approach."
            />
          }
        />

        <Route
          path="/accessibility"
          element={
            <PlaceholderPage
              eyebrow="ACCESSIBILITY"
              title="Support should be accessible to everyone."
              description="We're working towards a clear, inclusive, and accessible experience for every student."
            />
          }
        />

        <Route
          path="/departments"
          element={
            <PlaceholderPage
              eyebrow="STUDENT SUPPORT"
              title="Find the right support."
              description="Explore the departments and support services that will help students navigate their concerns."
            />
          }
        />
      </Routes>
    </BrowserRouter>
  );
}
