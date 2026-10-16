# Secure remote deployment

The public legal-research sources used by this service do not make user queries public. A query may itself contain client facts, legal strategy, or work product.

Production deployments must:

1. expose the container only through an HTTPS reverse proxy;
2. authenticate every MCP client and reject anonymous traffic;
3. apply per-user and per-IP rate limits, request-size limits, deadlines, and concurrency limits;
4. avoid request-body, query, authorization-header, and tool-argument logging;
5. retain only aggregate operational metrics for a documented period;
6. use exact allowed hosts and HTTPS origins—never wildcards;
7. run the container with the included non-root, read-only, capability-free settings;
8. keep dependency, OS-image, and incident-response procedures current.

The provided Compose file binds to loopback intentionally. It is not a complete internet-facing deployment. Authentication belongs at the reverse proxy or a separately reviewed identity-aware gateway; do not remove the loopback binding merely to make the service reachable.

Advise users not to submit names, identifying facts, sealed information, privileged communications, or unnecessary matter details. Prefer abstract legal questions and synthetic examples.
