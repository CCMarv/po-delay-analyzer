# Jerarquía con múltiples flags activas

* **Estatus:** 🟢 Vigente
* **Contexto Técnico:** Fase 2 / Modelado de Atribución Dominante
* **Referencias:** Issue #39, Discussion #52

## Contexto y Problema
En la realidad operativa de la cadena de suministro, un único pedido (*Purchase Order*) puede experimentar demoras simultáneas en múltiples tramos (Vendor, Carrier y DC). Forzar una causa única artificial mediante reglas estáticas oculta la fricción real del negocio. El reto consiste en estructurar la asignación de la etapa primaria sin perder la visibilidad del ecosistema de causas accesorias que impactaron al pedido.

## Opciones Consideradas

### Opción 1: Modelo de prioridades fijas estáticas
*   **Pros:** Sencillo de implementar mediante estructuras condicionales simples (ej. *si falla Carrier, ignorar lo demás*).
*   **Contras:** Genera un sesgo artificial masivo en los datos, ocultando ineficiencias críticas de otros actores.

### Opción 2: Criterio matemático del mayor exceso sobre el umbral (`argmax`) con vector complementario
*   **Pros:** Es un enfoque matemático transparente y justo. Determina la etapa primaria basándose en quién rompió de forma más grave su ventana de tiempo acordada, resolviendo la causa raíz principal sin sesgos fijos.
*   **Contras:** Requiere una arquitectura de datos capaz de soportar almacenamiento estructurado o matricial para la capa complementaria.

## Decisión
Elegimos la **Opción 2**. La etapa primaria de atribución del retraso se asignará dinámicamente mediante la función **`argmax`**, seleccionando el tramo de la cadena que muestre el **mayor exceso numérico en horas sobre su propio umbral parametrizado**. 

Para complementar este enfoque y no forzar una causa única excluyente, se anexa un **vector multi-causa como capa complementaria** en el registro del pedido, preservando el historial completo de todas las flags activadas durante el trayecto.

## Consecuencias
*   **Positivas:** El modelo refleja con precisión científica la severidad del impacto operativo de cada actor, permitiendo planes de acción eficientes.
*   **Negativas:** La lógica de agregación en reportes finales debe considerar el vector multi-causa para análisis avanzados, lo cual eleva la complejidad de las consultas analíticas iniciales.
