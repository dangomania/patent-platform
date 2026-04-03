import React, { useState } from 'react';

// Pure client-side: no backend call needed

const FW = (s) => s.replace(/[０-９]/g, (c) => String.fromCharCode(c.charCodeAt(0) - 0xfee0));
const toInt = (s) => parseInt(FW(String(s)));

function parseJa(text) {
  const claims = [];
  const re = /【請求項([０-９\d]+)】([\s\S]*?)(?=【請求項[０-９\d]+】|$)/g;
  let m;
  while ((m = re.exec(text)) !== null)
    claims.push({ num: toInt(m[1]), text: m[2].trim() });
  if (claims.length) return claims;
  const lines = text.split('\n');
  let cur = null;
  for (const line of lines) {
    const m2 =
      line.match(/^(?:請求項|クレーム)\s*([０-９\d]+)[．.。\s](.*)/) ||
      line.match(/^([０-９\d]+)[．.)）]\s*(.*)/);
    if (m2) { if (cur) claims.push(cur); cur = { num: toInt(m2[1]), text: m2[2] }; }
    else if (cur) cur.text += '\n' + line;
  }
  if (cur) claims.push(cur);
  return claims;
}

function parseEn(text) {
  const claims = [];
  const lines = text.split('\n');
  let cur = null;
  for (const line of lines) {
    const m = line.match(/^(\d+)[.)]\s+(.*)/);
    if (m) { if (cur) claims.push(cur); cur = { num: parseInt(m[1]), text: m[2] }; }
    else if (cur) cur.text += ' ' + line.trim();
  }
  if (cur) claims.push(cur);
  return claims;
}

function depsJa(text, own) {
  const nums = [];
  const re = /請求項([０-９\d]+)/g;
  let m;
  while ((m = re.exec(text)) !== null) {
    const n = toInt(m[1]); if (n !== own) nums.push(n);
  }
  return [...new Set(nums)];
}

function depsEn(text, own) {
  const nums = [];
  const re = /\bclaims?\s+([\d,\s\-–—toandr]+)/gi;
  let m;
  while ((m = re.exec(text)) !== null) {
    for (const part of m[1].split(/[,\s]+(?:and|or)?\s*/)) {
      const range = part.match(/(\d+)\s*[-–—to]+\s*(\d+)/);
      if (range) { for (let i = parseInt(range[1]); i <= parseInt(range[2]); i++) nums.push(i); }
      else { const n = parseInt(part); if (!isNaN(n) && n !== own) nums.push(n); }
    }
  }
  return [...new Set(nums.filter((n) => n !== own))];
}

const MultiClaimChecker = () => {
  const [text, setText] = useState('');
  const [lang, setLang] = useState('auto');
  const [rows, setRows] = useState(null);
  const [summary, setSummary] = useState(null);

  const runCheck = () => {
    if (!text.trim()) return;
    const useLang = lang === 'auto' ? (/[ぁ-ん]/.test(text) ? 'ja' : 'en') : lang;
    const claims = useLang === 'ja' ? parseJa(text) : parseEn(text.replace(/\r\n?/g, '\n'));
    if (!claims.length) { alert('請求項を認識できませんでした'); return; }

    const depsOf = {};
    for (const c of claims)
      depsOf[c.num] = useLang === 'ja' ? depsJa(c.text, c.num) : depsEn(c.text, c.num);

    const isMultiDep = (n) => (depsOf[n] || []).length >= 2;
    const isMultiMulti = (n) => isMultiDep(n) && (depsOf[n] || []).some((p) => isMultiDep(p));

    let mmCount = 0, multiCount = 0;
    const tableRows = claims.map((c) => {
      const deps = depsOf[c.num] || [];
      const multi = isMultiDep(c.num);
      const mm = isMultiMulti(c.num);
      if (mm) mmCount++;
      if (multi) multiCount++;
      return { num: c.num, deps, multi, mm, lang: useLang };
    });

    setRows(tableRows);
    setSummary({ mmCount, multiCount });
  };

  return (
    <div className="tool-page multi-claim-checker">
      <h1>多項引用（Multi-Multi）チェッカー</h1>
      <p>多項引用クレームが別の多項引用クレームを引用していないか確認します</p>

      <div className="step-card">
        <div className="step-head">
          <span className="step-title">1. 請求項を入力</span>
          <div className="step-actions">
            <select value={lang} onChange={(e) => setLang(e.target.value)}>
              <option value="auto">自動判定</option>
              <option value="ja">日本語</option>
              <option value="en">English</option>
            </select>
            <button onClick={runCheck} className="btn-primary">チェック実行</button>
          </div>
        </div>
        <textarea
          value={text}
          onChange={(e) => setText(e.target.value)}
          rows={14}
          className="claims-input"
          placeholder="【請求項１】…&#10;【請求項２】請求項１に記載の…&#10;【請求項３】請求項１または２に記載の…"
        />
      </div>

      {rows && (
        <div className="step-card">
          <div className="step-head">
            <span className="step-title">2. 結果</span>
            {summary && (
              <span className={summary.mmCount > 0 ? 'text-danger' : 'text-success'}>
                {summary.mmCount > 0
                  ? `⚠ Multi-Multi ${summary.mmCount}件 / 多項引用 ${summary.multiCount}件`
                  : summary.multiCount > 0
                  ? `✓ Multi-Multiなし（多項引用 ${summary.multiCount}件）`
                  : '✓ 問題なし'}
              </span>
            )}
          </div>
          <table className="mc-table">
            <thead>
              <tr>
                <th>請求項</th>
                <th>種別</th>
                <th>引用クレーム</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((row) => (
                <tr key={row.num} className={row.mm ? 'mm-row' : ''}>
                  <td><strong>{row.lang === 'ja' ? `請求項${row.num}` : `Claim ${row.num}`}</strong></td>
                  <td>
                    {row.mm ? <span className="badge-mm">⚠ Multi-Multi</span>
                      : row.multi ? <span className="badge-multi">多項引用</span>
                      : row.deps.length === 1 ? <span className="badge-single">従属</span>
                      : <span className="badge-indep">独立</span>}
                  </td>
                  <td>
                    {row.deps.length
                      ? row.deps.map((d) => (
                          <span key={d} className="dep-pill">
                            {row.lang === 'ja' ? `請求項${d}` : `Claim ${d}`}
                          </span>
                        ))
                      : '—'}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
};

export default MultiClaimChecker;
