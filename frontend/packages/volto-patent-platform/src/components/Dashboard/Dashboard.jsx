import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';

const LEVEL_COLORS = {
  empty:  '#f8fafc',
  low:    '#bbf7d0',
  medium: '#fde68a',
  high:   '#fca5a5',
};

const Dashboard = () => {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    fetch('/@@dashboard-data', {
      headers: { Accept: 'application/json' },
      credentials: 'include',
    })
      .then((r) => r.json())
      .then((d) => { setData(d); setLoading(false); })
      .catch((e) => { setError(e.message); setLoading(false); });
  }, []);

  if (loading) return <div className="dashboard loading">読み込み中…</div>;
  if (error) return <div className="dashboard error">{error}</div>;

  const today = data.today;

  return (
    <div className="dashboard">
      <h1>ダッシュボード</h1>

      {/* Workload calendar */}
      <div className="section-card">
        <h2>28日間ワークロード</h2>
        <div className="calendar-grid">
          {data.calendar.map((day) => (
            <div
              key={day.date}
              className={`cal-day ${day.date === today ? 'today' : ''}`}
              style={{ background: LEVEL_COLORS[day.level] }}
              title={`${day.date}: ${day.hours}h`}
            >
              <span className="cal-date">{day.date.slice(8)}</span>
              {day.hours > 0 && (
                <span className="cal-hours">{day.hours}h</span>
              )}
            </div>
          ))}
        </div>
      </div>

      {/* Overdue */}
      {data.overdue.length > 0 && (
        <div className="section-card overdue-section">
          <h2>期限切れ ({data.overdue.length}件)</h2>
          <JobList jobs={data.overdue} />
        </div>
      )}

      {/* Upcoming */}
      <div className="section-card">
        <h2>今後28日間の仕事 ({data.upcoming.length}件)</h2>
        <JobList jobs={data.upcoming} />
      </div>
    </div>
  );
};

const JobList = ({ jobs }) => (
  <table className="jobs-table">
    <thead>
      <tr>
        <th>期限</th>
        <th>案件</th>
        <th>種別</th>
        <th>優先度</th>
        <th>見積時間</th>
        <th>ステータス</th>
      </tr>
    </thead>
    <tbody>
      {jobs.map((job) => (
        <tr key={job.uid}>
          <td>{job.deadline}</td>
          <td>{job.case_ref}</td>
          <td><Link to={job.url}>{job.title}</Link></td>
          <td>{'★'.repeat(4 - (job.priority || 3))}</td>
          <td>{job.estimated_hours}h</td>
          <td>{job.status}</td>
        </tr>
      ))}
      {jobs.length === 0 && (
        <tr><td colSpan={6} style={{ color: '#9ca3af', textAlign: 'center' }}>なし</td></tr>
      )}
    </tbody>
  </table>
);

export default Dashboard;
