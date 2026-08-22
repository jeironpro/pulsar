/* PULSAR landing — playground.js
   Ejecuta el parser auténtico (pulsar.py) en el navegador vía Pyodide.
   Pyodide se descarga solo cuando el usuario lo pide. */
(() => {
  'use strict';

  const $ = (s, c = document) => c.querySelector(s);

  const input = $('#psr-input');
  const runBtn = $('#pg-run');
  const status = $('#pg-status');
  const outEl = $('#pg-out');
  const errEl = $('#pg-error');
  const errMsg = $('#pg-error-msg');

  if (!input || !runBtn) return;

  /* ============ Ejemplos precargados ============ */
  const EXAMPLES = {
    contacts: `-> contacto
    nombre >> "Ana Torres"
    edad >> 25
    activo >> true
    skills >> python | rust | go

    -> direccion
        ciudad >> Madrid
        cp >> 28000
    <-

<-

-> contacto
    nombre >> "Bruno Díaz"
    edad >> 41
    skills >> javascript | html
<-`,
    server: `-> app
    nombre >> "Mi Servicio"
    version >> 1.4
    debug >> false
    tags >> web | api

    limites >> { rpm >> 500 | timeout >> 30 }

    -> base_datos
        url >> postgres://localhost/app
        pool >> 8
    <-
<-`,
    errors: `-> base_datos
    url >> postgres://localhost/app
    pool >> 5

-> cache
    ttl >> 120
<-
:: falta cerrar el bloque base_datos`
  };

  const setExample = name => {
    if (EXAMPLES[name]) input.value = EXAMPLES[name];
  };
  setExample('contacts');

  document.querySelectorAll('.chip[data-example]').forEach(chip => {
    chip.addEventListener('click', () => {
      document.querySelectorAll('.chip[data-example]').forEach(c => c.classList.remove('is-active'));
      chip.classList.add('is-active');
      setExample(chip.dataset.example);
      resetOutput();
    });
  });

  /* El resaltado vive en assets/js/lib/highlight.js (window.PSRHl). */
  const hlJson = window.PSRHl.hlJson;

  const resetOutput = () => {
    outEl.hidden = true;
    errEl.hidden = true;
    status.textContent = '';
  };

  /* ============ Estado del motor ============ */
  let pyodide = null;
  let loadingPyodide = null;
  let parserReady = false;

  const PYODIDE_URL = 'https://cdn.jsdelivr.net/pyodide/v0.27.2/full/pyodide.js';
  const INDEX_URL = 'https://cdn.jsdelivr.net/pyodide/v0.27.2/full/';

  const loadScript = src => new Promise((res, rej) => {
    if (window.loadPyodide) return res();
    const s = document.createElement('script');
    s.src = src;
    s.onload = res;
    s.onerror = () => rej(new Error('No se pudo descargar Pyodide'));
    document.head.appendChild(s);
  });

  const ensureEngine = async () => {
    if (parserReady) return;

    if (!loadingPyodide) {
      loadingPyodide = (async () => {
        status.textContent = 'Descargando Python (WebAssembly)… ~10 MB, solo una vez';
        await loadScript(PYODIDE_URL);
        pyodide = await window.loadPyodide({ indexURL: INDEX_URL });

        status.textContent = 'Cargando pulsar.py…';
        const resp = await fetch('./pulsar.py');
        if (!resp.ok) throw new Error(`No se pudo cargar pulsar.py (${resp.status})`);
        const src = await resp.text();
        pyodide.FS.writeFile('/pulsar.py', src);
        pyodide.runPython('import sys; sys.path.insert(0, "/"); import pulsar');
        parserReady = true;
        status.textContent = 'Motor listo: parser real ejecutándose en tu navegador.';
      })();
    }
    await loadingPyodide;
  };

  /* ============ Parseo ============ */
  const RUNNER = `
import json as _json
from pulsar import lex_psr, parse, build_document, PSRLexError, PSRParseError

def _run(src):
    try:
        ast = parse(lex_psr(src))
        data = build_document(ast)
        payload = {"ok": True, "data": _json.dumps(data, indent=2, ensure_ascii=False)}
    except (PSRLexError, PSRParseError) as e:
        payload = {"ok": False, "error": str(e)}
    return _json.dumps(payload, ensure_ascii=False)
`;

  const parseSource = source => {
    pyodide.globals.set('__psr_src', source);
    pyodide.runPython(RUNNER);
    const raw = pyodide.runPython('_run(__psr_src)');
    return JSON.parse(String(raw));
  };

  runBtn.addEventListener('click', async () => {
    runBtn.disabled = true;
    errEl.hidden = true;
    outEl.hidden = true;

    try {
      await ensureEngine();
      const result = parseSource(input.value);

      if (result.ok) {
        status.textContent = 'Parseado con éxito.';
        outEl.innerHTML = hlJson(result.data);
        outEl.hidden = false;
      } else {
        status.textContent = 'El parser encontró un error.';
        errMsg.textContent = result.error;
        errEl.hidden = false;
      }
    } catch (e) {
      status.textContent = '';
      errMsg.textContent =
        e.message === 'No se pudo descargar Pyodide' || /pulsar\.py/.test(e.message)
          ? `${e.message}. Revisa tu conexión o inténtalo de nuevo.`
          : `Fallo inesperado: ${e.message}`;
      errEl.hidden = false;
    } finally {
      runBtn.disabled = false;
    }
  });
})();
