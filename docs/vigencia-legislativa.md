# Vigencia legislativa: SUTRA, Estado y CodeXPR

## Regla central

El MCP **no debe presentar una ley, código, reglamento o artículo como vigente, actual o no derogado únicamente porque aparezca en un buscador, PDF histórico o fuente secundaria**.

La ausencia de una señal de derogación tampoco equivale a prueba de vigencia.

## Jerarquía de fuentes

### Fuentes oficiales preferidas para vigencia

1. **SUTRA — Sistema Único de Trámite Legislativo / Oficina de Servicios Legislativos de Puerto Rico**
2. **Biblioteca Jurídica Virtual / Departamento de Estado de Puerto Rico**

SUTRA expone en fichas legislativas relaciones explícitas de enmienda, sustitución, reenumeración y derogación de artículos. Estas relaciones se usan como evidencia oficial, pero una sola ficha enmendatoria no basta por sí sola para afirmar que el resto de una ley sigue vigente.

### Fuentes secundarias de descubrimiento

- CodeXPR
- LexJuris
- Microjuris / Microjuris Al Día

Pueden ayudar a localizar rápidamente una ley, caso, reglamento o relación entre autoridades, pero **no son prueba final de vigencia** dentro de este MCP.

## Herramientas

### `verificar_vigencia_legislativa`

Recibe:

- `ley`
- `url_oficial`
- `articulo` opcional

La URL debe pertenecer a una fuente oficial permitida. La herramienta extrae únicamente señales explícitas visibles de:

- enmienda;
- derogación;
- sustitución;
- reenumeración.

Si la información disponible no permite resolver la vigencia, devuelve:

```json
{
  "estado_vigencia": "no_determinada",
  "puede_afirmarse_vigente": false
}
```

### `politica_vigencia_fuentes`

Expone al cliente MCP la jerarquía y los estados permitidos.

## Estados previstos

- `vigente_verificado`
- `enmendada`
- `parcialmente_derogada`
- `derogada`
- `sustituida`
- `vigencia_futura`
- `no_determinada`

En la versión 0.11.0 el sistema es deliberadamente conservador y usa `no_determinada` por defecto. La clasificación automática de `vigente_verificado` requerirá historial oficial completo y texto consolidado suficiente; no se infiere de una sola ficha.

## Política de acceso

Esta capa no usa cookies personales, sesiones exportadas, credenciales de usuarios ni extensiones de navegador para evadir controles de acceso. CodeXPR puede integrarse como descubrimiento cuando el contenido sea público y accesible, pero la verificación de vigencia permanece en fuentes oficiales.

## Objetivo futuro

Construir un grafo legislativo que conecte:

`ley original → leyes enmendatorias → artículos afectados → texto oficial aplicable → jurisprudencia que interpreta la disposición`

Esto permitirá que una respuesta jurídica distinga entre encontrar una norma y demostrar que la versión citada sigue siendo aplicable.
