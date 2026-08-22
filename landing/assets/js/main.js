/* PULSAR landing — main.js */
(() => {
  'use strict';

  document.documentElement.classList.add('js');

  const REDUCED = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  if (REDUCED) document.documentElement.classList.add('reduced-motion');

  const $ = (s, c = document) => c.querySelector(s);
  const $$ = (s, c = document) => [...c.querySelectorAll(s)];

  /* ============ Carga diferida de librerías CDN ============
     gsap, anime.js, Swiper y Floating UI se descargan solo cuando la
     sección que los usa entra en el viewport (IntersectionObserver).
     Se inyectan como <script> clásico en lugar de import(): con import()
     los UMD se evaluarían como módulo ES, donde `this` de nivel superior
     es undefined, lo que rompe anime.js (n.anime = ...). */
  const CDN = {
    gsap: 'https://cdn.jsdelivr.net/npm/gsap@3.13.0/dist/gsap.min.js',
    scrollTrigger:
      'https://cdn.jsdelivr.net/npm/gsap@3.13.0/dist/ScrollTrigger.min.js',
    anime: 'https://cdn.jsdelivr.net/npm/animejs@3.2.2/lib/anime.min.js',
    swiper: 'https://cdn.jsdelivr.net/npm/swiper@11/swiper-bundle.min.js',
    floatingCore:
      'https://cdn.jsdelivr.net/npm/@floating-ui/core@1.6.9/dist/floating-ui.core.umd.min.js',
    floating:
      'https://cdn.jsdelivr.net/npm/@floating-ui/dom@1.6.13/dist/floating-ui.dom.umd.min.js',
  };

  const _scripts = new Map();
  const loadScript = (url) => {
    if (!_scripts.has(url)) {
      _scripts.set(
        url,
        new Promise((res, rej) => {
          const s = document.createElement('script');
          s.src = url;
          s.async = false; // ejecución en orden: respeta dependencias (gsap → ScrollTrigger, core → dom)
          s.onload = () => res();
          s.onerror = () => {
            _scripts.delete(url);
            rej(new Error('Fallo al cargar ' + url));
          };
          document.head.appendChild(s);
        }),
      );
    }
    return _scripts.get(url);
  };

  const loadGsap = () =>
    loadScript(CDN.gsap)
      .then(() => loadScript(CDN.scrollTrigger))
      .then(() => {
        const { gsap, ScrollTrigger } = window;
        gsap.registerPlugin(ScrollTrigger);
        return gsap;
      });
  const loadAnime = () => loadScript(CDN.anime).then(() => window.anime);
  const loadSwiper = () => loadScript(CDN.swiper).then(() => window.Swiper);
  const loadFloating = () =>
    loadScript(CDN.floatingCore)
      .then(() => loadScript(CDN.floating))
      .then(() => window.FloatingUIDOM);

  const onceVisible = (el, cb, rootMargin = '0px 0px -8% 0px') => {
    if (!el) return;
    if (!('IntersectionObserver' in window)) {
      cb();
      return;
    }
    const io = new IntersectionObserver(
      ([e]) => {
        if (e.isIntersecting) {
          io.disconnect();
          cb();
        }
      },
      { rootMargin, threshold: 0.05 },
    );
    io.observe(el);
  };

  /* El resaltado de sintaxis vive en assets/js/lib/highlight.js (compartido
     con playground.js para evitar duplicación). */

  /* ============ Campo de estrellas ============ */
  const makeStars = (canvas, count = 150) => {
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    let stars = [],
      raf = null,
      W = 0,
      H = 0;

    const resize = () => {
      const dpr = Math.min(window.devicePixelRatio || 1, 2);
      W = canvas.clientWidth;
      H = canvas.clientHeight;
      canvas.width = W * dpr;
      canvas.height = H * dpr;
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      const n = Math.round((count * (W * H)) / (1440 * 900));
      stars = Array.from({ length: Math.max(40, n) }, () => ({
        x: Math.random() * W,
        y: Math.random() * H,
        r: Math.random() * 1.1 + 0.35,
        base: Math.random() * 0.55 + 0.25,
        phase: Math.random() * Math.PI * 2,
        speed: Math.random() * 0.9 + 0.25,
        color:
          Math.random() < 0.1
            ? '245,176,74'
            : Math.random() < 0.28
              ? '160,150,255'
              : '238,240,255',
      }));
    };

    const draw = (t) => {
      ctx.clearRect(0, 0, W, H);
      for (const s of stars) {
        const tw = REDUCED
          ? 1
          : 0.5 + 0.5 * Math.sin(s.phase + t * 0.001 * s.speed);
        ctx.globalAlpha = s.base * tw;
        ctx.fillStyle = `rgb(${s.color})`;
        ctx.beginPath();
        ctx.arc(s.x, s.y, s.r, 0, 7);
        ctx.fill();
      }
      raf = requestAnimationFrame(draw);
    };

    resize();
    if (REDUCED) {
      draw(0);
      cancelAnimationFrame(raf);
    } else {
      new IntersectionObserver(
        ([e]) => {
          if (e.isIntersecting && !raf) raf = requestAnimationFrame(draw);
          else if (!e.isIntersecting && raf) {
            cancelAnimationFrame(raf);
            raf = null;
          }
        },
        { threshold: 0.05 },
      ).observe(canvas);
    }
    window.addEventListener('resize', resize);
  };

  makeStars($('#starfield'), 170);
  makeStars($('#starfield-cta'), 110);

  /* ============ Nav con scroll ============ */
  const nav = $('#nav');
  const onScrollNav = () =>
    nav.classList.toggle('is-scrolled', window.scrollY > 24);
  onScrollNav();
  window.addEventListener('scroll', onScrollNav, { passive: true });

  /* ============ Menu hamburguesa (movil, <=900px) ============ */
  const navToggle = $('.nav-toggle');
  const navLinks = $('.nav-links');
  if (navToggle && navLinks) {
    // en escritorio los enlaces siempre visibles aunque quede hidden=true
    // tras redimensionar desde movil (allí la regla .nav-links[hidden]
    // solo existe dentro del media query <=900px)
    if (window.innerWidth > 900) navLinks.hidden = false;

    const setMenu = (open, focusToggle = false) => {
      navLinks.hidden = !open;
      navToggle.setAttribute('aria-expanded', String(open));
      navToggle.setAttribute(
        'aria-label',
        open ? 'Cerrar menú de navegación' : 'Abrir menú de navegación',
      );
      if (focusToggle) navToggle.focus();
    };

    navToggle.addEventListener('click', () => setMenu(navLinks.hidden));
    // al pulsar un enlace se cierra (el ancla navega y el panel sobra)
    navLinks.addEventListener('click', (e) => {
      if (e.target.closest('a')) setMenu(false);
    });
    // clic fuera del menu lo cierra
    document.addEventListener('click', (e) => {
      if (
        !navLinks.hidden &&
        !navToggle.contains(e.target) &&
        !navLinks.contains(e.target)
      )
        setMenu(false);
    });
    // Escape cierra y devuelve el foco al boton
    document.addEventListener('keydown', (e) => {
      if (e.key === 'Escape' && !navLinks.hidden) setMenu(false, true);
    });
  }

  /* ============ Parallax (GSAP ScrollTrigger + mouse, carga on-demand) ============ */
  const heroLayers = $$('.hero [data-depth]');
  if (!REDUCED && heroLayers.length) {
    onceVisible($('.hero'), () => {
      loadGsap()
        .then((gsap) => {
          if (REDUCED) return;
          heroLayers.forEach((layer) => {
            const depth = parseFloat(layer.dataset.depth) || 0.3;
            gsap.to(layer, {
              yPercent: depth * -46,
              ease: 'none',
              scrollTrigger: {
                trigger: '.hero',
                start: 'top top',
                end: 'bottom top',
                scrub: true,
              },
            });
          });
          gsap.to('.hero-inner', {
            opacity: 0.12,
            yPercent: -8,
            ease: 'none',
            scrollTrigger: {
              trigger: '.hero',
              start: '40% top',
              end: 'bottom top',
              scrub: true,
            },
          });

          // parallax de ratón (solo dispositivos con puntero fino)
          if (window.matchMedia('(pointer: fine)').matches) {
            const setters = heroLayers.map((l) =>
              gsap.quickTo(l, 'x', { duration: 0.9, ease: 'power3.out' }),
            );
            const innerX = gsap.quickTo('.hero-inner', 'x', {
              duration: 1.1,
              ease: 'power3.out',
            });
            $('.hero').addEventListener(
              'mousemove',
              (e) => {
                const nx = e.clientX / innerWidth - 0.5;
                heroLayers.forEach((l, i) => {
                  const d = parseFloat(l.dataset.depth) || 0.3;
                  setters[i](nx * d * 60);
                });
                innerX(nx * -14);
              },
              { passive: true },
            );
          }
        })
        .catch(() => {});
    });
  }

  /* ============ Reveals ============ */
  const revealIO = new IntersectionObserver(
    (entries) => {
      entries.forEach((en) => {
        if (en.isIntersecting) {
          en.target.classList.add('is-visible');
          revealIO.unobserve(en.target);
        }
      });
    },
    { threshold: 0.12, rootMargin: '0px 0px -40px 0px' },
  );
  $$('.reveal').forEach((el) => revealIO.observe(el));

  /* ============ Contadores ============ */
  $$('[data-count]').forEach((el) => {
    const target = parseInt(el.dataset.count, 10);
    const prefix = el.dataset.prefix || '';
    const suffix = el.dataset.suffix || '';
    const set = (v) => {
      el.textContent = prefix + v + suffix;
    };
    if (REDUCED) {
      set(target);
      return;
    }
    const state = { v: 0 };
    new IntersectionObserver(
      ([e], io) => {
        if (!e.isIntersecting) return;
        io.disconnect();
        loadAnime()
          .then((anime) => {
            anime({
              targets: state,
              v: target,
              round: 1,
              easing: 'easeOutExpo',
              duration: 1800,
              update: () => set(state.v),
            });
          })
          .catch(() => set(target));
      },
      { threshold: 0.5 },
    ).observe(el);
  });

  /* ============ Terminal CLI (Anime.js) ============ */
  const termBody = $('#term-body');
  if (termBody) {
    const SCRIPT = [
      {
        cmd: [
          ['t-prompt', '$ '],
          ['t-cmd', 'psr parse '],
          ['t-flag', '-f users.psr'],
        ],
        out: [
          ['t-out', '['],
          ['t-out', '  {'],
          ['j-key', '    "type": "user",'],
          ['t-out', '    "attributes": { "name": "Ada", "age": 25 },'],
          ['t-out', '    "children": []'],
          ['t-out', '  }'],
          ['t-out', ']'],
        ],
      },
      {
        cmd: [
          ['t-prompt', '$ '],
          ['t-cmd', 'psr dump '],
          ['t-flag', '-f users.psr -o copy.psr'],
        ],
        out: [['t-ok', 'Dump file created at: copy.psr']],
      },
      {
        cmd: [
          ['t-prompt', '$ '],
          ['t-cmd', 'psr validate '],
          ['t-flag', '-f users.psr -s schema.json'],
        ],
        out: [['t-ok', 'File valid ✔']],
      },
    ];

    const span = (cls, txt) => {
      const s = document.createElement('span');
      s.className = cls;
      s.textContent = txt;
      return s;
    };
    const cursor = span('t-cursor', '\u00a0');

    const renderStatic = () => {
      SCRIPT.forEach((step) => {
        step.cmd.forEach(([c, t]) => termBody.appendChild(span(c, t)));
        termBody.appendChild(document.createTextNode('\n'));
        step.out.forEach(([c, t]) => {
          termBody.appendChild(span(c, t));
          termBody.appendChild(document.createTextNode('\n'));
        });
        termBody.appendChild(document.createTextNode('\n'));
      });
      termBody.appendChild(cursor);
    };

    const runTyping = async () => {
      const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
      termBody.appendChild(cursor);

      while (true) {
        for (const step of SCRIPT) {
          const fullCmd = step.cmd.map(([, t]) => t).join('');
          const proxy = { n: 0 };
          await anime({
            targets: proxy,
            n: fullCmd.length,
            duration: fullCmd.length * 34,
            easing: 'linear',
            update: () => {
              const shown = fullCmd.slice(0, Math.round(proxy.n));
              $$('.t-cmd,.t-flag,.t-prompt', termBody).forEach((n) =>
                n.remove(),
              );
              let idx = 0;
              step.cmd.forEach(([c, t]) => {
                const part = shown.slice(idx, idx + t.length);
                if (part) termBody.insertBefore(span(c, part), cursor);
                idx += t.length;
              });
            },
          }).finished;
          termBody.insertBefore(document.createTextNode('\n'), cursor);

          await sleep(260);

          for (const [c, t] of step.out) {
            const o = span(c, t);
            termBody.insertBefore(o, cursor);
            termBody.insertBefore(document.createTextNode('\n'), cursor);
            anime({
              targets: o,
              opacity: [0, 1],
              duration: 220,
              easing: 'easeOutQuad',
            });
            await sleep(90);
          }
          await sleep(1500);
        }
        [...termBody.childNodes].forEach((n) => {
          if (n !== cursor) n.remove();
        });
        await sleep(400);
      }
    };

    if (REDUCED) renderStatic();
    else
      onceVisible(termBody, () =>
        loadAnime().then(runTyping).catch(renderStatic),
      );
  }

  /* ============ Tooltips (Floating UI) ============ */
  const tooltipEl = $('#tooltip');
  const tipApi = { showTip: null, hideTip: null };
  if (tooltipEl) {
    let cleanupAuto = null;

    const showTip = (ref, content) => {
      if (!ref || !content) return;
      tooltipEl.innerHTML = content;
      tooltipEl.hidden = false;
      loadFloating()
        .then((FloatingUIDOM) => {
          if (tooltipEl.hidden) return; // se cerró mientras se cargaba
          if (cleanupAuto) cleanupAuto();
          cleanupAuto = FloatingUIDOM.autoUpdate(ref, tooltipEl, () => {
            FloatingUIDOM.computePosition(ref, tooltipEl, {
              placement: 'top',
              middleware: [
                FloatingUIDOM.offset(8),
                FloatingUIDOM.flip(),
                FloatingUIDOM.shift({ padding: 8 }),
              ],
            }).then(({ x, y }) => {
              Object.assign(tooltipEl.style, { left: `${x}px`, top: `${y}px` });
            });
          });
        })
        .catch(() => {
          tooltipEl.hidden = true;
        });
    };

    const hideTip = () => {
      tooltipEl.hidden = true;
      if (cleanupAuto) {
        cleanupAuto();
        cleanupAuto = null;
      }
    };

    tipApi.showTip = showTip;
    tipApi.hideTip = hideTip;

    $$('[data-tip],[data-tip-html]').forEach((el) => {
      const getContent = () => {
        if (el.dataset.tipHtml) {
          const tpl = $(el.dataset.tipHtml);
          return tpl ? tpl.innerHTML : '';
        }
        return el.dataset.tip || '';
      };
      el.addEventListener('mouseenter', () => {
        el.__tipContent = getContent();
        showTip(el, el.__tipContent);
      });
      el.addEventListener('focusin', () => {
        el.__tipContent = getContent();
        showTip(el, el.__tipContent);
      });
      el.addEventListener('mouseleave', hideTip);
      el.addEventListener('focusout', hideTip);
    });
  }

  /* ============ Copiar al portapapeles ============ */
  const flashCopied = (btn) => {
    if (!tipApi.showTip) return;
    tipApi.showTip(btn, '<strong>¡Copiado!</strong>');
    setTimeout(() => tipApi.hideTip(), 1200);
  };

  $$('.copy-btn').forEach((btn) => {
    btn.addEventListener('click', () => {
      const text =
        btn.dataset.copyText ?? $(btn.dataset.copyTarget)?.textContent ?? '';
      if (!text) return;
      navigator.clipboard
        .writeText(text.trim())
        .catch(() => {
          const ta = document.createElement('textarea');
          ta.value = text.trim();
          document.body.appendChild(ta);
          ta.select();
          document.execCommand('copy');
          ta.remove();
        })
        .finally(() => flashCopied(btn));
    });
  });

  /* ============ Tabs de instalación ============ */
  const tabs = $$('#instalacion .tab');
  const panels = $$('#instalacion .tab-panel');
  const activateTab = (tab) => {
    tabs.forEach((t) => {
      const active = t === tab;
      t.classList.toggle('is-active', active);
      t.setAttribute('aria-selected', String(active));
      t.tabIndex = active ? 0 : -1;
    });
    panels.forEach((p) => {
      p.classList.toggle(
        'is-active',
        p.id === tab.getAttribute('aria-controls'),
      );
      p.hidden = p.id !== tab.getAttribute('aria-controls');
    });
  };
  tabs.forEach((tab, i) => {
    tab.addEventListener('click', () => activateTab(tab));
    tab.addEventListener('keydown', (e) => {
      let j = null;
      if (e.key === 'ArrowRight') j = (i + 1) % tabs.length;
      if (e.key === 'ArrowLeft') j = (i - 1 + tabs.length) % tabs.length;
      if (e.key === 'Home') j = 0;
      if (e.key === 'End') j = tabs.length - 1;
      if (j !== null) {
        e.preventDefault();
        tabs[j].focus();
        activateTab(tabs[j]);
      }
    });
  });

  /* Navegación por anclas: smooth scroll nativo (html { scroll-behavior }).
     Los reveals on-scroll aportan el movimiento; sin overlays ni wipes. */

  /* ============ Swiper: casos de uso (carga al entrar en viewport) ============ */
  const casosEl = $('.casos-swiper');
  if (casosEl) {
    onceVisible(casosEl, () => {
      loadSwiper()
        .then((Swiper) => {
          new Swiper('.casos-swiper', {
            slidesPerView: 1.08,
            spaceBetween: 18,
            grabCursor: true,
            keyboard: { enabled: true },
            a11y: { enabled: true },
            breakpoints: {
              700: { slidesPerView: 1.7 },
              1024: { slidesPerView: 2.4 },
              1280: { slidesPerView: 3 },
            },
            navigation: {
              nextEl: '.sw-next',
              prevEl: '.sw-prev',
            },
            pagination: {
              el: '.casos-swiper .swiper-pagination',
              clickable: true,
            },
          });
        })
        .catch(() => {});
    });
  }
})();
