import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from graphlens_agent.extraction import (
    LocalCVExtractionProvider,
    LocalCVNotImplementedError,
    MockScreenshotExtractionProvider,
    ProviderConfigurationError,
    get_screenshot_extraction_provider,
)


def test_provider_selection_defaults_to_mock(monkeypatch):
    monkeypatch.delenv("GRAPH_EXTRACTION_PROVIDER", raising=False)

    provider = get_screenshot_extraction_provider()

    assert isinstance(provider, MockScreenshotExtractionProvider)


def test_provider_selection_supports_local_cv(monkeypatch):
    monkeypatch.setenv("GRAPH_EXTRACTION_PROVIDER", "local_cv")

    provider = get_screenshot_extraction_provider()

    assert isinstance(provider, LocalCVExtractionProvider)


def test_invalid_provider_name_returns_clear_error(monkeypatch):
    monkeypatch.setenv("GRAPH_EXTRACTION_PROVIDER", "bad-provider")

    with pytest.raises(ProviderConfigurationError) as error:
        get_screenshot_extraction_provider()

    assert "Unsupported GRAPH_EXTRACTION_PROVIDER" in str(error.value)
    assert "mock, local_cv" in str(error.value)


def test_mock_provider_adds_mock_warning():
    provider = MockScreenshotExtractionProvider()

    document = provider.extract(
        filename="graph.jpg",
        content_type="image/jpeg",
        content=b"fake image bytes",
    )

    assert any("Mock extraction result" in warning for warning in document.warnings)


def test_local_cv_provider_is_planned_not_implemented():
    provider = LocalCVExtractionProvider()

    with pytest.raises(LocalCVNotImplementedError) as error:
        provider.extract(
            filename="graph.png",
            content_type="image/png",
            content=b"fake image bytes",
        )

    assert "Local OCR/OpenCV screenshot extraction is planned but not implemented yet" in str(error.value)
