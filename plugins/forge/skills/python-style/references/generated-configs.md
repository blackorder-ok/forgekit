<!-- Reference for python-style: files scaffold writes unchanged. -->

## Generated: ruff.toml and mypy.ini
Scaffold writes both at the project root, unchanged.

```toml
target-version = "py311"
line-length = 100

# N (pep8-naming) is deliberately not selected: the team uses camelCase
# functions and variables and PascalCase classes.
[lint]
select = ["E", "F", "I", "S", "B", "UP"]

[lint.per-file-ignores]
"tests/**" = ["S101"]
```

```ini
[mypy]
python_version = 3.11
strict = True
files = backend
```
