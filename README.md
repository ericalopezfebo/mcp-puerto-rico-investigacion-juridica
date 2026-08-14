# MCP Puerto Rico Sentencias 🇵🇷

## Busca y lee sentencias de Puerto Rico directamente desde Claude

**MCP Puerto Rico Sentencias** permite a **Claude Desktop / Cowork** buscar, localizar y leer sentencias de Puerto Rico directamente desde fuentes públicas. Está diseñado para investigación jurídica rápida y verificable: encuentra la mejor sentencia disponible para una cuestión, recupera el documento y permite extraer los **párrafos exactos**, junto con su **número de caso, cita y fuente**, cuando esos datos aparecen en el documento.

### Descripción

Un servidor MCP enfocado exclusivamente en jurisprudencia de Puerto Rico. Convierte las fuentes públicas de decisiones judiciales en herramientas que Claude puede consultar en lenguaje natural, reduciendo el tiempo necesario para localizar precedentes y revisar el texto de las opiniones.

El objetivo es combinar **velocidad + precisión + trazabilidad**: encontrar rápidamente las decisiones más relevantes, leer su contenido y devolver pasajes verificables sin inventar autoridades ni completar datos que no estén en la fuente.

> **No inventa jurisprudencia.** Si una sentencia, cita, nombre, número de caso o dato jurídico no puede verificarse en una fuente identificable, el MCP lo marca como no verificado o informa que no fue encontrado.

## Qué hace

- 🔎 **Busca sentencias de Puerto Rico** desde Claude.
- ⚡ Diseñado para búsquedas rápidas y consultas directas.
- 📄 **Lee el contenido** de decisiones públicas.
- 🎯 Ayuda a encontrar la **mejor sentencia** para una cuestión jurídica mediante búsqueda y clasificación de resultados verificables.
- 📌 Extrae **párrafos exactos** del documento fuente.
- ⚖️ Devuelve el **número de caso**, cita TSPR y demás metadatos únicamente cuando aparecen en la fuente.
- 🔗 Conserva el **enlace a la fuente original** para verificación.
- 🛡️ Aplica una política estricta de **zero citation hallucination**.

## Regla crítica: integridad de citas

**Este MCP NO puede inventar casos, sentencias, citas, nombres de las partes, jueces, fechas, números de caso, holdings ni citas textuales.**

La regla es **source-first / zero citation hallucination**:

1. Una autoridad jurídica solo se presenta como verificada cuando sus datos identificadores provienen de una fuente pública identificable.
2. Los campos que la fuente no proporciona se dejan vacíos; el servidor no los completa por inferencia.
3. `buscar_por_cita` exige coincidencia exacta de la cita y **no sustituye una cita inexistente por una parecida**.
4. Si una autoridad no puede verificarse, el servidor devuelve `encontrado: false` y no genera una alternativa plausible.
5. Los párrafos y citas textuales deben provenir del documento recuperado; nunca se presenta texto generado por un modelo como si fuera texto judicial.
6. Los enlaces a la fuente se conservan para que el abogado pueda verificar la autoridad original.

**Es preferible devolver “no encontrado” que una autoridad jurídica falsa.**

## Fuentes

- **Poder Judicial de Puerto Rico — Tribunal Supremo:** fuente oficial de decisiones del Tribunal Supremo.
- **LexJuris:** fuente complementaria para localizar jurisprudencia y documentos cuando estén públicamente accesibles.

Cuando exista una publicación oficial verificable, esta debe preferirse para la comprobación final de la autoridad.

## Herramientas MCP

- `buscar_sentencias` — búsqueda por palabras/frases, año y máximo de resultados.
- `buscar_por_cita` — búsqueda **exacta y verificable** por cita TSPR.
- `leer_sentencia` — extracción del texto de una URL pública permitida, conservando la procedencia.
- `opciones_busqueda` — fuentes, filtros y reglas de integridad.
- `estado` — diagnóstico y garantías de integridad de citas.

## Ejemplos de uso desde Claude

> “Busca la mejor sentencia del Tribunal Supremo de Puerto Rico sobre prescripción de una acción de daños y perjuicios.”

> “Encuentra sentencias sobre arbitraje y dame el número de caso y los párrafos exactos donde el Tribunal explica la regla.”

> “Busca jurisprudencia sobre legitimación activa y selecciona las decisiones más relevantes.”

> “Verifica si existe 2024 TSPR 140 y, si existe, dime el número de caso y extrae los párrafos pertinentes.”

> “Si no encuentras la cita, no inventes ni sustituyas la sentencia.”

## Arquitectura de confianza

La arquitectura sigue esta secuencia:

**FUENTE → EXTRACCIÓN → VALIDACIÓN → MCP → CLAUDE**

No se utiliza el LLM como fuente de autoridad jurídica. Claude puede ayudar a interpretar una consulta, ordenar resultados o resumir documentos que ya fueron recuperados y verificados, pero **no puede crear una autoridad ni rellenar sus datos faltantes**.

Los resultados incluyen campos de procedencia como `source`, `url`, `verified` y `verification_status`.

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

## Seguridad y acceso

El servidor no intenta eludir CAPTCHA, controles anti-bot, autenticación, paywalls ni límites de acceso. Si una fuente no permite acceso automatizado, se debe utilizar el enlace para consulta manual.

## Privacidad

No se incluyen credenciales en el repositorio. No se almacenan expedientes, consultas ni documentos del usuario por defecto.

**Para uso jurídico:** las consultas deben estar anonimizadas y no deben incluir información confidencial del cliente cuando no sea necesaria para localizar jurisprudencia.

## Uso profesional

El MCP es una herramienta de investigación jurídica. Antes de citar una autoridad en un escrito u opinión, debe verificarse el documento original, su cita, contenido y vigencia/aplicabilidad.

## Licencia

MIT.
