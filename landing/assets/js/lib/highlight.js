/* PULSAR landing — lib/highlight.js
   Resaltado de sintaxis compartido (.psr y JSON).
   Expone window.PSRHl y colorea los bloques estáticos del documento. */
(() => {
  'use strict';

  const esc = (s) =>
    s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');

  const typeVal = (v) => {
    v = v.trim();
    if (/^".*"$/s.test(v)) return `<span class="tk-str">${esc(v)}</span>`;
    if (/^(true|false)$/i.test(v))
      return `<span class="tk-bool">${esc(v)}</span>`;
    if (/^-?\d+(\.\d+)?$/.test(v))
      return `<span class="tk-num">${esc(v)}</span>`;
    return esc(v);
  };

  const splitList = (rest) =>
    rest
      .split('|')
      .map((p) => typeVal(p))
      .join(' <span class="tk-op">|</span> ');

  const hlPsrLine = (line) => {
    const ind = (line.match(/^\s*/) || [''])[0];
    let body = line.slice(ind.length);

    // comentario fuera de comillas
    let ci = -1,
      q = false;
    for (let i = 0; i < body.length; i++) {
      if (body[i] === '"') q = !q;
      if (!q && body[i] === ':' && body[i + 1] === ':') {
        ci = i;
        break;
      }
    }
    let comPart = '';
    if (ci >= 0) {
      comPart = `<span class="tok-comment">${esc(body.slice(ci))}</span>`;
      body = body.slice(0, ci).replace(/\s+$/, '');
    }
    if (!body.trim()) return esc(ind) + comPart;

    if (/^->/.test(body)) {
      const name = body.replace(/^->\s*/, '');
      return (
        esc(ind) +
        `<span class="tk-block">-&gt;</span> <span class="tk-block">${esc(name)}</span>` +
        comPart
      );
    }
    if (/^<-/.test(body))
      return esc(ind) + '<span class="tk-block">&lt;-</span>' + comPart;

    const am = body.match(/^([A-Za-z_][\w-]*)(\s*)(>>)(\s*)([\s\S]*)$/);
    if (am) {
      let valHtml;
      const rest = am[5];
      if (rest.trim() === '<<') {
        valHtml = '<span class="tk-op">&lt;&lt;</span>';
      } else if (rest.includes('|')) {
        valHtml = splitList(rest);
      } else if (/^\{.*\}$/.test(rest.trim())) {
        valHtml = esc(rest.trim())
          .replace(/\{|\}/g, (m) => `<span class="tk-op">${m}</span>`)
          .replace(/&gt;&gt;/g, ' <span class="tk-op">&gt;&gt;</span> ');
      } else {
        valHtml = typeVal(rest);
      }
      return (
        esc(ind) +
        `<span class="tk-key">${esc(am[1])}</span>` +
        am[2] +
        '<span class="tk-op">&gt;&gt;</span>' +
        am[4] +
        valHtml +
        comPart
      );
    }

    return esc(ind) + esc(body) + comPart;
  };

  const hlPsr = (t) => t.split('\n').map(hlPsrLine).join('\n');

  const hlJson = (t) =>
    esc(t).replace(
      /("(?:\\.|[^"\\])*")(\s*:)?|\b(true|false|null)\b|-?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?/g,
      (m, str, col, bool) => {
        if (str)
          return col
            ? `<span class="j-key">${str}</span>${col}`
            : `<span class="j-str">${str}</span>`;
        if (bool) return `<span class="j-bool">${m}</span>`;
        return `<span class="j-num">${m}</span>`;
      },
    );

  // colorear bloques estáticos presentes en el documento
  document.querySelectorAll('.code-psr').forEach((el) => {
    el.innerHTML = hlPsr(el.textContent);
  });
  document.querySelectorAll('.code-json').forEach((el) => {
    el.innerHTML = hlJson(el.textContent);
  });

  window.PSRHl = { esc, hlPsr, hlPsrLine, hlJson };
})();
