# MCP Puerto Rico Sentencias 🇵🇷

Servidor **Model Context Protocol (MCP)** para buscar y consultar jurisprudencia de Puerto Rico desde clientes compatibles con MCP.

El proyecto toma como referencia la experiencia de [DerechoVirtual/mcp-cendoj-sentencias](https://github.com/DerechoVirtual/mcp-cendoj-sentencias), pero está diseñado específicamente para las fuentes públicas de Puerto Rico.

## Regla crítica: integridad de citas

**Este MCP NO puede inventar casos, sentencias, citas, nombres de las partes, jueces, fechas, números de caso, holdings ni citas textuales.**

La regla es **source-first / zero citation hallucination**:

1. Una autoridad jurídica solo se presenta como verificada cuando sus datos identificadores provienen de una fuente pública identificable.
2. Los campos que la fuente no proporciona se dejan vacíos; el servidor no los completa por inferencia.
3. `buscar_por_cita` exige coincidencia exacta de la cita y **no sustituye una cita inexistente por una parecida**.
4. Si una autoridad no puede verificarse, el servidor devuelve `encontrado: false` y no genera una alternativa plausible.
5. El texto de una decisión se identifica como extracción de la fuente; nunca se presenta texto generado por un modelo como una cita textual.
6. Los enlaces a la fuente se conservan para que el abogado pueda verificar la autoridad original.

Esta garantía es deliberadamente más importante que producir una respuesta. **Es preferible devolver “no encontrado” que una autoridad jurídica falsa.**

## Fuentes

- **Poder Judicial de Puerto Rico — Tribunal Supremo:** fuente oficial de decisiones del Tribunal Supremo.
- **LexJuris:** fuente complementaria para localizar jurisprudencia y documentos cuando estén públicamente accesibles.

> LexJuris no se trata como sustituto de la publicación oficial. Cuando exista una fuente oficial verificable, esta debe preferirse.

## Herramientas MCP

- `buscar_sentencias`: búsqueda por palabras/frases, año y máximo de resultados. No completa metadatos ausentes.
- `buscar_por_cita`: búsqueda **exacta y verificable** por cita TSPR.
- `leer_sentencia`: extrae texto de una URL pública permitida y conserva su procedencia.
- `opciones_busqueda`: fuentes, filtros y reglas de integridad.
- `estado`: diagnóstico y garantías de integridad de citas.

## Instalación

Requiere Python 3.10+.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .
```

### Claude Desktop / Cowork

```json
{
  "mcpServers": {
    "puerto-rico-sentencias": {
      "command": "/ruta/al/repositorio/.venv/bin/python",
      "args": ["/ruta/al/repositorio/server.py"]
    }
  }
}
```

## Ejemplos

> “Busca sentencias del Tribunal Supremo de Puerto Rico sobre daños punitivos entre 2018 y 2025.”

> “Verifica si existe 2024 TSPR 140.”

> “Si 2024 TSPR 140 existe, dame solamente los datos que aparezcan en la fuente.”

> “Si no encuentras 2024 TSPR 999, no inventes ni sustituyas la cita.”

## Arquitectura de confianza

La arquitectura sigue esta secuencia:

**FUENTE → EXTRACCIÓN → VALIDACIÓN → MCP**

No se utiliza el LLM como fuente de autoridad jurídica. Un modelo puede, en una capa posterior, resumir o clasificar documentos que ya fueron recuperados y verificados, pero no puede crear la autoridad ni rellenar sus datos faltantes.

Los resultados incluyen campos de procedencia como `source`, `url`, `verified` y `verification_status`.

## Seguridad y acceso

El servidor no intenta eludir CAPTCHA, controles anti-bot, autenticación, paywalls ni límites de acceso. Si una fuente no permite acceso automatizado, se debe utilizar el enlace para consulta manual.

## Privacidad

No se incluyen credenciales en el repositorio. No se almacenan expedientes, consultas ni documentos del usuario por defecto.

**Recomendación para uso jurídico:** las consultas deben estar anonimizadas y no deben incluir información confidencial del cliente cuando no sea necesaria para localizar jurisprudencia.

## Uso profesional

El MCP es una herramienta de investigación, no un sustituto de la revisión jurídica. Antes de citar una autoridad en un escrito u opinión, debe verificarse el documento original y su vigencia/aplicabilidad.

## Licencia

MIT.
