# Release process

LogicaHome cuts patch and minor releases on demand. The flow is the same either way.

## Cutting a release

1. Make sure `main` is green: lint, tests, type checks.
2. Bump version in two places:
   - `src/logicahome/__init__.py` (`__version__`)
   - `pyproject.toml` (`[project] version`)
3. Update `CHANGELOG.md`:
   - Move `[Unreleased]` items into a new dated section.
   - Add a new empty `[Unreleased]` block.
   - Add the comparison link at the bottom.
4. Commit (`release: vX.Y.Z`) and push.
5. Tag and push the tag:

   ```bash
   git tag -a vX.Y.Z -m "vX.Y.Z — short headline"
   git push --follow-tags
   ```

6. The `Release` workflow builds sdist + wheel and creates a GitHub Release with both attached.
7. PyPI publishing is gated until trusted publishing is configured (see below).
8. Run the [hardware testing checklist](hardware-testing.md) on the release artifact before announcing.

## PyPI trusted publishing (one-time setup)

1. Register the project on [pypi.org](https://pypi.org).
2. Add `Rovemark/logicahome` as a trusted publisher with workflow `release.yml`.
3. Uncomment the `pypi:` job at the bottom of [`.github/workflows/release.yml`](../.github/workflows/release.yml).
4. Push a new patch tag — wheel + sdist publish automatically. No long-lived tokens.

## Versioning

LogicaHome follows [SemVer](https://semver.org). Until 1.0:

- **Patch** (0.x.Y): bug fixes, internal refactors, doc-only changes.
- **Minor** (0.X.0): new adapters, new MCP tools, new CLI subcommands.
- **Major** (X.0.0): reserved for 1.0 — stable adapter API, freeze the MCP tool schema.

Adapter API and MCP tool schemas may change between minor releases. Pin a version in production.
