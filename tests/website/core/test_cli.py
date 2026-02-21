from click.testing import CliRunner

from bundle.website import cli as website_cli


def test_website_cli_exposes_site_group():
    runner = CliRunner()
    result = runner.invoke(website_cli.website, ["--help"])
    assert result.exit_code == 0
    assert "site" in result.output


def test_website_site_start_bundle_invokes_uvicorn(monkeypatch):
    captured = {}

    def fake_run(app, host, port):
        captured["host"] = host
        captured["port"] = port
        captured["title"] = app.title

    monkeypatch.setattr(website_cli.uvicorn, "run", fake_run)

    runner = CliRunner()
    result = runner.invoke(
        website_cli.website,
        ["site", "start", "bundle", "--host", "127.0.0.1", "--port", "9001"],
    )
    assert result.exit_code == 0
    assert captured["host"] == "127.0.0.1"
    assert captured["port"] == 9001
    assert captured["title"] == "Bundle Website"
