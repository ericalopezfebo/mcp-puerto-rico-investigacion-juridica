# VELUM — MCP para documentos legales y jurisprudencia de Puerto Rico 🇵🇷

**VELUM** es un servidor MCP local-first que combina dos capacidades separadas:

1. **Privacidad documental local:** prepara documentos jurídicos sensibles antes de compartirlos con una IA.
2. **Investigación de jurisprudencia:** busca decisiones públicas de Puerto Rico y recupera evidencia directamente de las fuentes.

## Jurisprudencia: búsqueda verificable, no citas inventadas

La herramienta principal para investigación temática es `investigar_sentencias`.

Ejemplo de uso desde Claude u otro cliente MCP:

> Busca las 5 mejores sentencias de Puerto Rico que ayuden a mi argumento sobre pensión alimenticia. Dame la cita TSPR, enlace oficial, página y el pasaje relevante. No inventes nada.

El flujo es:

```text
Consulta jurídica
      │
      ▼
VELUM MCP
      │
      ├── índice público del Poder Judicial
      ├── páginas por año
      ├── PDFs de decisiones
      ├── extracción del texto fuente
      └── búsqueda/ranking documental
              │
              ▼
   cita TSPR + URL + pasaje + página
              │
              ▼
       análisis del modelo
```

### Garantía de procedencia

VELUM no trata al LLM como fuente de autoridad. Para los resultados de investigación:

- la decisión debe encontrarse en una fuente permitida;
- el PDF se descarga desde la fuente pública;
- el texto relevante se extrae del documento;
- la cita TSPR se devuelve cuando aparece en el documento;
- el pasaje se devuelve desde el texto extraído, no generado por el modelo;
- la página del PDF se conserva cuando puede identificarse;
- si una cita exacta no aparece, `buscar_por_cita` no la sustituye por otra;
- los datos que la fuente no proporciona se dejan vacíos;
- el ranking mide coincidencia textual/temática y **no declara por sí mismo que una sentencia sea jurídicamente favorable**.

Esto permite que Claude o ChatGPT haga la parte de razonamiento jurídico sobre evidencia que primero fue recuperada de una fuente identificable.

### Herramientas de jurisprudencia

#### `investigar_sentencias`

Busca dentro del contenido de decisiones públicas y devuelve las autoridades potencialmente más relevantes para una consulta.

Devuelve, cuando están disponibles:

- cita TSPR;
- URL oficial;
- fuente;
- puntuación de relevancia documental;
- pasaje relevante extraído;
- página del PDF;
- número de caso si puede extraerse de la fuente.

#### `buscar_sentencias`

Busca decisiones en los índices públicos y, cuando el índice no contiene lenguaje temático suficiente, utiliza búsqueda dentro de documentos.

#### `buscar_por_cita`

Verifica una cita TSPR exacta. Si no se encuentra, devuelve `verificado: false` y no inventa ni sustituye la autoridad.

#### `leer_sentencia`

Abre una URL permitida de una decisión y devuelve pasajes directamente extraídos del PDF/HTML, con página cuando está disponible.

#### `opciones_busqueda` y `estado`

Exponen las fuentes, herramientas y garantías técnicas del servidor.

### Límite importante

Una coincidencia textual no equivale automáticamente al **holding** de una sentencia. Antes de citar una autoridad en un escrito, el usuario debe leer la decisión, comprobar qué resolvió realmente el Tribunal y verificar vigencia, precedentes posteriores y aplicabilidad al problema concreto.

VELUM deliberadamente no inventa esa parte.

## Fuentes de jurisprudencia

- Poder Judicial de Puerto Rico: https://poderjudicial.pr/tribunal-supremo/decisiones-del-tribunal-supremo/
- LexJuris: https://www.lexjuris.com/lexbusquedas.htm

El servidor no elude CAPTCHA, autenticación ni controles de acceso.

---

# Privacidad documental local

La parte de privacidad de VELUM procesa los documentos **en la computadora donde se ejecuta el MCP**. No necesita una cuenta de VELUM, una base de datos remota ni un servidor VELUM para anonimizar el documento.

```text
Documento legal original
        │
        ▼
   VELUM en tu equipo
        │
        ├── extracción local
        ├── redacción determinística
        ├── reglas personalizadas
        └── copia sanitizada local
                │
                ▼
       revisión humana
                │
                ▼
       IA externa, si el usuario decide compartir
```

- El archivo original se lee desde `VELUM_DOCUMENT_ROOT`.
- Las herramientas de privacidad no hacen llamadas HTTP para procesar documentos.
- VELUM usa MCP **stdio** para el servidor local.
- El original no se modifica.
- La copia anonimizada se crea dentro del directorio local permitido.
- La huella SHA-256 se calcula localmente sin devolver el contenido.
- La ruta de un documento se valida para impedir acceso fuera del directorio autorizado.

### Límite de privacidad

VELUM protege el documento original durante el procesamiento local, pero no puede controlar lo que el usuario posteriormente envíe a un proveedor de IA.

Si una herramienta devuelve texto a ChatGPT, Claude u otra IA, ese texto sale del equipo y llega al proveedor de IA. La revisión humana sigue siendo necesaria.

## No usamos un LLM para anonimizar

La anonimización básica es determinística, mediante reglas locales. Actualmente contempla, entre otros:

- correo electrónico;
- teléfonos con formato estadounidense/PR;
- SSN;
- números de tarjeta;
- fechas identificadas explícitamente como fecha de nacimiento;
- redacciones personalizadas definidas por el usuario.

Esto no constituye una garantía de anonimización completa.

## Instalación

Requiere Python 3.10+.

```bash
git clone https://github.com/ericalopezfebo/mcp-puerto-rico-sentencias.git
cd mcp-puerto-rico-sentencias
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[test]"
```

Para las herramientas de privacidad local, configura el directorio de documentos:

```bash
mkdir -p ~/Documents/VELUM
export VELUM_DOCUMENT_ROOT="$HOME/Documents/VELUM"
```

## Ejecutar

Para iniciar el servidor local:

```bash
mcp-puerto-rico-sentencias
```

También puede ejecutarse con:

```bash
python3 server.py
```

El servidor MCP por `stdio` normalmente no abre una ventana: queda esperando mensajes del cliente MCP. Eso es normal.

## Clientes de IA

### Claude y clientes MCP locales

Un cliente compatible con MCP/stdio puede iniciar el servidor local y utilizar sus herramientas.

### ChatGPT

ChatGPT puede utilizar apps MCP personalizadas, pero el mecanismo depende del producto y del plan. Actualmente OpenAI indica que ChatGPT se conecta a **servidores MCP remotos**, no directamente a un servidor MCP local por stdio. Para conectar un servidor que corre en una computadora de desarrollo se necesita una capa compatible, como un túnel MCP seguro. Consulta la documentación vigente de OpenAI antes de desplegarlo.

Por eso este repositorio se puede descargar y ejecutar localmente para clientes MCP compatibles, mientras que para ChatGPT el siguiente paso de despliegue es exponer el MCP mediante una conexión remota compatible.

## Seguridad

- No se inventan casos, citas, nombres, fechas, holdings ni citas textuales.
- No se eluden controles de acceso de las fuentes.
- Las URLs de documentos están restringidas a los hosts configurados.
- No se almacenan consultas ni documentos por defecto.
- Los documentos originales no se modifican por las herramientas de privacidad.

## Pruebas

```bash
pytest -q
```

## Licencia

El código original está disponible bajo **MIT License**. La licencia del software no concede derechos sobre sentencias, sitios web, marcas, bases de datos u otros contenidos de terceros.
