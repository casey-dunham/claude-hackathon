# Frontend Contract Tests

Automated tests live in:
- `testing/frontendtests/test_frontend_contract.py`

These tests verify frontend-facing assumptions from `API_CONTRACT.md`:
- Health check for app bootstrap
- Log response shape for table rendering
- Dashboard history order/length for line charts
- Chat response behavior for non-log and log messages

Run:

```bash
python3 -m pytest -q testing/frontendtests/test_frontend_contract.py
```
