# End-to-end tests

The one place the whole platform is wired together. Everything else is tested per service
(a service never imports another — hard rule 1); these tests deliberately live *outside*
`services/` so they may import every service and drive the real pipeline.

`test_pipeline.py` runs a Brain sync all the way through:

```
connector-brain sync -> outbox -> RelayWorker -> Kafka
    -> catalog / offer / price-history / matching
    -> matching auto-link -> outbox -> RelayWorker -> Kafka -> catalog (canonical link)
```

then asserts, through each service's own repository, that the data arrived.

## Running

Needs Docker (spins up one Postgres + one Kafka via testcontainers, a database per service):

```
uv run pytest -m integration tests/e2e
```

Marked `@pytest.mark.integration`, so it is excluded from the fast unit run and the coverage
gate, and runs in CI's integration job.
