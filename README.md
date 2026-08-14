# MCP Puerto Rico Sentencias 🇵🇷

## Busca y lee sentencias de Puerto Rico desde Claude, ChatGPT y otros clientes MCP

**MCP Puerto Rico Sentencias** permite a **Claude Desktop / Cowork, ChatGPT y otros clientes compatibles con MCP** buscar, localizar y leer sentencias de Puerto Rico directamente desde fuentes públicas. Está diseñado para investigación jurídica rápida y verificable: encuentra los precedentes más relevantes disponibles para una cuestión, recupera el documento y permite extraer **pasajes del texto fuente**, junto con su **número de caso, cita y fuente**, cuando esos datos aparecen en el documento.

### Descripción

Un servidor MCP enfocado en jurisprudencia de Puerto Rico. Convierte fuentes públicas de decisiones judiciales en herramientas que los asistentes compatibles con MCP pueden consultar en lenguaje natural, reduciendo el tiempo necesario para localizar precedentes y revisar el texto de las opiniones.

El objetivo es combinar **velocidad + precisión + trazabilidad**: encontrar rápidamente candidatos relevantes, leer sus documentos y devolver pasajes verificables sin inventar autoridades ni completar datos que no estén en la fuente.

> **No inventa jurisprudencia.** Si una sentencia, cita, nombre, número de caso o dato jurídico no puede verificarse en una fuente identificable, el MCP lo marca como no verificado o informa que no fue encontrado.

## Claude + ChatGPT

El proyecto ofrece **un mismo conjunto de herramientas y reglas de integridad** para distintos clientes MCP:

- **Claude Desktop / Cowork:** ejecución local mediante `stdio`.
- **ChatGPT:** ejecución remota mediante **Streamable HTTP** sobre HTTPS.
- **Otros clientes MCP:** pueden utilizar el transporte que soporte el cliente.

El código de búsqueda, extracción y verificación es compartido. El cliente —Claude, ChatGPT u otro— **no es la fuente de la autoridad jurídica**.

### ChatGPT: MCP remoto

ChatGPT no se conecta directamente a un servidor MCP que solo esté ejecutándose en el ordenador local. Para usar este proyecto desde ChatGPT, el servidor debe estar desplegado en una URL **HTTPS** accesible y exponer el endpoint MCP:

```text
https://TU-DOMINIO/mcp
```

El repositorio incluye `remote_server.py`, `Dockerfile` y `render.yaml` para facilitar ese despliegue. El transporte utilizado es **Streamable HTTP**, el transporte HTTP actual del SDK de MCP.

Después del despliegue, la URL `/mcp` puede utilizarse al crear/configurar una app MCP personalizada en ChatGPT, sujeto a la disponibilidad y permisos del plan o espacio de trabajo de ChatGPT.

## Qué hace

- 🔎 **Busca sentencias de Puerto Rico** desde Claude, ChatGPT u otros clientes MCP.
- ⚡ Diseñado para búsquedas rápidas y consultas directas.
- 📄 **Lee decisiones públicas en HTML y PDF**.
- 🎯 Ordena candidatos por coincidencia con la consulta dentro de los metadatos que realmente aparecen en la fuente.
- 📌 Extrae **pasajes del documento fuente** y conserva su procedencia; en PDF, incluye página cuando puede determinarse.
- ⚖️ Devuelve **número de caso, cita TSPR y otros metadatos** únicamente cuando aparecen en la fuente.
- 🔗 Conserva el **enlace a la fuente original** para verificación.
- 🛡️ Aplica una política estricta de **zero citation hallucination**.
- 🔒 Las herramientas son de investigación/lectura: no crean, modifican ni eliminan información en las fuentes judiciales.

## Regla crítica: integridad de citas

**Este MCP NO puede inventar casos, sentencias, citas, nombres de las partes, jueces, fechas, números de caso, holdings ni citas textuales.**

La regla es **source-first / zero citation hallucination**:

1. Una autoridad jurídica solo se presenta como verificada cuando sus datos identificadores provienen de una fuente pública identificable.
2. Los campos que la fuente no proporciona se dejan vacíos; el servidor no los completa por inferencia.
3. `buscar_por_cita` exige coincidencia exacta de la cita y **no sustituye una cita inexistente por una parecida**.
4. Si una autoridad no puede verificarse, el servidor devuelve `encontrado: false` y no genera una alternativa plausible.
5. Los pasajes y citas textuales deben provenir del documento recuperado; nunca se presenta texto generado por un modelo como si fuera texto judicial.
6. Los enlaces a la fuente se conservan para que el abogado pueda verificar la autoridad original.

**Es preferible devolver “no encontrado” que una autoridad jurídica falsa.**

## Fuentes

- **Poder Judicial de Puerto Rico — Tribunal Supremo:** fuente oficial de decisiones del Tribunal Supremo.
- **LexJuris:** fuente complementaria para localizar jurisprudencia y documentos cuando estén públicamente accesibles.

Cuando exista una publicación oficial verificable, esta debe preferirse para la comprobación final de la autoridad.

## Herramientas MCP

- `buscar_sentencias` — búsqueda por palabras/frases, año y máximo de resultados.
- `buscar_por_cita` — búsqueda **exacta y verificable** por cita TSPR.
- `leer_sentencia` — descarga y extracción de texto desde HTML/PDF público, con pasajes relevantes y procedencia.
- `opciones_busqueda` — fuentes, filtros y reglas de integridad.
- `estado` — diagnóstico y garantías de integridad de citas.

## Ejemplos de uso

> “Busca la mejor sentencia disponible del Tribunal Supremo de Puerto Rico sobre prescripción de una acción de daños y perjuicios.”

> “Encuentra sentencias sobre arbitraje y dame el número de caso y los pasajes exactos donde el Tribunal explica la regla.”

> “Busca jurisprudencia sobre legitimación activa y selecciona los resultados más relevantes que puedas verificar.”

> “Verifica si existe 2024 TSPR 140 y, si existe, dime el número de caso y extrae los pasajes pertinentes del documento.”

> “Si no encuentras la cita, no inventes ni sustituyas la sentencia.”

## Arquitectura de confianza

La arquitectura sigue esta secuencia:

**FUENTE → EXTRACCIÓN → VALIDACIÓN → MCP → CLIENTE (CLAUDE / CHATGPT / OTRO)**

No se utiliza el LLM como fuente de autoridad jurídica. El cliente puede ayudar a interpretar una consulta, ordenar resultados o resumir documentos que ya fueron recuperados y verificados, pero **no puede crear una autoridad ni rellenar sus datos faltantes**.

Los resultados incluyen campos de procedencia como `source`, `url`, `verified` y `verification_status`.

## Instalación local

Requiere Python 3.10+.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .
```

Para ejecutar las pruebas:

```bash
pip install -e ".[test]"
pytest -q
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

### Servidor remoto

Para desplegar el endpoint HTTP:

```bash
python remote_server.py
```

Por defecto escucha en `0.0.0.0` y usa el puerto `8000` o la variable `PORT` proporcionada por el proveedor de hosting. El endpoint MCP es `/mcp`.

Para producción, debe utilizarse un proveedor que proporcione **HTTPS** y protección operacional adecuada. No se deben publicar credenciales ni información confidencial en variables de entorno o en el repositorio.

## Seguridad y acceso

El servidor no intenta eludir CAPTCHA, controles anti-bot, autenticación, paywalls ni límites de acceso. Si una fuente no permite acceso automatizado, se debe utilizar el enlace para consulta manual.

El endpoint remoto está diseñado como **MCP de lectura/investigación**: no ofrece herramientas para modificar las fuentes judiciales.

ChatGPT advierte que conectar servidores MCP inseguros puede aumentar riesgos como prompt injection. Por ello, el servidor debe desplegarse, revisarse y mantenerse bajo control del propietario antes de conectarlo a un cliente externo.

## Privacidad

No se incluyen credenciales en el repositorio. No se almacenan expedientes, consultas ni documentos del usuario por defecto.

**Para uso jurídico:** las consultas deben estar anonimizadas y no deben incluir información confidencial del cliente cuando no sea necesaria para localizar jurisprudencia.

## Uso profesional

El MCP es una herramienta de investigación jurídica. Antes de citar una autoridad en un escrito u opinión, debe verificarse el documento original, su cita, contenido y vigencia/aplicabilidad.

## Licencia y contenido de terceros

El **código de este repositorio** está disponible bajo la **MIT License**. La licencia MIT aplica al software original de este proyecto; **no concede derechos sobre las sentencias, documentos, sitios web, marcas, bases de datos ni otro contenido de terceros** que el MCP pueda consultar o recuperar.

Los usuarios son responsables de cumplir las condiciones de uso y los derechos aplicables a cada fuente. Las decisiones judiciales deben verificarse en la fuente original antes de su uso profesional.

## Licencia

MIT — ver [`LICENSE`](LICENSE).
