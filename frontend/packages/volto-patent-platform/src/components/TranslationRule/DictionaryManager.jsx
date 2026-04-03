import React, { useState, useEffect } from 'react';
import config from '@plone/volto/registry';
const { settings } = config;

const DictionaryManager = () => {
  const [rules, setRules] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [newRule, setNewRule] = useState({
    pattern: '', replacement: '', rule_type: 'exact', sort_order: 0,
  });

  const fetchRules = async () => {
    setLoading(true);
    try {
      const apiBase = settings.apiPath;
      const r = await fetch(`${apiBase}/@translation-rules`, {
        headers: { Accept: 'application/json' },
        credentials: 'include',
      });
      const data = await r.json();
      setRules(data.rules || []);
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetchRules(); }, []);

  const handleAdd = async () => {
    if (!newRule.pattern || !newRule.replacement) return;
    try {
      const apiBase = settings.apiPath;
      await fetch(`${apiBase}/@translation-rules`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
        credentials: 'include',
        body: JSON.stringify(newRule),
      });
      setNewRule({ pattern: '', replacement: '', rule_type: 'exact', sort_order: 0 });
      fetchRules();
    } catch (e) {
      setError(e.message);
    }
  };

  const handleToggle = async (rule) => {
    try {
      await fetch(`${rule.url}/@update`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
        credentials: 'include',
        body: JSON.stringify({ enabled: !rule.enabled }),
      });
      fetchRules();
    } catch (e) {
      setError(e.message);
    }
  };

  const handleDelete = async (rule) => {
    if (!window.confirm(`「${rule.pattern}」を削除しますか？`)) return;
    try {
      await fetch(`${rule.url}/@delete`, {
        method: 'DELETE',
        headers: { Accept: 'application/json' },
        credentials: 'include',
      });
      fetchRules();
    } catch (e) {
      setError(e.message);
    }
  };

  return (
    <div className="tool-page dictionary-manager">
      <h1>翻訳辞書</h1>
      <p>翻訳前処理の用語置換ルールを管理します</p>

      {error && <div className="error-msg">{error}</div>}

      <div className="add-rule-form step-card">
        <h3>ルールを追加</h3>
        <div className="form-row">
          <input
            value={newRule.pattern}
            onChange={(e) => setNewRule({ ...newRule, pattern: e.target.value })}
            placeholder="置換前（パターン）"
          />
          <input
            value={newRule.replacement}
            onChange={(e) => setNewRule({ ...newRule, replacement: e.target.value })}
            placeholder="置換後"
          />
          <select
            value={newRule.rule_type}
            onChange={(e) => setNewRule({ ...newRule, rule_type: e.target.value })}
          >
            <option value="exact">完全一致</option>
            <option value="regex">正規表現</option>
          </select>
          <input
            type="number"
            value={newRule.sort_order}
            onChange={(e) => setNewRule({ ...newRule, sort_order: parseInt(e.target.value) || 0 })}
            placeholder="順序"
            style={{ width: 70 }}
          />
          <button onClick={handleAdd} className="btn-primary">追加</button>
        </div>
      </div>

      {loading ? (
        <p>読み込み中…</p>
      ) : (
        <table className="dict-table">
          <thead>
            <tr>
              <th>順序</th>
              <th>パターン</th>
              <th>置換後</th>
              <th>種別</th>
              <th>有効</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {rules.map((rule) => (
              <tr key={rule.uid} className={rule.enabled ? '' : 'disabled-row'}>
                <td>{rule.sort_order}</td>
                <td><code>{rule.pattern}</code></td>
                <td><code>{rule.replacement}</code></td>
                <td>{rule.rule_type === 'regex' ? '正規表現' : '完全一致'}</td>
                <td>
                  <input
                    type="checkbox"
                    checked={rule.enabled}
                    onChange={() => handleToggle(rule)}
                  />
                </td>
                <td>
                  <button onClick={() => handleDelete(rule)} className="btn-danger-sm">
                    削除
                  </button>
                </td>
              </tr>
            ))}
            {rules.length === 0 && (
              <tr><td colSpan={6} style={{ textAlign: 'center', color: '#9ca3af' }}>ルールがありません</td></tr>
            )}
          </tbody>
        </table>
      )}
    </div>
  );
};

export default DictionaryManager;
