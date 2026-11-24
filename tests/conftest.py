import os, tempfile, pytest
@pytest.fixture(autouse=True)
def isolated_db(monkeypatch, tmp_path):
    monkeypatch.setenv("LOYALTY_DB_PATH", str(tmp_path / "test.db"))
    # Modules capture DB_PATH at import, so patch the module-level path.
    import app.config, app.db, app.campaigns
    app.config.DB_PATH = str(tmp_path / "test.db")
    app.db.DB_PATH = str(tmp_path / "test.db")
    app.db.init_db()
    from app.db import connect
    with connect() as c:
        c.execute("INSERT INTO partners VALUES('hotelco','Test Hotel',2.0)")
        c.execute("INSERT INTO members VALUES('M0001','Test Member')")
