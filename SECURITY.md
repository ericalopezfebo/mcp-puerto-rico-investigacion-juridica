# Security model

## Local document boundary

VELUM's privacy tools are designed to run as an MCP stdio process on the user's machine. They do not contain an outbound HTTP client and do not upload local document files to a VELUM server.

Local document access is restricted to `VELUM_DOCUMENT_ROOT`, which defaults to `~/Documents/VELUM`.

## External AI boundary

MCP is a bridge between a host application and tools. If a tool returns document text to an external AI service, that returned text is available to that service. VELUM therefore recommends:

1. keep the original file local;
2. run deterministic redaction locally;
3. inspect the sanitized result;
4. send only the approved sanitized text to an external model.

VELUM does not claim that a redaction engine can identify every sensitive fact in a legal document.

## Do not expose the local server

The local privacy server is intentionally stdio-only. Do not replace it with a public HTTP endpoint unless a separate security design, authentication, authorization, logging policy and threat model have been completed.

## Reporting vulnerabilities

Do not include client documents, confidential facts, credentials, API keys, or other sensitive material in a GitHub issue. Report security concerns with the minimum information necessary to reproduce the problem.
