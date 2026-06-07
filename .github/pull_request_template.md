<!--
Modelo de merge NO bloqueante: trabajamos en horarios desfasados, así que NO esperamos
a que otro revise antes de mergear. El gate es tu self-review + CI en verde. La review
cruzada es opcional y POSTERIOR (sobre main ya integrado).
-->

Closes #<!-- número del issue. Al mergear, GitHub lo cierra solo. -->

## Qué cambia
<!-- Bullets concretos de lo que hace este PR. -->
-
-

## Self-review (esto es tu gate para mergear)
<!--
Tú confirmas esto antes de mergear — reemplaza al revisor humano. Si algo no aplica,
táchalo y di por qué. Si CI aún no existe en el repo: usa "tests/pipeline pasan en local".
-->
- [ ] Corre en entorno limpio (`venv` desde `requirements.txt`)
- [ ] Tests / pipeline pasan en local
- [ ] **CI en verde** (o, si CI no existe aún, lo verifiqué a mano)
- [ ] Sin secrets, datos (CSV) ni outputs de notebook commiteados
- [ ] La DoD del issue está cumplida

## Notas para quien revise después
<!--
La review cruzada es opcional y va DESPUÉS del merge, cuando alguien esté disponible.
Dile a qué prestar atención. Si quien revisa encuentra algo, abre un issue de
seguimiento (no se revierte ni se bloquea por ello).
-->
-

---
<sub>Merge no bloqueante: self-review + CI en verde → mergeas tú. Review cruzada opcional y posterior. Estrategia: **Merge commit**. Borra la rama al cerrar.</sub>
