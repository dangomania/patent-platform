import React, { useState } from 'react';
import { useDispatch } from 'react-redux';
import { Link } from 'react-router-dom';
import { updateContent } from '@plone/volto/actions';

const STATUS_LABELS = {
  active:         '対応中',
  action_needed:  '要対応',
  waiting_client: 'クライアント待ち',
  no_task:        'タスクなし',
  abandoned:      '取り下げ',
  transferred:    '移管済み',
};

const STATUS_COLORS = {
  active:         '#2563eb',
  action_needed:  '#dc2626',
  waiting_client: '#d97706',
  no_task:        '#6b7280',
  abandoned:      '#9ca3af',
  transferred:    '#7c3aed',
};

const CaseView = ({ content }) => {
  const dispatch = useDispatch();
  const [status, setStatus] = useState(content.status || 'active');

  const handleStatusChange = async (e) => {
    const newStatus = e.target.value;
    setStatus(newStatus);
    dispatch(updateContent(content['@id'], { status: newStatus }));
  };

  const jobs = content.items || [];

  return (
    <div className="patent-case-view">
      <div className="case-header">
        <h1>{content.title}</h1>
        <div className="case-meta">
          <span className="meta-item"><strong>整理番号:</strong> {content.case_ref}</span>
          <span className="meta-item"><strong>クライアント:</strong> {content.client || '—'}</span>
          <span className="meta-item"><strong>出願番号:</strong> {content.app_number || '—'}</span>
          <span className="meta-item"><strong>国:</strong> {content.country}</span>
          <span className="meta-item"><strong>技術分野:</strong> {content.technology || '—'}</span>
        </div>
        <div className="case-status">
          <label>ステータス: </label>
          <select
            value={status}
            onChange={handleStatusChange}
            style={{ color: STATUS_COLORS[status], fontWeight: 600 }}
          >
            {Object.entries(STATUS_LABELS).map(([val, label]) => (
              <option key={val} value={val}>{label}</option>
            ))}
          </select>
        </div>
        {content.notes && (
          <div className="case-notes">{content.notes}</div>
        )}
      </div>

      <div className="case-jobs">
        <div className="section-header">
          <h2>仕事一覧</h2>
          <Link to={`${content['@id']}/++add++PatentJob`} className="btn-add">
            + 仕事を追加
          </Link>
        </div>
        {jobs.length === 0 ? (
          <p className="empty-msg">仕事がありません</p>
        ) : (
          <table className="jobs-table">
            <thead>
              <tr>
                <th>種別</th>
                <th>説明</th>
                <th>期限</th>
                <th>見積時間</th>
                <th>ステータス</th>
                <th>優先度</th>
              </tr>
            </thead>
            <tbody>
              {jobs.map((job) => (
                <tr key={job['@id']} className={`status-${job.status}`}>
                  <td><Link to={job['@id']}>{job.job_type}</Link></td>
                  <td>{job.description || '—'}</td>
                  <td>{job.deadline}</td>
                  <td>{job.estimated_hours}h</td>
                  <td>{job.status}</td>
                  <td>{'★'.repeat(4 - (job.priority || 3))}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
};

export default CaseView;
