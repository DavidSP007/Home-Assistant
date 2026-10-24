# Development

## Set up

Install [uv](https://docs.astral.sh/uv/), then:

```shell
uv sync --group dev
```

## Quality gates

All four must pass before a commit (CLAUDE.md section 14). CI runs the same
commands, plus Home Assistant's `hassfest` and the HACS check.

```shell
uv run ruff check .
uv run ruff format .
uv run mypy custom_components tests
uv run pytest
```

`pytest` fails below 95% coverage.

## Mock S&P Connect server

`tests/mock_connect.py` serves the S&P Connect endpoints from in-memory state.
Tests change that state, or inject an error response, to drive each case.
When S&P Connect's response shapes change, update the mock and
`api/models.py` together.
