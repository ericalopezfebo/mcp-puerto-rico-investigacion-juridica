# MCP Puerto Rico — Investigación Jurídica 🇵🇷

## Investigación jurídica verificable desde Claude, ChatGPT y otros clientes MCP

**MCP Puerto Rico — Investigación Jurídica** es una plataforma abierta de investigación jurídica de Puerto Rico. El objetivo es localizar y verificar **jurisprudencia, legislación, reglamentos, órdenes ejecutivas, decisiones administrativas y actualidad jurídica pública** sin convertir al modelo de lenguaje en fuente de autoridad.

> **Regla central: source-first / zero legal hallucination.** Si una autoridad, cita, nombre, número de caso, fecha, página o pasaje no puede verificarse en una fuente identificable, el MCP no debe inventarlo ni rellenarlo.

El repositorio y el paquete Python se llaman `mcp-puerto-rico-investigacion-juridica`. Los comandos históricos `mcp-puerto-rico-sentencias` se mantienen como aliases de compatibilidad para instalaciones existentes.

## Qué cubre

### Fuentes primarias oficiales

- **Tribunal Supremo de Puerto Rico** — opiniones, sentencias y resoluciones públicas.
- **Tribunal de Apelaciones** — determinaciones finales públicas disponibles desde enero de 2015, salvo casos confidenciales.
- **Biblioteca Jurídica Virtual del Departamento de Estado** — leyes, resoluciones conjuntas, reglamentos, órdenes ejecutivas, decretos y proclamas disponibles públicamente.
- **Junta de Relaciones del Trabajo de Puerto Rico** — decisiones y órdenes, órdenes administrativas y otros documentos públicos laborales.

### Fuente secundaria pública

- **Microjuris Al Día** — únicamente su búsqueda y contenido público para descubrir noticias, cambios y temas recientes. **No se accede al producto premium, no se usan credenciales, no se evade ningún paywall y no se replica la base de datos propietaria de Microjuris.** Una noticia nunca sustituye la sentencia, ley, reglamento u otra autoridad primaria correspondiente.

## Qué pretende replicar — y qué no

Este proyecto busca reproducir **funcionalidad de investigación** que normalmente ofrecen plataformas jurídicas comerciales: localizar fuentes, cruzar colecciones, encontrar autoridades relacionadas, extraer pasajes verificables y facilitar investigación temática.

No intenta copiar bases privadas, anotaciones editoriales, headnotes, clasificación propietaria ni contenido protegido de servicios de suscripción. Cuando el documento jurídico original está disponible públicamente, el MCP intenta trabajar directamente con ese original.

## Herramientas MCP

### Jurisprudencia del Tribunal Supremo — núcleo probado

- `investigar_sentencias` — busca dentro del texto real de PDFs públicos y devuelve autoridades verificadas con cita, número de caso, página y pasaje cuando están disponibles.
- `buscar_sentencias` — búsqueda temática por palabras/frases y año.
- `buscar_por_cita` — verificación exacta de una cita TSPR; no sustituye una cita inexistente por otra parecida.
- `leer_sentencia` — lee un documento público y extrae pasajes directamente de la fuente.

### Investigación jurídica ampliada

- `investigar_derecho_pr` — punto de entrada multi-fuente. Coordina candidatos del Tribunal Supremo y Tribunal de Apelaciones y orienta hacia fuentes oficiales adicionales.
- `buscar_decisiones_apelaciones` — busca determinaciones finales públicas del Tribunal de Apelaciones por año y texto visible en el índice oficial.
- `buscar_biblioteca_juridica` — busca enlaces visibles en la Biblioteca Jurídica Virtual del Departamento de Estado.
- `buscar_decisiones_laborales` — descubre decisiones y órdenes públicas de la Junta de Relaciones del Trabajo.
- `buscar_actualidad_juridica` — busca noticias/análisis públicos de Microjuris Al Día y los marca expresamente como **fuente secundaria**.
- `catalogo_fuentes_juridicas` — muestra las colecciones integradas y su jerarquía.
- `estado_investigacion_juridica` — diagnóstico de la capa ampliada.

Las herramientas existentes `opciones_busqueda` y `estado` continúan disponibles por compatibilidad con la etapa original del proyecto.

## Ejemplos

> “Investiga la obligación alimentaria de los padres en Puerto Rico. Dame las mejores autoridades primarias verificables: ley, reglamento aplicable si existe y jurisprudencia. Para cada caso cita la página y el pasaje exacto.”

> “¿Qué cambió con la doctrina Chevron? Busca primero actualidad jurídica pública para detectar el desarrollo y después identifica la autoridad primaria que realmente cambió la doctrina. No uses el artículo como sustituto de la sentencia.”

> “Busca decisiones administrativas laborales sobre negociación colectiva y luego identifica jurisprudencia del Tribunal Supremo relacionada.”

> “Busca el reglamento aplicable y casos recientes sobre revisión judicial de decisiones de agencias administrativas.”

> “Si solo encuentras tres autoridades verificables, devuelve tres. No completes la lista con casos marginales ni inventados.”

## Arquitectura de confianza

```text
PREGUNTA JURÍDICA
        ↓
DETECCIÓN DE MATERIA / TIPO DE AUTORIDAD
        ↓
FUENTES PRIMARIAS OFICIALES
  ├─ Constitución / leyes
  ├─ Reglamentos
  ├─ Tribunal Supremo
  ├─ Tribunal de Apelaciones
  └─ Decisiones administrativas
        ↓
EXTRACCIÓN / IDENTIFICACIÓN
        ↓
VERIFICACIÓN
        ↓
PASAJES + PÁGINA + URL + METADATOS
        ↓
CLAUDE / CHATGPT / OTRO CLIENTE MCP
```

Las fuentes secundarias públicas se usan como **descubrimiento/contexto**, no como sustituto de la autoridad primaria.

## Taxonomía y datos semilla

El proyecto utiliza una taxonomía de `tipo de autoridad → materia → tema específico → fuente → estado de verificación`. Un inventario desarrollado para el proyecto `legal-agents` contiene alrededor de 450 autoridades de derecho administrativo, constitucional y penal, incluyendo TSPR/DPR, decisiones federales, leyes especiales, códigos y reglamentos.

Ese inventario se trata como **seed de investigación**, no como fuente de verdad. Algunas entradas están expresamente marcadas “Pendiente de verificar” o contienen notas de posible error. Ninguna entrada debe convertirse en autoridad confirmada hasta localizarse en una fuente verificable.

Ver [`docs/taxonomia-autoridades.md`](docs/taxonomia-autoridades.md).

## Instalación local

Requiere Python 3.10+ y Git.

```bash
git clone https://github.com/ericalopezfebo/mcp-puerto-rico-investigacion-juridica.git
cd mcp-puerto-rico-investigacion-juridica
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -e .
```

Comando principal:

```bash
mcp-puerto-rico-investigacion-juridica
```

Los comandos históricos siguen funcionando:

```bash
mcp-puerto-rico-sentencias
```

### Claude Desktop / Cowork

Ejemplo de configuración local:

```json
{
  "mcpServers": {
    "puerto-rico-investigacion-juridica": {
      "command": "/RUTA/AL/REPO/.venv/bin/python",
      "args": ["/RUTA/AL/REPO/research_server.py"]
    }
  }
}
```

En Windows usa `.venv\\Scripts\\python.exe`.

### Claude Code

```bash
claude mcp add puerto-rico-investigacion-juridica -- /RUTA/AL/REPO/.venv/bin/python /RUTA/AL/REPO/research_server.py
```

## ChatGPT / servidor remoto

El repositorio incluye `remote_server.py`, `Dockerfile` y `render.yaml`. El servidor remoto expone el mismo conjunto de herramientas mediante Streamable HTTP en:

```text
https://TU-DOMINIO/mcp
```

Una instancia desplegada con el nombre histórico puede continuar usando temporalmente su dominio anterior durante la migración de branding. El endpoint de demostración no tiene SLA y un plan gratuito puede sufrir arranque en frío o timeouts.

## Integridad jurídica

El MCP debe observar estas reglas:

1. **No inventar autoridades.**
2. **No inventar citas, nombres, números de expediente, fechas, páginas o quotations.**
3. **Distinguir fuente primaria de secundaria.**
4. **Conservar URL y procedencia.**
5. **Una coincidencia temática no equivale a holding.**
6. **No presentar una noticia como derecho vigente.**
7. **No determinar vigencia de una ley/reglamento sin evidencia suficiente.**
8. **Si la evidencia no alcanza, devolver menos resultados.**
9. **No acceder ni intentar eludir contenido de suscripción.**
10. **Preferir “no verificado” a una conclusión plausible pero no demostrada.**

## Estado de cobertura

| Colección | Estado |
|---|---|
| Tribunal Supremo | ✅ Búsqueda temática, lectura de PDF, cita/página/pasaje |
| Tribunal de Apelaciones | 🟡 Índice oficial y búsqueda inicial |
| Leyes / resoluciones conjuntas | 🟡 Portal oficial integrado; profundización pendiente |
| Reglamentos | 🟡 Portal oficial integrado; vigencia/historial pendiente |
| Órdenes ejecutivas | 🟡 Portal oficial integrado |
| Decisiones administrativas laborales | 🟡 Descubrimiento oficial inicial |
| Autoridad federal | ⏳ Próxima expansión |
| Actualidad jurídica pública | 🟡 Microjuris Al Día como fuente secundaria |
| Grafo de citas / tratamiento posterior | ⏳ Futuro |

## Licencia y contenido de terceros

El **código de este repositorio** se publica bajo licencia MIT. Eso no convierte en MIT los documentos, sitios o contenido de terceros a los que el MCP enlaza o consulta. Cada fuente mantiene sus propios términos, derechos y políticas.

Este proyecto no está afiliado ni respaldado por el Poder Judicial de Puerto Rico, el Departamento de Estado, la Junta de Relaciones del Trabajo ni Microjuris.

## Aviso

Herramienta de investigación jurídica. No sustituye la revisión profesional de las autoridades, historial, vigencia, tratamiento posterior ni expediente oficial. Antes de presentar una autoridad en un escrito, verifica la fuente primaria y su estado actual.
