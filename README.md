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

- `investigar_sentencias` — la herramienta principal para argumentos jurídicos: busca dentro del **texto real** de las sentencias públicas (no solo en el índice), puntúa por coincidencia temática y devuelve las mejores autoridades **ya verificadas** contra el PDF oficial, con cita, número de caso, página y pasaje exacto. Si no existen suficientes decisiones pertinentes y verificables, devuelve menos de las solicitadas — nunca rellena con casos marginales.
- `buscar_sentencias` — búsqueda por palabras/frases, año y máximo de resultados.
- `buscar_por_cita` — búsqueda **exacta y verificable** por cita TSPR.
- `leer_sentencia` — descarga y extracción de texto desde HTML/PDF público, con pasajes relevantes y procedencia.
- `opciones_busqueda` — fuentes, filtros y reglas de integridad.
- `estado` — diagnóstico y garantías de integridad de citas.

### Cómo prioriza y por qué puede devolver menos resultados de los pedidos

El índice oficial del Tribunal Supremo no incluye materia/asunto junto a cada enlace — solo la cita. Por eso `investigar_sentencias` no puede clasificar por tema sin abrir los documentos. Para responder en un tiempo razonable sin descargar cientos de PDFs innecesariamente, la búsqueda avanza **por rondas**: revisa un año a la vez (empezando por el más reciente), lee y verifica un lote acotado de sus PDFs, y se detiene en cuanto encuentra suficientes resultados verificados o agota su presupuesto de lectura. La respuesta incluye `anos_explorados` y `anos_no_explorados` para que quede claro qué se revisó realmente — un año en `anos_no_explorados` significa que no se llegó a revisar en esa llamada, **no** que ahí no haya jurisprudencia relevante.

## Ejemplos de uso

> “Busca las mejores 5 sentencias del Tribunal Supremo de Puerto Rico que apoyen mi argumento sobre pensión alimenticia.”

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

Requiere Python 3.10+ y [Git](https://git-scm.com/downloads).

```bash
git clone https://github.com/ericalopezfebo/mcp-puerto-rico-sentencias.git
cd mcp-puerto-rico-sentencias
python -m venv .venv
source .venv/bin/activate   # en Windows: .venv\Scripts\activate
pip install -e .
```

Para ejecutar las pruebas:

```bash
pip install -e ".[test]"
pytest -q
```

### Claude Desktop / Cowork

Agrega esto al archivo de configuración de Claude Desktop:

- macOS: `~/Library/Application Support/Claude/claude_desktop_config.json`
- Windows: `%APPDATA%\Claude\claude_desktop_config.json`

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

En Windows, `command` apunta a `C:\ruta\al\repositorio\.venv\Scripts\python.exe` (el layout del venv es distinto: `Scripts\` en vez de `bin/`).

Reinicia Claude Desktop después de guardar el archivo.

### Claude Code (CLI)

```bash
claude mcp add puerto-rico-sentencias -- /ruta/al/repositorio/.venv/bin/python /ruta/al/repositorio/server.py
```

En Windows, usa `.venv\Scripts\python.exe` en vez de `.venv/bin/python`.

En ambos casos, usa la ruta absoluta al intérprete dentro de `.venv` creado en el paso anterior (no el `python` del sistema), para que el servidor arranque con las dependencias del proyecto ya instaladas.

### Verifica que quedó conectado

- **Claude Desktop:** después de reiniciar, el ícono de 🔌/herramientas en el cuadro de mensaje debe mostrar `puerto-rico-sentencias` con sus herramientas listadas (`investigar_sentencias`, `buscar_sentencias`, `buscar_por_cita`, `leer_sentencia`, `opciones_busqueda`, `estado`). Si no aparece, revisa que la ruta al `.venv/bin/python` en el JSON sea absoluta y exista.
- **Claude Code:** ejecuta `claude mcp list` — debe aparecer `puerto-rico-sentencias` como conectado (no como "Pending approval" ni con error).
- **Prueba rápida en cualquiera de los dos:** pídele a Claude que use la herramienta `estado` del MCP. Debe devolver un JSON con `"servidor": "puerto-rico-sentencias"` y las garantías de integridad. Esa llamada es instantánea (no toca la fuente pública), a diferencia de `investigar_sentencias`/`buscar_sentencias`, que sí consultan el sitio oficial y por eso pueden tardar.

### Servidor remoto (para ChatGPT u otros clientes HTTP)

**Opción con un clic (Render):** el repo incluye `render.yaml`, listo para un despliegue *Blueprint*:

1. Entra a [render.com](https://render.com) e inicia sesión (puedes usar tu cuenta de GitHub).
2. **New +** → **Blueprint** → selecciona tu fork/clon de este repositorio en GitHub.
3. Render detecta `render.yaml` y `Dockerfile` automáticamente y crea el servicio. Espera a que el build termine (unos minutos).
4. Copia la URL pública que Render asigna al servicio (algo como `https://mcp-puerto-rico-sentencias.onrender.com`) — el endpoint MCP es esa URL **+ `/mcp`**.

**Manual / otro proveedor:**

```bash
python remote_server.py
```

Por defecto escucha en `0.0.0.0` y usa el puerto `8000` o la variable `PORT` proporcionada por el proveedor de hosting. El endpoint MCP es `/mcp`.

Para producción, debe utilizarse un proveedor que proporcione **HTTPS** y protección operacional adecuada. No se deben publicar credenciales ni información confidencial en variables de entorno o en el repositorio.

### Conectar la URL remota a ChatGPT

1. En ChatGPT, entra a la configuración de conectores/apps (la ubicación exacta depende de tu plan/espacio de trabajo — busca "Connectors", "Apps" o "Conectar aplicaciones" en Configuración).
2. Agrega un conector personalizado y pega la URL con `/mcp` al final (paso 4 de arriba).
3. Guarda y actívalo en la conversación donde quieras usarlo. ChatGPT mostrará un aviso sobre conectar servidores MCP externos — es normal; revisa que la URL sea la tuya antes de aceptar.
4. Prueba pidiendo que use la herramienta `estado` para confirmar la conexión, igual que en Claude.

### Solución de problemas comunes

- **El MCP no aparece en Claude Desktop después de reiniciar.** Revisa que la ruta en `command` sea absoluta (no `~` ni rutas relativas) y apunte al `python` **dentro de `.venv`**, no al del sistema. Verifica el JSON con un validador — una coma de más lo invalida silenciosamente.
- **`ModuleNotFoundError` al iniciar.** Las dependencias se instalaron en un entorno distinto al que Claude está usando para lanzar el proceso. Vuelve a correr `pip install -e .` con el mismo `.venv` referenciado en la configuración.
- **`investigar_sentencias`/`buscar_sentencias` parecen "colgados" o tardan mucho.** Es esperado: leen y verifican PDFs reales contra el sitio oficial en cada llamada, así que una búsqueda temática amplia puede tardar 1-2 minutos. Si el cliente reporta timeout antes de eso, pide la búsqueda para un año específico (parámetro `anos`) — es más rápida porque cubre menos terreno.
- **Python menor a 3.10.** `pip install -e .` fallará indicando la versión requerida. Instala Python 3.10+ y vuelve a crear el `.venv`.
- **Windows: `source .venv/bin/activate` no funciona.** Usa `.venv\Scripts\activate` en PowerShell o CMD (ya indicado arriba).

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
