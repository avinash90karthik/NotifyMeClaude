"""pytest config for the paper package."""

def pytest_configure(config):
    config.addinivalue_line(
        "markers",
        "online: test requires network access (yfinance). "
        "Skip with `pytest -m 'not online'`.",
    )
