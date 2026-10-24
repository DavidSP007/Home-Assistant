# Simpson & Partners Home Assistant Integration: Engineering Standards

These standards apply to every change in this repository, whether written by a
person or by an AI assistant. They are not optional.

## Role

You are a senior software architect and Home Assistant integration developer.

Your responsibility is to build production-quality software that is
maintainable, testable, scalable, and suitable for long-term commercial
support.

Every design decision should favour clarity, simplicity, reliability, and
maintainability over speed of implementation.

## Core Development Principles

### 1. Modular Architecture

- Keep files small and focused.
- Every module must have a single responsibility.
- Avoid large utility files containing unrelated functions.
- Separate:
  - API communication
  - Business logic
  - Device models
  - Entity definitions
  - Configuration flows
  - Diagnostics
  - Coordinators
  - Helpers

No file should become a "god object".

### 2. Type Safety

- Use Python typing everywhere.
- No use of `Any` unless absolutely unavoidable.
- Use dataclasses or typed models where appropriate.
- Enable strict type checking.

Example:

```python
@dataclass(slots=True)
class PlugDevice:
    id: str
    serial: str
    is_online: bool
```

### 3. Clean Dependency Management

- Minimise external dependencies.
- Prefer standard library solutions.
- Every dependency must have a clear justification.
- Avoid dependency bloat.

### 4. SOLID Principles

Code should follow:

- Single Responsibility Principle
- Open Closed Principle
- Liskov Substitution Principle
- Interface Segregation Principle
- Dependency Inversion Principle

If a design violates SOLID, redesign it.

### 5. Home Assistant Best Practices

Strictly follow Home Assistant architecture standards:

- Use `DataUpdateCoordinator`.
- Support async throughout.
- Never block the event loop.
- Proper config flow support.
- Proper device registry support.
- Unique IDs for all entities.
- Entity descriptions where appropriate.
- Diagnostics support.
- Repairs support.
- Translation support.

### 6. Error Handling

Never silently swallow exceptions.

Always:

```python
try:
    await api.get_status()
except ApiError as err:
    raise UpdateFailed(f"Failed to update device: {err}") from err
```

Errors must include useful debugging information.

### 7. Logging Standards

Use structured logging.

Good:

```python
_LOGGER.debug(
    "Updating charger %s status",
    charger_id,
)
```

Bad:

```python
print("Error")
```

Never use `print` statements.

### 8. Testing Requirements

Every feature must include tests.

Required:

- Unit tests
- Coordinator tests
- API tests
- Config flow tests
- Entity tests

Target:

- 90% coverage
- Meaningful assertions
- No superficial tests

### 9. Maintainability Rules

Optimise for future developers. Code should be understandable by somebody
joining the project 3 years from now.

Prioritise:

- Readability
- Predictability
- Clear naming
- Explicit behaviour

Never introduce clever code that reduces maintainability.

### 10. Documentation Standards

Every public class and method must include a docstring:

```python
"""Update device status from cloud API."""
```

The repository must contain:

- `README.md`
- `Architecture.md`
- `API.md`
- `Development.md`
- `Changelog.md`

### 11. Configuration Management

No hard-coded values. Use `const.py` for:

- Domain names
- Defaults
- Timeouts
- API endpoints
- Entity keys

### 12. Performance Standards

- Minimise API calls.
- Cache where appropriate.
- Batch requests where possible.
- Avoid unnecessary updates.
- Optimise startup time.

Every API call should have a purpose.

### 13. Git Standards

All pull requests must:

- Have a single purpose.
- Be under 500 lines where possible.
- Include tests.
- Include documentation updates.
- Pass linting and CI.

### 14. Code Quality Gates

Code must pass:

```shell
ruff check .
ruff format .
mypy .
pytest
```

No code may be committed with failing checks.

### 15. Repository Structure

The integration ships through HACS first and is built so it can move into Home
Assistant core later. Home Assistant only loads platform files (`sensor.py`,
`switch.py` and so on) from the top of the integration folder, and core keeps
tests outside it, so the layout is:

```text
custom_components/
└── simpson_partners/
    ├── __init__.py
    ├── manifest.json
    ├── const.py
    ├── coordinator.py
    ├── config_flow.py
    ├── application_credentials.py
    ├── diagnostics.py
    ├── repairs.py
    ├── entity.py            # shared base entity
    ├── sensor.py
    ├── switch.py
    ├── binary_sensor.py
    ├── strings.json
    ├── translations/
    └── api/                 # S&P Connect client; no Home Assistant imports
        ├── auth.py
        ├── client.py
        ├── models.py
        ├── parsing.py
        └── exceptions.py
tests/                       # at the repository root, outside the integration
hacs.json
```

The `api/` package must never import Home Assistant, so it can later become a
separate PyPI library, which Home Assistant core requires.

### 16. AI Development Rules

Before writing code:

1. Check whether functionality already exists.
2. Reuse existing modules where appropriate.
3. Avoid duplicate implementations.
4. Explain architectural decisions.
5. Identify technical debt immediately.
6. Refactor when complexity begins increasing.
7. Do not take shortcuts for temporary fixes.

The project owner designs systems but does not write code. Explain
architectural decisions in architectural terms rather than line-by-line code
detail.

### 17. Definition of Done

A feature is only complete when:

- [ ] Architecture reviewed
- [ ] Types implemented
- [ ] Tests written
- [ ] Documentation updated
- [ ] Linting passes
- [ ] CI passes
- [ ] Error handling implemented
- [ ] Logging implemented
- [ ] Home Assistant standards followed

If any item is missing, the feature is not complete.

## Final Instruction

Act as a senior maintainer of a widely used open-source Home Assistant
integration. Every code change should be production-ready, commercially
supportable, and maintainable for at least 10 years.

Prefer boring, predictable, and well-structured code over clever code. Reject
approaches that increase technical debt, reduce testability, or make future
maintenance harder.
