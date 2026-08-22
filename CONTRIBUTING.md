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

## Normas Generales

- Sé respetuoso y constructivo en tus comentarios.
- Sé lo más claro posible, especialmente en ideas o reportes.
- Revisa si tu idea o bug ya ha sido reportado antes de abrir un nuevo issue.

---

¡Gracias por contribuir!
Recuerda: **toda contribución cuenta**, no solo el código.
