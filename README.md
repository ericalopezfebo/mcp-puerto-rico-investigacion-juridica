# VELUM — MCP local para documentos legales 🇵🇷

**VELUM** es un servidor MCP **local-first** para trabajar con documentos legales sensibles desde aplicaciones de IA compatibles con MCP.

Su diseño principal es simple:

```text
Documento legal en tu Mac/PC
        │
        ▼
   VELUM local
        │
        ├── extracción local
        ├── huella SHA-256 local
        └── anonimización/redacción local
                │
                ▼
        texto sanitizado
                │
                ▼
       ChatGPT / Claude / otra IA
```

## Qué protege

El documento original permanece en el dispositivo. Las herramientas de privacidad de VELUM:

- no suben archivos a VELUM ni a un servidor propio;
- no abren un puerto de red;
- funcionan mediante **MCP stdio**;
- no hacen llamadas HTTP para procesar documentos locales;
- permiten extraer texto de PDF, DOCX, TXT, Markdown y HTML localmente;
- pueden sustituir automáticamente identificadores comunes (email, teléfono, SSN, tarjeta y fecha de nacimiento etiquetada);
- permiten especificar redacciones adicionales, por ejemplo `{"Jane Doe":"[CLIENTE]"}`;
- pueden crear una copia anonimizada local;
- pueden generar un SHA-256 del archivo sin devolver su contenido.

### La regla de privacidad más importante

**VELUM no puede impedir que una IA externa reciba los datos que el usuario decida devolverle.**

Por eso el flujo recomendado para un documento confidencial es:

1. El archivo se queda en tu equipo.
2. VELUM lo procesa localmente.
3. VELUM devuelve únicamente el texto sanitizado.
4. El usuario revisa el resultado.
5. Solo entonces ese texto sanitizado puede enviarse a ChatGPT, Claude u otra IA.

No debe afirmarse que el contenido está "100% privado" frente al proveedor de IA si el texto se envía a ese proveedor. **La garantía de VELUM es que el archivo original no se envía a un servidor de VELUM y que la sanitización ocurre antes de compartir contenido con una IA externa.**

## Importante sobre ChatGPT y Claude

Los servidores MCP locales usan normalmente **stdio**: la aplicación de IA ejecuta VELUM como un proceso local en la misma computadora. El SDK oficial de MCP documenta este patrón como el modelo de despliegue local.

Claude Desktop admite servidores MCP locales y también permite empaquetarlos como extensiones `.mcpb`.

**ChatGPT es diferente:** actualmente ChatGPT no se conecta directamente a un MCP que solo corre localmente. OpenAI documenta el uso de servidores MCP remotos o de Secure MCP Tunnel para conectar un servidor que permanece local sin exponerlo públicamente.

Por eso hay dos escenarios:

### Claude Desktop / clientes con MCP local

VELUM puede ejecutarse completamente local mediante stdio. El cliente inicia el proceso en tu computadora.

### ChatGPT

Para que ChatGPT pueda usar un MCP local hay que utilizar el mecanismo de conexión que admita el producto, actualmente Secure MCP Tunnel para este caso. **Eso no convierte el documento original en un documento remoto:** el servidor y el archivo pueden permanecer en tu máquina, pero cualquier texto que VELUM devuelva a ChatGPT será recibido por ChatGPT.

Para documentos confidenciales, el flujo recomendado sigue siendo **anonimizar primero y enviar después**.

## Instalación

Requiere Python 3.10+.

```bash
git clone https://github.com/ericalopezfebo/mcp-puerto-rico-sentencias.git
cd mcp-puerto-rico-sentencias

python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[test]"
```

Crea el directorio protegido de documentos:

```bash
mkdir -p ~/Documents/VELUM
```

Puedes cambiarlo:

```bash
export VELUM_DOCUMENT_ROOT="$HOME/Documents/VELUM"
```

## Ejecutar el MCP local

El comando principal es:

```bash
velum
```

También puedes ejecutar directamente:

```bash
python3 velum.py
```

**No esperes que aparezca un mensaje en pantalla.** Un servidor MCP stdio queda esperando mensajes del cliente. No abre un puerto y no termina hasta que el cliente lo cierre.

Para detenerlo manualmente:

```text
Ctrl+C
```

## Herramientas de privacidad local

### `listar_documentos_locales`

Lista nombres y metadatos de documentos permitidos dentro de `VELUM_DOCUMENT_ROOT` sin devolver su contenido.

### `huella_documento_local`

Calcula SHA-256 localmente. Es útil para demostrar que un archivo cambió sin enviar el archivo.

### `preparar_documento_para_ia`

Lee el archivo localmente, extrae su texto y aplica redacciones determinísticas. Devuelve **solo el resultado sanitizado**.

Ejemplo de redacciones adicionales:

```json
{
  "Jane Doe": "[CLIENTE]",
  "Acme Holdings LLC": "[EMPRESA]",
  "787-555-9876": "[TELEFONO_CLIENTE]"
}
```

### `crear_copia_anonimizada`

Crea una copia `.anonimizado.txt` dentro del directorio local permitido. El original no se modifica.

### `estado_privacidad`

Muestra las garantías técnicas del modo local y deja explícito qué ocurre cuando el texto sanitizado se entrega a una IA externa.

## Herramientas de jurisprudencia de Puerto Rico

El mismo MCP también conserva la investigación de jurisprudencia de Puerto Rico:

- `buscar_sentencias`
- `buscar_por_cita`
- `leer_sentencia`
- `opciones_busqueda`
- `estado`

Estas herramientas consultan fuentes públicas judiciales y LexJuris. **Solo esa parte necesita Internet para buscar decisiones públicas.** Las herramientas de privacidad local no usan esas llamadas de red.

La política jurídica sigue siendo **source-first / zero citation hallucination**: no se deben inventar casos, citas, nombres, fechas, holdings ni citas textuales.

## Tipos de documentos

- PDF
- DOCX
- TXT
- Markdown
- HTML

Límite predeterminado: **25 MB por archivo**.

## Seguridad del sistema de archivos

VELUM no permite que las herramientas locales lean cualquier ruta arbitraria del sistema.

Por defecto solo acepta archivos dentro de:

```text
~/Documents/VELUM
```

También puede configurarse mediante `VELUM_DOCUMENT_ROOT`.

Esto evita que una llamada de herramienta pueda intentar leer, por ejemplo, `/Users/.../.ssh`, `/etc/passwd` u otros archivos fuera del directorio autorizado.

## Qué NO hace VELUM

- No envía documentos a un servidor propio.
- No guarda expedientes en una base de datos remota.
- No usa una API de OpenAI, Anthropic u otro proveedor para anonimizar documentos.
- No usa un LLM para decidir qué texto debe ocultar.
- No promete detectar todos los datos personales automáticamente.
- No modifica el archivo original.

La anonimización automática es **determinística y limitada**. En documentos jurídicos reales puede haber nombres, direcciones, identificadores, hechos sensibles o combinaciones de datos que requieran revisión humana y/o reglas personalizadas.

## Integridad jurídica

Este proyecto no sustituye la revisión profesional de una autoridad jurídica. Antes de utilizar una sentencia en un escrito, debe verificarse el documento original, la cita, su contenido y su vigencia/aplicabilidad.

## Pruebas

Ejecuta:

```bash
pytest -q
```

Las pruebas cubren tanto la integridad de citas como las garantías básicas de privacidad local, incluyendo:

- redacción de identificadores comunes;
- redacciones personalizadas;
- prohibición de devolver el original desde la herramienta de preparación;
- rechazo de rutas fuera de `VELUM_DOCUMENT_ROOT`.

## Distribución local

El proyecto puede distribuirse como código fuente desde GitHub. El ecosistema MCP también dispone del formato **MCP Bundle (`.mcpb`)** para empaquetar servidores locales con un manifiesto y facilitar instalaciones de un clic en clientes compatibles.

La siguiente evolución natural de este repositorio es publicar un `.mcpb` para VELUM, especialmente para Claude Desktop.

## Licencia

El código original está disponible bajo la **MIT License**. La licencia del software no concede derechos sobre sentencias, sitios web, marcas, bases de datos u otros contenidos de terceros.
