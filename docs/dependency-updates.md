# Dependency update policy

The reliability baseline supports CPython 3.10 through 3.13. Runtime and optional
dependency ranges live in `pyproject.toml`; every direct dependency has both a
minimum and a compatibility ceiling. `constraints/py310.txt` and
`constraints/py313.txt` are the reproducible, fully resolved runtime + `dev`
environments used by CI. Separate locks prevent a newer binary dependency from
silently dropping Python 3.10 wheel support. The optional `external` parser
stack is intentionally not part of the default baseline lock or CI.
`constraints/compatibility.txt` records transitive wheel ceilings that upstream
packages do not declare correctly; each entry must include a reason.

Install the baseline environment with:

```powershell
python -m pip install -c constraints/py313.txt -e ".[dev]"
```

To update dependencies, change bounds deliberately in `pyproject.toml`, then
regenerate the universal lock from the repository root:

```powershell
uv pip compile pyproject.toml --extra dev --universal --upgrade `
  --constraints constraints/compatibility.txt `
  --python-version 3.10 --output-file constraints/py310.txt
uv pip compile pyproject.toml --extra dev --universal --upgrade `
  --constraints constraints/compatibility.txt `
  --python-version 3.13 --output-file constraints/py313.txt
```

Review the resulting diff for major-version changes and transitive additions.
Before merging, install from the new lock and run the backend suite, M1 matrix,
encoding gate, Ruff, and mypy locally. GitHub Actions repeats the backend suite
on Python 3.10 and 3.13 and verifies the frontend with the pinned Node version.
Never hand-edit a single transitive pin without regenerating and testing the
complete lock.
