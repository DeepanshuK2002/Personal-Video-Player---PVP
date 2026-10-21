import pytest
import sys
import os

# Add the app directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'app'))

from app.core.matching import (
    normalize_for_match, token_similarity, series_match_confidence,
    are_same_series, combine_adult_signals, group_into_canonical,
    is_eligible, parse_chapter_label, reconcile_chapters,
)
from app.models import NormalizedTitle, AdultContentMetadata, AdultClassification, ContentOrigin, Category


def test_normalize_for_match():
    assert normalize_for_match("  The GHOST!  ") == "the ghost"
    assert normalize_for_match("Secret Class Raw") == "secret class"
    assert normalize_for_match("Title [Uncensored]") == "title"
    assert normalize_for_match("Title (Decensored)") == "title"
    assert normalize_for_match("Title - English") == "title"
    assert normalize_for_match("Title (Raw)") == "title"


def test_token_similarity():
    assert token_similarity("Chainsaw Man", "Chainsaw Man") == 1.0
    assert token_similarity("Chainsaw Man", "Cooking Papa") < 0.3


def test_series_match_confidence():
    a = NormalizedTitle(
        id="p1:title", provider="p1", provider_id="id1", slug="s1", title="Blue Period",
        alternative_titles=[], description=None, category="manga", is_adult=True,
        cover_image=None, rating=None, popularity=None, genres=[], tags=[],
        artists=[], authors=["Author A"], language="en", status=None,
        updated_at=None, published_at="2017", provider_url=None, readable=False,
        adult=AdultContentMetadata(classification="confirmed_adult", is_adult=True,
            is_explicit=True, origin="manga", source_provider="test", reason="test"),
    )
    b = NormalizedTitle(
        id="p2:title", provider="p2", provider_id="id2", slug="s2", title="Blue Period",
        alternative_titles=[], description=None, category="manga", is_adult=True,
        cover_image=None, rating=None, popularity=None, genres=[], tags=[],
        artists=[], authors=["Author A"], language="en", status=None,
        updated_at=None, published_at="2017", provider_url=None, readable=False,
        adult=AdultContentMetadata(classification="confirmed_adult", is_adult=True,
            is_explicit=True, origin="manga", source_provider="test", reason="test"),
    )
    score, reasons = series_match_confidence(a, b)
    assert score >= 0.55
    assert "exact title/alt-title match" in reasons


def test_are_same_series():
    a = NormalizedTitle(
        id="p1:t", provider="p1", provider_id="1", slug="s1", title="Same Title",
        alternative_titles=[], description=None, category="manga", is_adult=True,
        cover_image=None, rating=None, popularity=None, genres=[], tags=[],
        artists=[], authors=[], language="en", status=None,
        updated_at=None, published_at=None, provider_url=None, readable=False,
        adult=AdultContentMetadata(classification="confirmed_adult", is_adult=True,
            is_explicit=True, origin="manga", source_provider="test", reason="test"),
    )
    b = NormalizedTitle(
        id="p2:t", provider="p2", provider_id="2", slug="s2", title="Same Title",
        alternative_titles=[], description=None, category="manga", is_adult=True,
        cover_image=None, rating=None, popularity=None, genres=[], tags=[],
        artists=[], authors=[], language="en", status=None,
        updated_at=None, published_at=None, provider_url=None, readable=False,
        adult=AdultContentMetadata(classification="confirmed_adult", is_adult=True,
            is_explicit=True, origin="manga", source_provider="test", reason="test"),
    )
    assert are_same_series(a, b) == True


def test_combine_adult_signals():
    sig = lambda c: AdultContentMetadata(
        classification=c, is_adult=c=="confirmed_adult", is_explicit=c=="confirmed_adult",
        origin="manga", source_provider="test", reason="test"
    )
    out = combine_adult_signals([sig("general_audience"), sig("confirmed_adult")])
    assert out.classification == "confirmed_adult"
    assert out.is_adult == True


def test_is_eligible():
    from app.config import settings
    # The test uses default settings
    assert is_eligible("confirmed_adult") == True
    assert is_eligible("mature_non_explicit") == True
    assert is_eligible("general_audience") == False
    assert is_eligible("unknown") == False


def test_parse_chapter_label():
    assert parse_chapter_label("Chapter 12") == {"number": 12.0, "type": "main", "volume": None}
    assert parse_chapter_label("Ch. 10.5") == {"number": 10.5, "type": "main", "volume": None}
    assert parse_chapter_label("Vol. 3 Chapter 7") == {"number": 7.0, "type": "main", "volume": "3"}
    assert parse_chapter_label("Prologue") == {"number": None, "type": "prologue", "volume": None}
    assert parse_chapter_label("Epilogue") == {"number": None, "type": "epilogue", "volume": None}
    assert parse_chapter_label("Oneshot") == {"number": None, "type": "oneshot", "volume": None}


def test_reconcile_chapters():
    inputs = [
        {
            "provider_id": "a", "provider_series_id": "s1", "provider_chapter_id": "ch1",
            "label": "Chapter 1", "title": None, "volume_number": None,
            "language": "en", "release_group": None, "source_url": None,
            "page_access_capability": "available", "page_count": 20, "published_at": None,
        },
        {
            "provider_id": "b", "provider_series_id": "s2", "provider_chapter_id": "ch1",
            "label": "Chapter 1", "title": None, "volume_number": None,
            "language": "en", "release_group": None, "source_url": None,
            "page_access_capability": "available", "page_count": 18, "published_at": None,
        },
    ]
    out = reconcile_chapters("series-1", inputs)
    assert len(out) == 1
    assert len(out[0].source_versions) == 2
    assert {v.provider_id for v in out[0].source_versions} == {"a", "b"}


def test_group_into_canonical():
    titles = [
        NormalizedTitle(
            id="p1:t", provider="p1", provider_id="1", slug="s1", title="Shared Work",
            alternative_titles=[], description=None, category="manga", is_adult=True,
            cover_image=None, rating=None, popularity=None, genres=[], tags=[],
            artists=[], authors=["Author A"], language="en", status=None,
            updated_at=None, published_at="2020", provider_url=None, readable=False,
            adult=AdultContentMetadata(classification="confirmed_adult", is_adult=True,
                is_explicit=True, origin="manga", source_provider="p1", reason="test"),
        ),
        NormalizedTitle(
            id="p2:t", provider="p2", provider_id="2", slug="s2", title="Shared Work",
            alternative_titles=[], description=None, category="manga", is_adult=True,
            cover_image=None, rating=None, popularity=None, genres=[], tags=[],
            artists=[], authors=["Author A"], language="en", status=None,
            updated_at=None, published_at="2020", provider_url=None, readable=False,
            adult=AdultContentMetadata(classification="confirmed_adult", is_adult=True,
                is_explicit=True, origin="manga", source_provider="p2", reason="test"),
        ),
    ]
    series = group_into_canonical(titles)
    assert len(series) == 1
    assert len(series[0]["provider_mappings"]) == 2