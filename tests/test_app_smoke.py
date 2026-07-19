"""
test_app_smoke.py — red mínima de CI sobre la app de Fase 4 (T7).

Antes de esta unidad, nada en CI ejecutaba las páginas de 04_app/: los bugs de
rutas por CWD (T2, T9) y el _REPO_ROOT roto del bot (T5) solo se detectaban
corriendo la app a mano. `AppTest` (streamlit.testing.v1) ejecuta el script de
una página como lo haría `streamlit run`, sin servidor ni navegador, y expone
`at.exception` si algo revienta durante la corrida — eso es lo único que se
verifica aquí: que las dos páginas cargan sin excepción con los datos reales
del repo (o su fallback a la muestra versionada de G1 si el artefacto de F3 no
existe, y sin `agente1_raw.txt` en la vista de red). No se afirma nada sobre el
contenido visual ni el layout; eso se revisa a mano (ver skill /verify).
"""
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

_APP_DIR = Path(__file__).resolve().parent.parent / "04_app"

_PAGES = [
    _APP_DIR / "pages" / "1_🔍_Exception_Workbench.py",
    _APP_DIR / "pages" / "2_📊_Network_Intelligence.py",
]


@pytest.mark.parametrize("page_path", _PAGES, ids=[p.name for p in _PAGES])
def test_pagina_importa_y_corre_sin_excepcion(page_path):
    assert page_path.exists(), f"No se encontró la página: {page_path}"
    at = AppTest.from_file(str(page_path))
    at.run(timeout=30)
    assert not at.exception, f"{page_path.name} lanzó una excepción: {at.exception}"
