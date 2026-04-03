import React, { useState } from 'react';
import { useDispatch } from 'react-redux';
import { Link, useHistory } from 'react-router-dom';
import { updateContent, createContent } from '@plone/volto/actions';

const JobView = ({ content }) => {
  const dispatch = useDispatch();
  const history = useHistory();
  const [status, setStatus] = useState(content.status || 'pending');

  const handleStatusChange = async (e) => {
    const newStatus = e.target.value;
    setStatus(newStatus);
    dispatch(updateContent(content['@id'], { status: newStatus }));
  };

  const openOrCreateOA = async () => {
    const oa = (content.items || []).find(
      (item) => item['@type'] === 'OfficeAction'
    );
    if (oa) {
      history.push(oa['@id']);
    } else {
      // Create a new OA under this job
      const result = await dispatch(
        createContent(content['@id'], {
          '@type': 'OfficeAction',
          title: 'Office Action',
        })
      );
      if (result?.['@id']) history.push(result['@id']);
    }
  };

  const parentPath = content['@id'].split('/').slice(0, -1).join('/');

  return (
    <div className="patent-job-view">
      <div className="job-header">
        <div className="breadcrumb">
          <Link to={parentPath}>← 案件に戻る</Link>
        </div>
        <h1>{content.title || content.job_type}</h1>
        <div className="job-meta">
          <span><strong>カテゴリ:</strong> {content.category}</span>
          <span><strong>種別:</strong> {content.job_type}</span>
          <span><strong>期限:</strong> {content.deadline}</span>
          <span><strong>見積時間:</strong> {content.estimated_hours}h</span>
          <span><strong>優先度:</strong> {content.priority}</span>
        </div>

        <div className="job-status">
          <label>ステータス: </label>
          <select value={status} onChange={handleStatusChange}>
            <option value="pending">未着手</option>
            <option value="in_progress">進行中</option>
            <option value="done">完了</option>
          </select>
        </div>

        {content.description && (
          <div className="job-description">{content.description}</div>
        )}
        {content.notes && (
          <div className="job-notes">{content.notes}</div>
        )}
      </div>

      <div className="job-actions">
        <button className="btn-primary" onClick={openOrCreateOA}>
          OA ワークスペースを開く
        </button>
      </div>
    </div>
  );
};

export default JobView;
