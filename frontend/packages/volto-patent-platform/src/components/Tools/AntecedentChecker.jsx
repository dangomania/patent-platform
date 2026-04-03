import React, { useState } from 'react';
import { flattenToAppURL } from '@plone/volto/helpers';
import { settings } from '@plone/volto/config';

const esc = (s) =>
  String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');

const AntecedentChecker = () => {
  const [text, setText] = useState('');
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const runCheck = async () => {
    if (!text.trim()) return;
    setLoading(true);
    setError('');
    try {
      const apiBase = settings.apiPath;
      const r = await fetch(`${apiBase}/@antecedent-check`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
        credentials: 'include',
        body: JSON.stringify({ text }),
      });
      const data = await r.json();
      if (data.error) throw new Error(data.error);
      setResult(data);
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };

  const highlightRefs = (claimText, terms) => {
    let h = esc(claimText);
    for (const term of terms) {
      for (const pfx of ['前記', '該']) {
        const pat = esc(pfx + term);
        h = h.replaceAll(
          pat,
          `<mark class="hl-ref">${esc(pfx)}<strong>${esc(term)}</strong></mark>`
        );
      }
    }
    return h;
  };

  const highlightSnippet = (snippet, termStart, termLen) => {
    const before = esc(snippet.slice(0, termStart));
    const match = esc(snippet.slice(termStart, termStart + termLen));
    const after = esc(snippet.slice(termStart + termLen));
    return `${before}<mark class="hl-found"><strong>${match}</strong></mark>${after}`;
  };

  return (
    <div className="tool-page antecedent-checker">
      <h1>前記/該 先行詞チェッカー</h1>
      <p>SudachiPy形態素解析による名詞句抽出・先行詞確認</p>

      <div className="step-card">
        <div className="step-head">
          <span className="step-title">1. 請求項を入力</span>
          <button onClick={runCheck} disabled={loading} className="btn-primary">
            {loading ? '解析中…' : 'チェック実行'}
          </button>
        </div>
        <textarea
          value={text}
          onChange={(e) => setText(e.target.value)}
          rows={14}
          placeholder="【請求項１】&#10;照明装置であって、…&#10;&#10;【請求項２】&#10;前記照明装置において…"
          className="claims-input"
        />
        {error && <div className="error-msg">{error}</div>}
      </div>

      {result && (
        <div className="step-card results-card">
          <h2>2. チェック結果</h2>
          <div className="results-scroll">
            <table className="ant-table">
              <thead>
                <tr>
                  <th>請求項</th>
                  <th>クレーム全文</th>
                  <th>参照語</th>
                  <th>先行詞</th>
                  <th>発見クレーム</th>
                  <th>コンテキスト</th>
                </tr>
              </thead>
              <tbody>
                {result.claims.flatMap((claim) => {
                  if (!claim.refs.length) return [];
                  const terms = claim.refs.map((r) => r.term);
                  const claimHtml = highlightRefs(claim.text, terms);

                  return claim.refs.map((ref, ri) => {
                    const badge = ref.self_found
                      ? <span className="badge-self">同一クレーム内</span>
                      : ref.preceding_nums.length
                      ? <span className="badge-ok">○ あり</span>
                      : <span className="badge-ng">✗ なし</span>;

                    const chainStrs = (ref.dep_chains || []).map((ch) =>
                      ch.join(' › ')
                    );
                    const foundNums = chainStrs.length
                      ? chainStrs.join('\n')
                      : ref.self_found
                      ? ''
                      : '—';

                    const ctxBlocks = ref.contexts.map((ctx, ci) => {
                      const isSelf = ctx.label.includes('同一');
                      return (
                        <div key={ci} className={`ctx-block${isSelf ? ' self' : ''}`}>
                          <span className="ctx-label">{ctx.label}</span>
                          <span
                            dangerouslySetInnerHTML={{
                              __html:
                                '…' +
                                highlightSnippet(ctx.snippet, ctx.term_start, ctx.term_len) +
                                '…',
                            }}
                          />
                        </div>
                      );
                    });

                    return (
                      <tr key={`${claim.num}-${ri}`} className={ri === 0 ? 'group-start' : ''}>
                        {ri === 0 && (
                          <>
                            <td rowSpan={claim.refs.length} className="claim-num-cell">
                              請求項{claim.num}
                            </td>
                            <td
                              rowSpan={claim.refs.length}
                              className="claim-text-cell"
                              dangerouslySetInnerHTML={{ __html: claimHtml }}
                            />
                          </>
                        )}
                        <td>
                          <code>{ref.term}</code>
                        </td>
                        <td className="badge-cell">{badge}</td>
                        <td className="chain-cell" style={{ whiteSpace: 'pre' }}>
                          {foundNums}
                        </td>
                        <td className="ctx-cell">
                          {ctxBlocks.length ? ctxBlocks : <span className="no-ctx">先行詞なし</span>}
                        </td>
                      </tr>
                    );
                  });
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
};

export default AntecedentChecker;
