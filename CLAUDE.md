# Claude Code instructions — MCP Puerto Rico Investigación Jurídica

## Regla principal
Cuando el usuario pida investigación jurídica de Puerto Rico dentro de este repo, usa primero las herramientas del MCP local de este proyecto. No sustituyas silenciosamente una falla del MCP con una búsqueda web genérica prolongada.

## Top-N de jurisprudencia
Si el usuario pide “las mejores”, “las más relevantes”, “Top N”, “las que más apoyan mi argumento” o equivalente sobre decisiones del Tribunal Supremo de Puerto Rico, usa `buscar_mejores_sentencias` como herramienta principal. El ranking debe ser por relevancia jurídica, no por año.

## Falla de conexión: fail fast
Si el MCP local no responde, la conexión está obsoleta o el entorno virtual apunta a una ruta vieja:

1. Haz **un solo diagnóstico corto** de la conexión.
2. No gastes 10–20 minutos navegando la web para sustituir el MCP, salvo que el usuario lo autorice expresamente.
3. Explica el fallo concreto y la acción mínima para restablecer el MCP.
4. Si el repo fue renombrado o movido, sospecha primero rutas absolutas obsoletas en `.venv` o en la configuración MCP.

## Repo renombrado
El nombre actual es `mcp-puerto-rico-investigacion-juridica`. Si existe un entorno editable creado bajo la ruta histórica `mcp-puerto-rico-sentencias`, recrea o reinstala el entorno en la ruta actual antes de investigar:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .
```

Después, la configuración MCP local debe apuntar al Python y al `mixed_server.py` de la ruta actual del repo.

## Integridad jurídica
- No inventes casos, citas, holdings, páginas, números de caso ni texto.
- No presentes resultados de índice como autoridad verificada.
- Si una ley/reglamento depende de vigencia, usa la capa SUTRA antes de decir que está vigente.
- Si no hay 5 autoridades suficientemente pertinentes, devuelve menos.
- Si una fuente secundaria ayuda a descubrir una autoridad, verifica la proposición final contra fuente primaria.
