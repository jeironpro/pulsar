# Contributing to pulsar

¡Gracias por interesarte en contribuir a pulsar!
Tu ayuda hace que este proyecto sea mejor para todos, ya sea con código, ideas, documentación o reportes de errores.

## Cómo Contribuir

### 1. Contribuciones de Código
(Sigue los pasos tradicionales: fork, branch, commits, PR…)

### 2. Contribuciones de Ideas y Mejoras
Si tienes ideas para nuevas funcionalidades, mejoras o cambios en el proyecto:

1. Abre un **Issue** en GitHub.
2. Describe tu idea de manera clara:
   - Qué problema resuelve o qué mejora aporta.
   - Cómo podría implementarse (opcional).
   - Ejemplos o referencias si aplican.
3. Etiqueta tu issue como `idea` o `enhancement`.

Se revisarán la propuesta antes de implementarla.

### 3. Contribuciones de Documentación
Mejorar la documentación es muy valioso:

- Corrección de errores tipográficos.
- Explicaciones más claras.
- Nuevos ejemplos o tutoriales.

Sigue los mismos pasos de código: crea una rama, haz cambios en los archivos `.md` y envía un Pull Request.

### 4. Reportes de Errores (Bugs)
Si encuentras un error o bug:

1. Abre un **Issue** en GitHub.
2. Describe el problema claramente:
   - Qué estabas intentando hacer.
   - Qué esperabas que ocurriera.
   - Qué ocurrió realmente.
3. Incluye capturas de pantalla o logs si es posible.

---

## Sincronía del parser con la landing

La landing (`landing/`) ejecuta el parser real en el navegador vía Pyodide usando una copia del módulo en `landing/pulsar.py`.

Reglas:

- **`landing/pulsar.py` debe ser idéntico a `pulsar.py`** (fuente única). El playground depende de esa copia exacta.
- El workflow `pages.yml` la resincroniza automáticamente al desplegar (`cp pulsar.py landing/pulsar.py`).
- El job **Parser sync (landing)** del CI (`ci.yml`) compara ambas copias en cada push/PR y **falla si divergen**.

Para contribuir al parser:

1. Edita `pulsar.py` (única fuente de verdad).
2. Sincroniza la copia: `cp pulsar.py landing/pulsar.py`.
3. Incluye ambos archivos en el mismo commit/PR (el CI verifica la identidad).

Si el job `Parser sync (landing)` se marca en rojo, las copias divergen: ejecuta `cp pulsar.py landing/pulsar.py`, haz commit y vuelve a hacer push.

---

## Publicar un release

El release es automático y guiado por tags (el flujo completo vive en `.github/workflows/release.yml`):

1. **Preparar la rama** (formato `release/X.Y.Z`):
   - Subir `__version__` en `pulsar.py` (fuente única) y sincronizar `landing/pulsar.py` (`cp pulsar.py landing/pulsar.py`).
   - Añadir la entrada en `CHANGELOG.md` y actualizar las referencias de versión en `README.md` y `landing/index.html`.
   - Abrir PR y esperar CI verde.
2. **Mergear** el PR a `main`.
3. **Crear el tag**:
   ```bash
   git checkout main && git pull
   git tag -a v2.0.1 -m "PULSAR v2.0.1"
   git push origin v2.0.1
   ```
4. **Qué dispara**: `release.yml` ejecuta tests → build + GitHub Release (sdist/wheel) → publicación en PyPI con trusted publishing (OIDC, sin tokens) → verificación automática (`verify`: PyPI responde con la versión y `pip install pulsar-psr==<versión>` funciona).

### Configurar el trusted publisher (solo la primera vez)

En https://pypi.org/manage/account/publishing/ (a nivel de cuenta si el proyecto aún no existe) → *Add publisher* → GitHub:
- Owner: `jeironpro`
- Repository: `pulsar`
- Workflow name: `release.yml` (el **nombre del archivo**, no el nombre visible del workflow)
- Environment name: `pypi`
- Nombre del proyecto: `pulsar-psr`

Los tres valores (workflow name, environment y repo) deben coincidir **al carácter** con `release.yml`.

### Si el job publish falla

El error típico es `invalid-publisher` (los claims OIDC no coinciden con el publisher registrado). Verifica en PyPI que `repository`, `workflow name` y `environment name` coinciden exactamente con `release.yml`, corrige, y re-ejecuta solo el job fallido:

```bash
gh run rerun <run-id> --failed
```

**Ojo**: el re-run usa el workflow del commit original. Si el arreglo fue un cambio de *workflow*, hay que recrear el tag para que el nuevo run lo use:

```bash
git push origin :refs/tags/v2.0.1 && git tag -d v2.0.1
gh release delete v2.0.1 --yes
git tag -a v2.0.1 -m "PULSAR v2.0.1" && git push origin v2.0.1
```

---

## Normas Generales

- Sé respetuoso y constructivo en tus comentarios.
- Sé lo más claro posible, especialmente en ideas o reportes.
- Revisa si tu idea o bug ya ha sido reportado antes de abrir un nuevo issue.

---

¡Gracias por contribuir!
Recuerda: **toda contribución cuenta**, no solo el código.
