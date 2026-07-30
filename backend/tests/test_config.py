"""Configuration guards.

The signing key is the whole of the auth story, so the settings object refuses
to build a production environment around a placeholder.
"""

import pytest

from app.core.config import (
    MIN_SECRET_KEY_LENGTH,
    PLACEHOLDER_SECRET_KEYS,
    Settings,
)

REAL_KEY = "j4Zq8x0nLpV2wS7yB1cR6tE9uH3kM5aD8fG0iJ2lN4oQ6sU8w"


def _settings(**overrides) -> Settings:
    """Build settings without picking up a developer's local .env file."""
    return Settings(_env_file=None, **overrides)


def test_development_tolerates_a_placeholder_key():
    settings = _settings(
        ENVIRONMENT="development",
        SECRET_KEY="your-secret-key-change-in-production",
    )
    assert settings.is_production is False
    assert settings.SECRET_KEY in PLACEHOLDER_SECRET_KEYS


@pytest.mark.parametrize("placeholder", sorted(PLACEHOLDER_SECRET_KEYS))
def test_production_rejects_placeholder_keys(placeholder):
    with pytest.raises(ValueError, match="placeholder"):
        _settings(ENVIRONMENT="production", SECRET_KEY=placeholder)


def test_production_rejects_short_keys():
    with pytest.raises(ValueError, match="at least"):
        _settings(ENVIRONMENT="production", SECRET_KEY="a" * (MIN_SECRET_KEY_LENGTH - 1))


def test_production_accepts_a_real_key():
    settings = _settings(ENVIRONMENT="production", SECRET_KEY=REAL_KEY)
    assert settings.is_production is True
    assert settings.SECRET_KEY == REAL_KEY


def test_environment_check_ignores_case_and_padding():
    assert _settings(ENVIRONMENT="  Production ", SECRET_KEY=REAL_KEY).is_production is True
    assert _settings(ENVIRONMENT="staging", SECRET_KEY=REAL_KEY).is_production is False


def test_cors_origins_accepts_a_comma_separated_string():
    settings = _settings(CORS_ORIGINS="https://a.example, https://b.example")
    assert settings.cors_origins == ["https://a.example", "https://b.example"]


def test_cors_origins_accepts_a_json_list():
    settings = _settings(CORS_ORIGINS='["https://a.example", "https://b.example"]')
    assert settings.cors_origins == ["https://a.example", "https://b.example"]


def test_cors_origins_accepts_a_real_list():
    settings = _settings(CORS_ORIGINS=["https://a.example", "https://b.example"])
    assert settings.cors_origins == ["https://a.example", "https://b.example"]


def test_cors_origins_ignores_blanks_and_whitespace():
    assert _settings(CORS_ORIGINS="  ").cors_origins == []
    assert _settings(CORS_ORIGINS="https://a.example,,  ").cors_origins == ["https://a.example"]


def test_cors_origins_falls_back_when_the_json_is_malformed():
    """A bracketed but unparseable value degrades to the comma parser."""
    assert _settings(CORS_ORIGINS="[not-json").cors_origins == ["[not-json"]


def test_cors_origins_defaults_to_the_local_dev_servers():
    assert _settings().cors_origins == [
        "http://localhost:5173",
        "http://localhost:3000",
    ]


@pytest.mark.parametrize(
    "raw",
    [
        "http://localhost:5173,http://localhost:3000",  # .env.example / docker-compose
        '["http://localhost:5173","http://localhost:3000"]',
    ],
)
def test_cors_origins_parses_from_a_real_environment_variable(monkeypatch, raw):
    """The env source must not choke before the parser runs (regression)."""
    monkeypatch.setenv("CORS_ORIGINS", raw)
    settings = Settings(_env_file=None)
    assert settings.cors_origins == [
        "http://localhost:5173",
        "http://localhost:3000",
    ]


def test_stripe_disabled_without_a_secret_key():
    assert _settings().stripe_enabled is False
    assert _settings(STRIPE_SECRET_KEY="sk_test_123").stripe_enabled is True
