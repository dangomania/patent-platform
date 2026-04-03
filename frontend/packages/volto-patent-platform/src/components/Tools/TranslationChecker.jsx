import React, { useState } from 'react';
import config from '@plone/volto/registry';
const { settings } = config;

const TranslationChecker = () => {
  const [japanese, setJapanese] = useState('');
  const [english, setEnglish] = useState('');
  const [backTranslation, setBackTranslation] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const runBackTranslate = async () => {
    if (!japanese.trim()) return;
    setLoading(true);
    setError('');
    try {
      const apiBase = settings.apiPath;
      const r = await fetch(`${apiBase}/@back-translate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
        credentials: 'include',
        body: JSON.stringify({ text: japanese }),
      });
      const data = await r.json();
      if (data.error) throw new Error(data.error);
      setBackTranslation(data.back_translation);
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="tool-page translation-checker">
      <h1>翻訳精度チェッカー</h1>
      <p>日本語翻訳を英語に逆翻訳して原文と比較します</p>

      <div className="checker-grid">
        <div className="panel">
          <h3>原文（英語）</h3>
          <textarea
            value={english}
            onChange={(e) => setEnglish(e.target.value)}
            rows={16}
            placeholder="1. A device comprising…"
          />
        </div>
        <div className="panel">
          <h3>日本語翻訳</h3>
          <textarea
            value={japanese}
            onChange={(e) => setJapanese(e.target.value)}
            rows={16}
            placeholder="【請求項１】&#10;…を備える装置。"
          />
        </div>
      </div>

      <div className="checker-actions">
        <button onClick={runBackTranslate} disabled={loading} className="btn-primary">
          {loading ? '逆翻訳中…' : '逆翻訳して比較'}
        </button>
        {error && <span className="error-msg">{error}</span>}
      </div>

      {backTranslation && (
        <div className="back-translation-result">
          <h3>逆翻訳結果（参考）</h3>
          <textarea
            readOnly
            value={backTranslation}
            rows={16}
          />
        </div>
      )}
    </div>
  );
};

export default TranslationChecker;
