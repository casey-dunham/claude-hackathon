# End-to-End Flow Tests

Automated tests live in:
- `testing/end2endtests/test_end_to_end_flows.py`

These tests cover cross-endpoint user journeys from the API contract:
- Manual food entry lifecycle (`POST /api/log` -> `GET /api/log` -> `GET /api/dashboard/today` -> `DELETE /api/log/{id}`)
- Chat logging flow (`POST /api/chat` -> `GET /api/log` -> `GET /api/chat/history`)

Both tests clean up created food entries so they can run repeatedly.

Run:

```bash
python3 -m pytest -q testing/end2endtests/test_end_to_end_flows.py
```
