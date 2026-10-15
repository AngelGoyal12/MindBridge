
import { useEffect, useMemo, useState } from 'react';
import { NavLink } from 'react-router-dom';
import {
  ArrowDownUp,
  ArrowRight,
  ArrowUpRight,
  Search,
  SlidersHorizontal,
  FileText,
  CircleHelp,
} from 'lucide-react';

import { getMyCases } from "../services/caseService";


function formatStoredCase(item) {
  const categoryLabels = {
    ragging_bullying: 'Ragging & bullying',
    emotional_support: 'Emotional support',
    academic_support: 'Academic support',
    hostel_issue: 'Hostel & accommodation',
    financial_assistance: 'Financial assistance',
    other: 'Other support',
  };

  const statusLabels = {
  submitted: 'Submitted',
  in_review: 'Under review',
  in_progress: 'In progress',
  resolved: 'Resolved',
  closed: 'Closed',
};

  return {
    ...item,
    categoryValue: item.categoryValue ?? item.category,
    category:
      categoryLabels[item.category] ??
      item.categoryLabel ??
      item.category,
    statusValue: item.statusValue ?? item.status,
    status: statusLabels[item.status] ?? item.status,
    date: item.date ?? item.created_at?.slice(0, 10) ?? item.createdAt?.slice(0, 10) ?? '',
  };
}

const filters = [
  { label: 'All cases', value: 'all' },
  { label: 'Awaiting / under review', value: 'awaiting_review' },
  { label: 'In progress', value: 'in_progress' },
  { label: 'Resolved', value: 'resolved' },
];

function formatDate(date) {
  if (!date) return 'Date unavailable';

  const parsedDate = new Date(`${date}T00:00:00`);

  if (Number.isNaN(parsedDate.getTime())) {
    return 'Date unavailable';
  }

  return parsedDate.toLocaleDateString('en-IN', {
    day: 'numeric',
    month: 'short',
    year: 'numeric',
  });
}

function StatusBadge({ status, statusValue }) {
  return (
    <span className={`status-badge case-status-${statusValue}`}>
      <span className="status-dot" />
      {status}
    </span>
  );
}

export default function MyCases() {
  const [activeFilter, setActiveFilter] = useState('all');
  const [searchTerm, setSearchTerm] = useState('');
  const [sortOrder, setSortOrder] = useState('newest');

const [cases, setCases] = useState([]);
const [loading, setLoading] = useState(true);
const [error, setError] = useState('');

useEffect(() => {
  let cancelled = false;

  async function loadCases() {
    try {
      setLoading(true);
      setError('');

      const data = await getMyCases();

      if (!cancelled) {
        setCases(data.map(formatStoredCase));
      }
    } catch (err) {
      if (!cancelled) {
        setError(err.message || 'Could not load cases.');
      }
    } finally {
      if (!cancelled) {
        setLoading(false);
      }
    }
  }

  loadCases();

  return () => {
    cancelled = true;
  };
}, []);


  const filteredCases = useMemo(() => {
    const query = searchTerm.trim().toLowerCase();

    return cases
      .filter((item) => {
       const matchesFilter =
  activeFilter === 'all' ||
  (activeFilter === 'awaiting_review'
    ? ['submitted', 'in_review'].includes(item.statusValue)
    : item.statusValue === activeFilter);

        const matchesSearch =
          !query ||
          String(item.id).toLowerCase().includes(query) ||
          item.title.toLowerCase().includes(query) ||
          item.category.toLowerCase().includes(query);

        return matchesFilter && matchesSearch;
      })
      .sort((a, b) =>
        sortOrder === 'newest'
          ? b.date.localeCompare(a.date)
          : a.date.localeCompare(b.date)
      );
  }, [cases, activeFilter, searchTerm, sortOrder]);

  const counts = {
    all: cases.length,

    awaiting_review: cases.filter((item) =>
  ['submitted', 'in_review'].includes(item.statusValue)
).length,

    in_progress: cases.filter(
      (item) => item.statusValue === 'in_progress'
    ).length,

    resolved: cases.filter(
      (item) => item.statusValue === 'resolved'
    ).length,
  };

  return (
    <main className="my-cases page-container">
      <NavLink to="/dashboard" className="back-link">
        <ArrowRight className="back-arrow" size={15} />
        Back to your space
      </NavLink>

      <section className="cases-intro">
        <div className="eyebrow">
          <span className="eyebrow-dot" />
          YOUR SUPPORT JOURNEY
        </div>
        <h1>Your concerns, <em>in one place.</em></h1>
        <p>
          Keep track of what you've shared, see where things stand,
          and check for updates when you're ready.
        </p>
      </section>

      <section className="cases-summary">
        <div>
          <span className="section-overline">YOUR RECORD</span>
          <h2>Every step matters.</h2>
        </div>
        <div className="cases-summary-count">
          <strong>{String(counts.all).padStart(2, '0')}</strong>
          <span>demo cases</span>
        </div>
      </section>

      <section className="cases-workspace">
        <div className="cases-toolbar">
          <div className="cases-toolbar-title">
            <h2>Case history</h2>
            <span>{filteredCases.length} shown</span>
          </div>

          <div className="cases-toolbar-actions">
            <label className="case-search">
              <Search size={16} />
              <input
                type="search"
                placeholder="Search cases..."
                value={searchTerm}
                onChange={(event) => setSearchTerm(event.target.value)}
                aria-label="Search cases by reference, title or category"
              />
            </label>

            <button
              type="button"
              className="sort-button"
              onClick={() =>
                setSortOrder((current) =>
                  current === 'newest' ? 'oldest' : 'newest'
                )
              }
              aria-label={`Sort by ${sortOrder === 'newest' ? 'oldest' : 'newest'} first`}
            >
              <ArrowDownUp size={15} />
              {sortOrder === 'newest' ? 'Newest' : 'Oldest'}
            </button>
          </div>
        </div>

        <div className="case-filter-row" aria-label="Filter cases">
          {filters.map((filter) => (
            <button
              key={filter.value}
              type="button"
              className={`case-filter ${activeFilter === filter.value ? 'active' : ''}`}
              onClick={() => setActiveFilter(filter.value)}
              aria-pressed={activeFilter === filter.value}
            >
              {filter.label}
              <span>{counts[filter.value]}</span>
            </button>
          ))}
        </div>

        <div className="cases-results">

{loading ? (
  <p role="status">Loading your cases...</p>
) : error ? (
  <p role="alert">Could not load cases: {error}</p>
) : null}

          {filteredCases.length > 0 ? (
            filteredCases.map((item, index) => (
              <article
                className="case-history-card"
                key={item.id}
                style={{ animationDelay: `${index * 70}ms` }}
              >
                <div className="case-history-icon">
                  <FileText size={19} strokeWidth={1.5} />
                </div>

                <div className="case-history-content">
                  <div className="case-history-meta">
                    <span>{item.id}</span>
                    <span className="case-meta-divider">·</span>
                    <span>{formatDate(item.date)}</span>
                  </div>

                  <h3>{item.title}</h3>
                  <p>{item.category}</p>
                </div>

                <div className="case-history-end">
                  <StatusBadge
                    status={item.status}
                    statusValue={item.statusValue}
                  />
                  <NavLink
                    to={`/cases/${item.id}`}
                    state={{ caseData: item }}
                    className="case-open-link"
                  >
                    View details <ArrowUpRight size={15} />
                  </NavLink>
                </div>
              </article>
            ))
          ) : (
            <div className="cases-empty">
              <div className="cases-empty-icon">
                {searchTerm ? <Search size={22} /> : <CircleHelp size={22} />}
              </div>
              <h3>No matching cases</h3>
              <p>
                Try another search term or select a different status filter.
              </p>
              <button
                type="button"
                className="secondary-button"
                onClick={() => {
                  setSearchTerm('');
                  setActiveFilter('all');
                }}
              >
                Clear filters
              </button>
            </div>
          )}
        </div>
      </section>

      <section className="cases-bottom-note">
        <SlidersHorizontal size={17} />
        <p>
          These are sample records for the MindBridge prototype.
          The connected version will show only cases your account is
          authorized to access.
        </p>
      </section>
    </main>
  );
}
