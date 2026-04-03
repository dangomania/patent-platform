import React, { useState, useRef } from 'react';
import { Link } from 'react-router-dom';
import { flattenToAppURL } from '@plone/volto/helpers';

const OAView = ({ content }) => {
  const [translation, setTranslation] = useState(content.translation || '');
  const [translating, setTranslating] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');
  const [saveMsg, setSaveMsg] = useState('');

  const baseUrl = flattenToAppURL(content['@id']);
  const parentPath = content['@id'].split('/').slice(0, -1).join('/');

  const callService = async (endpoint, method = 'POST', body = null) => {
    const url = `${flattenToAppURL(content['@id'])}/${endpoint}`;
    const opts = {
      method,
      headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
      credentials: 'include',
    };
    if (body) opts.body = JSON.stringify(body);
    return fetch(url, opts);
  };

  const handleTranslate = async () => {
    setTranslating(true);
    setError('');
    try {
      const r = await callService('@translate-oa');
      const data = await r.json();
      if (data.error) throw new Error(data.error);
      setTranslation(data.translation);
    } catch (e) {
      setError(e.message);
    } finally {
      setTranslating(false);
    }
  };

  const handleSave = async () => {
    setSaving(true);
    setSaveMsg('');
    try {
      await callService('@save-translation', 'POST', { translation });
      setSaveMsg('保存しました');
      setTimeout(() => setSaveMsg(''), 3000);
    } catch (e) {
      setError(e.message);
    } finally {
      setSaving(false);
    }
  };

  const handleDownloadDocx = () => {
    window.location.href = `${content['@id']}/@download-docx`;
  };

  // Parallel view: split original and translation by newline
  const [parallelMode, setParallelMode] = useState(false);
  const originalLines = (content.original_text || '').split('\n');
  const translationLines = translation.split('\n');
  const [editedLines, setEditedLines] = useState(null);

  const getEditedLines = () => editedLines || translation.split('\n');

  const updateLine = (idx, val) => {
    const lines = getEditedLines();
    const updated = [...lines];
    updated[idx] = val;
    setEditedLines(updated);
    setTranslation(updated.join('\n'));
  };

  return (
    <div className="oa-view">
      <div className="oa-header">
        <Link to={parentPath}>← 仕事に戻る</Link>
        <h1>Office Action ワークスペース</h1>
        <div className="oa-toolbar">
          <button onClick={handleTranslate} disabled={translating} className="btn-primary">
            {translating ? '翻訳中…' : '翻訳実行'}
          </button>
          <button onClick={handleSave} disabled={saving} className="btn-secondary">
            {saving ? '保存中…' : '翻訳を保存'}
          </button>
          <button onClick={handleDownloadDocx} className="btn-success">
            Word出力
          </button>
          <button
            onClick={() => setParallelMode(!parallelMode)}
            className="btn-outline"
          >
            {parallelMode ? '通常表示' : '対訳表示'}
          </button>
        </div>
        {error && <div className="error-msg">{error}</div>}
        {saveMsg && <div className="success-msg">{saveMsg}</div>}
      </div>

      {parallelMode ? (
        /* Parallel (side-by-side) view */
        <div className="parallel-view">
          <div className="parallel-col">
            <h3>原文</h3>
          </div>
          <div className="parallel-col">
            <h3>翻訳</h3>
          </div>
          {originalLines.map((line, i) => (
            <React.Fragment key={i}>
              <div className="parallel-cell original">{line}</div>
              <div className="parallel-cell">
                <textarea
                  value={getEditedLines()[i] || ''}
                  onChange={(e) => updateLine(i, e.target.value)}
                  rows={Math.max(1, Math.ceil((getEditedLines()[i] || '').length / 80))}
                />
              </div>
            </React.Fragment>
          ))}
        </div>
      ) : (
        /* Normal view */
        <div className="normal-view">
          <div className="panel">
            <h3>原文</h3>
            <textarea
              className="text-area-original"
              readOnly
              value={content.original_text || ''}
              rows={20}
            />
          </div>
          <div className="panel">
            <h3>翻訳</h3>
            <textarea
              className="text-area-translation"
              value={translation}
              onChange={(e) => setTranslation(e.target.value)}
              rows={20}
            />
          </div>
        </div>
      )}
    </div>
  );
};

export default OAView;
