"""Config loading: YAML files + environment overrides."""

from reducto.config import apply_env, load_config
from reducto.models import AppConfig


def test_apply_env_model_override(monkeypatch):
    monkeypatch.setenv("REDUCTO_MODEL", "gpt-test")
    assert apply_env(AppConfig()).model == "gpt-test"


def test_apply_env_prefer_local_false(monkeypatch):
    monkeypatch.setenv("REDUCTO_PREFER_LOCAL", "false")
    assert apply_env(AppConfig()).prefer_local is False


def test_apply_env_verbose(monkeypatch):
    monkeypatch.setenv("REDUCTO_VERBOSE", "1")
    assert apply_env(AppConfig()).verbose is True


def test_apply_env_noop_when_unset(monkeypatch):
    for key in ("REDUCTO_MODEL", "REDUCTO_PREFER_LOCAL", "REDUCTO_VERBOSE"):
        monkeypatch.delenv(key, raising=False)
    cfg = apply_env(AppConfig())
    assert cfg.prefer_local is True
    assert cfg.verbose is False
    assert cfg.model == ""


def test_load_config_yaml(tmp_path, monkeypatch):
    (tmp_path / ".reducto.yaml").write_text(
        "verbose: true\ncomplexity_thresholds:\n  cyclomatic_complexity: 3\n"
    )
    monkeypatch.chdir(tmp_path)
    cfg = load_config()
    assert cfg.verbose is True
    assert cfg.complexity_thresholds.cyclomatic_complexity == 3


def test_load_config_explicit_path(tmp_path):
    p = tmp_path / "custom.yaml"
    p.write_text("model: zzz\n")
    assert load_config(str(p)).model == "zzz"


def test_load_config_missing_returns_defaults(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("HOME", str(tmp_path))
    assert load_config().model == AppConfig().model
