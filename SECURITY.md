# Security Policy

## Reporting a vulnerability

If you discover a security vulnerability in LogicaHome, **please do not open a public issue**. Instead, report it privately:

1. Use GitHub's [private vulnerability reporting](https://github.com/Rovemark/logicahome/security/advisories/new) for this repository, or
2. Email the maintainer directly (see profile for contact).

You should expect an initial response within 7 days. We will work with you to validate, fix, and disclose the issue responsibly.

## Scope

LogicaHome runs on the user's own hardware and talks to their own devices on their own network. The threat model focuses on:

- **Credentials and tokens.** Adapter configs may contain device keys and API tokens. Any code path that logs, transmits, or persists these incorrectly is in scope.
- **MCP tool surface.** The tools exposed to AI clients must not enable lateral movement beyond device control (e.g. arbitrary command execution, filesystem reads outside the registry).
- **Adapter input handling.** Untrusted JSON/YAML from device endpoints must not crash, hang, or escalate the daemon.

Out of scope: misconfiguration by the user (e.g. exposing the MCP server to the public internet), bugs in upstream vendor APIs, and attacks that require pre-existing root on the host.

## Supported versions

Until 1.0, only `main` and the latest tagged release receive security fixes.

## Coordinated disclosure

We will coordinate a fix and a public advisory before disclosing details. Credit is given to reporters by default.
