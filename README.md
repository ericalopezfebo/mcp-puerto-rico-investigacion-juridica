# MCP Puerto Rico Sentencias 🇵🇷

Servidor **Model Context Protocol (MCP)** para buscar y consultar jurisprudencia de Puerto Rico desde clientes compatibles con MCP.

El proyecto toma como referencia la experiencia de [DerechoVirtual/mcp-cendoj-sentencias](https://github.com/DerechoVirtual/mcp-cendoj-sentencias), pero está diseñado específicamente para las fuentes públicas de Puerto Rico.

## Fuentes

- **Poder Judicial de Puerto Rico — Tribunal Supremo:** índice oficial de decisiones, con páginas por año desde 1998 y metadatos como TSPR, número de caso, partes, fecha, ponente y materia.
- **LexJuris:** portal jurídico de Puerto Rico, utilizado como fuente complementaria para localizar jurisprudencia y documentos cuando estén públicamente accesibles.

> El servidor no pretende sustituir la consulta de la fuente oficial. Los resultados incluyen la fuente y URL cuando están disponibles para facilitar la verificación.

## Herramientas MCP

- `buscar_sentencias`: búsqueda por palabras/frases, con filtros de año y máximo de resultados.
- `buscar_por_cita`: localiza una decisión por cita TSPR o número de caso.
- `leer_sentencia`: recupera y extrae el texto de una decisión pública a partir de su URL.
- `opciones_busqueda`: devuelve años disponibles y orientación sobre las fuentes.
- `estado`: diagnóstico del servidor y fuentes configuradas.

## Instalación

Requiere Python 3.10+.

```bash
python -m venv .venv
# macOS/Linux
source .venv/bin/activate
# Windows PowerShell
# .venv\\Scripts\\Activate.ps1

pip install -e .
```

### Claude Desktop / Cowork

Ejemplo de configuración:

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

En Windows usa `python.exe` dentro de `.venv\\Scripts\\`.

## Ejemplos

> “Busca sentencias del Tribunal Supremo de Puerto Rico sobre daños punitivos entre 2018 y 2025.”

> “Busca la cita 2024 TSPR 140 y dime el número del caso, las partes, fecha y materia.”

> “Encuentra decisiones sobre cláusulas de arbitraje y dame los enlaces a la fuente oficial.”

> “Lee la sentencia de esta URL y extrae los pasajes relevantes sobre jurisdicción.”

## Diseño

El código separa la obtención de datos de las herramientas MCP. Esto permite añadir posteriormente adaptadores para Tribunal de Apelaciones, Tribunal Federal para el Distrito de Puerto Rico u otras fuentes sin cambiar la interfaz MCP.

El servidor usa peticiones HTTP estándar, caché en memoria de corta duración y límites conservadores para evitar consultas innecesarias a sitios públicos.

## Uso responsable

Utiliza el servidor para investigación jurídica legítima y respetuosa con las condiciones de cada fuente. No intenta eludir CAPTCHA, controles anti-bot, autenticación, paywalls ni límites de acceso. Si una fuente no permite acceso automatizado, el servidor devuelve el enlace para consulta manual.

Los resultados deben verificarse en la fuente original antes de utilizarlos en escritos, opiniones legales o decisiones profesionales.

## Privacidad

No se incluyen credenciales en el repositorio. Las consultas se envían a las fuentes necesarias para obtener resultados. No se almacenan expedientes ni documentos del usuario por defecto.

## Licencia

MIT.
