# Idioma fuente canónico y convención de nombres para documentación bilingüe (ES→EN)

* **Estatus:** 🔵 **BORRADOR** (abierto 2026-07-13; la versión final la valida el equipo)
* **Contexto Técnico:** Documentación — Cierre y entregables; plan de traducción ES→EN
* **Referencias:** Issue #88 (plan de traducción); Issue #96 (ejecución de la traducción);
  `../plan-traduccion.md`; repo del mentor (kickoff ES + EN publicados como artefactos
  paralelos); práctica reconocida "maintaining bilingual documentation source language"

## Contexto y Problema

Los entregables deben ser bilingües ES + EN, pero hoy toda la documentación está en español.
Traducir antes de que el fuente esté validado obliga a re-traducir cada corrección, y sin una
convención explícita el par de idiomas diverge: nadie sabe cuál versión es la de verdad
cuando difieren. Hace falta fijar cuál es el idioma fuente y cómo se nombra y mantiene la
traducción derivada para que ES y EN no se separen a lo largo del cierre del proyecto.

## Opciones Consideradas

### Opción A: Mantenimiento paralelo independiente
Ambos idiomas se editan a mano por separado, sin relación fuente-derivado.
* **Pros:** Cada idioma se puede redactar con lectura natural, sin atarse a la estructura del
  otro.
* **Contras:** Los dos idiomas divergen inevitablemente conforme el proyecto corrige el
  contenido; el esfuerzo de corrección se duplica; no hay una fuente de verdad única a la que
  recurrir ante una discrepancia. Descartada.

### Opción B: Fuente canónica ES + traducción derivada con sufijo `.en.md`
El español es el canónico; el inglés es una derivación que nunca se edita de forma
independiente. Los archivos son hermanos en la misma carpeta (`README.md` / `README.en.md`).
* **Pros:** Una sola fuente de verdad (ES); el `.en.md` se re-deriva cuando el ES cambia; la
  convención de nombres es simple y hace visible la relación fuente↔traducción en el árbol
  del repo, sin carpetas ni herramientas nuevas; replica el patrón del kickoff del mentor
  (ES + EN paralelos).
* **Contras:** Depende de disciplina humana (no editar el `.en.md` directamente); la
  re-derivación ante cada cambio del ES es manual.

### Opción C: Tooling de i18n
Extracción y merge automatizados con `gettext`/archivos `.po`, carpetas `locale/`, o una rama
separada por idioma.
* **Pros:** Estándar en software con UI internacionalizada; automatiza extracción y
  reconciliación de cadenas.
* **Contras:** Sobreingeniería para un conjunto de ~5–7 documentos Markdown de un entregable
  académico; añade curva de setup y mantenimiento sin beneficio a este volumen. Fuera de
  alcance; se registra como posible evolución futura si el volumen creciera.

## Decisión

Se adopta la **Opción B**: idioma fuente ES canónico, traducción EN derivada con convención
de nombres de archivo hermano `.en.md`. El detalle operativo (alcance, orden y disparador de
la traducción) vive en `../plan-traduccion.md`.
