"""Series matching and chapter reconciliation logic."""
import re
from typing import List, Set, Dict, Any, Tuple, Optional
from app.models import (
    NormalizedTitle, NormalizedChapter, CanonicalChapter, ChapterSourceVersion,
    AdultContentMetadata, AdultClassification, ContentOrigin, Category,
)
from app.config import settings


# Adult classification ranking
ADULT_RANK = {
    "confirmed_adult": 3,
    "mature_non_explicit": 2,
    "general_audience": 1,
    "unknown": 0,
}

COMMON_SUFFIXES = [
    "raw", "uncensored", "decensored", "english", "colored", "colour",
    "digital", "fan colored", "fan-coloured", "official", "scanlation",
    "complete", "ongoing", "hiatus",
]

FILLER = {"the", "a", "an", "of", "and", "to", "in", "on", "no"}


def classify_mangadex(content_rating: Optional[str], origin: ContentOrigin = "manga") -> AdultContentMetadata:
    """Classify MangaDex content rating."""
    mapping = {
        "pornographic": "confirmed_adult",
        "erotica": "mature_non_explicit",
        "suggestive": "mature_non_explicit",
        "safe": "general_audience",
    }
    classification = mapping.get((content_rating or "").lower(), "unknown")
    return AdultContentMetadata(
        classification=classification,
        is_adult=classification == "confirmed_adult",
        is_explicit=classification == "confirmed_adult",
        origin=origin,
        source_provider="mangadex",
        source_classification=content_rating,
        reason=f"mangadex.contentRating={content_rating}" if content_rating else "mangadex.contentRating missing",
    )


def classify_anilist(is_adult: Optional[bool], origin: ContentOrigin = "manga") -> AdultContentMetadata:
    """Classify AniList isAdult flag."""
    classification = "confirmed_adult" if is_adult else "general_audience"
    return AdultContentMetadata(
        classification=classification,
        is_adult=is_adult or False,
        is_explicit=is_adult or False,
        origin=origin,
        source_provider="anilist",
        source_classification=f"isAdult={is_adult}",
        reason="anilist.isAdult",
    )


def classify_hentairead(origin: ContentOrigin) -> AdultContentMetadata:
    """Classify HentaiRead - always adult."""
    return AdultContentMetadata(
        classification="confirmed_adult",
        is_adult=True,
        is_explicit=True,
        origin=origin,
        source_provider="hentairead",
        source_classification="hentairead.io (adult-only catalogue)",
        reason="hentairead.io is an adult-only hentai source",
    )


def infer_origin(hints: Dict[str, Any]) -> ContentOrigin:
    """Infer content origin from tags/demographic/country."""
    tags = [t.lower() for t in (hints.get("tags") or [])]
    if "doujinshi" in tags or "doujin" in tags:
        return "doujinshi"
    if "manhwa" in tags or (hints.get("countryOfOrigin") or "").upper() == "KR":
        return "manhwa"
    if "manhua" in tags or (hints.get("countryOfOrigin") or "").upper() in ("CN", "TW", "HK"):
        return "manhua"
    if hints.get("demographic") in ("shoujo", "josei"):
        return "manhwa"
    return "manga"


def normalize_for_match(title: str) -> str:
    """Normalize title for matching: lowercase, strip diacritics, punctuation, suffixes."""
    if not title:
        return ""
    key = title.lower()
    # Strip diacritics
    key = re.sub(r'[\u0300-\u036f]', '', key)
    # Remove parenthetical/bracketed content
    key = re.sub(r'[\(\[].*?[\)\]]', '', key)
    # Strip common suffixes
    for suffix in COMMON_SUFFIXES:
        pattern = re.compile(rf'(?:[\s\-_]){re.escape(suffix)}$')
        key = pattern.sub('', key).strip()
    # Remove punctuation, collapse whitespace
    key = re.sub(r'[^a-z0-9\s]', ' ', key)
    key = re.sub(r'\s+', ' ', key).strip()
    return key


def tokens(title: str) -> Set[str]:
    return set(
        w for w in normalize_for_match(title).split()
        if len(w) > 1 and w not in FILLER
    )


def token_similarity(a: str, b: str) -> float:
    ta, tb = tokens(a), tokens(b)
    if not ta or not tb:
        return 0.0
    inter = len(ta & tb)
    return inter / (len(ta) + len(tb) - inter)


def identity_set(t: NormalizedTitle) -> Set[str]:
    s = {normalize_for_match(t.title)}
    for alt in t.alternative_titles or []:
        s.add(normalize_for_match(alt))
    return s


def overlap(a: Set[str], b: Set[str]) -> bool:
    return any(x in b for x in a)


def series_match_confidence(a: NormalizedTitle, b: NormalizedTitle) -> Tuple[float, List[str]]:
    """Compute match confidence between two titles (0..1)."""
    score = 0.0
    reasons = []
    
    # Exact identity match
    id_a, id_b = identity_set(a), identity_set(b)
    if overlap(id_a, id_b):
        score += 0.6
        reasons.append("exact title/alt-title match")
    else:
        # Token similarity
        sim = token_similarity(a.title, b.title)
        if sim >= 0.75:
            score += 0.45
            reasons.append(f"high title similarity {sim:.2f}")
        elif sim >= 0.45:
            score += 0.35
            reasons.append(f"moderate title similarity {sim:.2f}")
        elif sim >= 0.3:
            score += 0.2
            reasons.append(f"low title similarity {sim:.2f}")
        else:
            reasons.append(f"very low title similarity {sim:.2f}")
    
    # Corroborating metadata
    authors_a = {x.lower().strip() for x in (a.authors or []) if x}
    authors_b = {x.lower().strip() for x in (b.authors or []) if x}
    if authors_a and authors_b:
        if authors_a & authors_b:
            score += 0.25
            reasons.append("shared author/artist")
        else:
            score -= 0.4
            reasons.append("conflicting authors")
    
    if a.published_at and b.published_at and a.published_at[:4] == b.published_at[:4]:
        score += 0.1
        reasons.append("same release year")
    
    if a.category == b.category:
        score += 0.05
        reasons.append("same category")
    
    return max(0.0, min(1.0, score)), reasons


def are_same_series(a: NormalizedTitle, b: NormalizedTitle, threshold: float = None) -> bool:
    if threshold is None:
        threshold = settings.match_threshold
    return series_match_confidence(a, b)[0] >= threshold


def combine_adult_signals(records: List[AdultContentMetadata]) -> AdultContentMetadata:
    """Combine adult classifications from multiple providers."""
    if not records:
        return AdultContentMetadata(
            classification="unknown", is_adult=False, is_explicit=False,
            origin="other", source_provider="aggregate", reason="no provider records"
        )
    
    best = max(records, key=lambda r: ADULT_RANK.get(r.classification, 0))
    origin = next((r.origin for r in records if r.origin != "other"), best.origin)
    
    return AdultContentMetadata(
        classification=best.classification,
        is_adult=best.classification == "confirmed_adult",
        is_explicit=best.classification == "confirmed_adult",
        origin=origin,
        source_provider="+".join(r.source_provider for r in records),
        reason=f"combined from {len(records)} record(s); strongest={best.classification}",
    )


def group_into_canonical(titles: List[NormalizedTitle]) -> List["CanonicalSeries"]:
    """Group titles into canonical series using confident matches."""
    eligible = [t for t in titles if is_eligible(t.adult.classification)]
    used = [False] * len(eligible)
    series = []
    
    for i, title in enumerate(eligible):
        if used[i]:
            continue
        members = [title]
        used[i] = True
        
        for j in range(i + 1, len(eligible)):
            if used[j]:
                continue
            if any(are_same_series(m, eligible[j]) for m in members):
                members.append(eligible[j])
                used[j] = True
        
        primary = members[0]
        adult = combine_adult_signals([m.adult for m in members])
        
        provider_mappings = [
            {
                "provider_id": m.provider,
                "provider_series_id": m.provider_id,
                "source_url": m.provider_url,
                "capabilities": {
                    "search": True,
                    "metadata": True,
                    "chapters": m.readable,
                    "reader": m.readable,
                }
            }
            for m in members
        ]
        
        series.append({
            "id": f"series:{normalize_for_match(primary.title).replace(' ', '-')[:80]}",
            "slug": normalize_for_match(primary.title).replace(' ', '-')[:80],
            "title": primary.title,
            "alternative_titles": list((set().union(*[m.alternative_titles for m in members]) - {primary.title})),
            "category": primary.category,
            "origin": adult.origin,
            "is_adult": adult.is_adult,
            "adult": adult,
            "description": next((m.description for m in members if m.description), None),
            "cover_url": next((m.cover_image for m in members if m.cover_image), None),
            "genres": list(set().union(*[m.genres for m in members])),
            "tags": list(set().union(*[m.tags for m in members])),
            "authors": list(set().union(*[m.authors for m in members])),
            "artists": list(set().union(*[m.artists for m in members])),
            "status": next((m.status for m in members if m.status), None),
            "original_language": next((m.original_language for m in members if m.original_language), None),
            "available_languages": list(set().union(*[[m.language] for m in members if m.language])),
            "release_year": next((int(m.published_at[:4]) for m in members if m.published_at and m.published_at[:4].isdigit()), None),
            "rating": next((m.rating for m in members if m.rating is not None), None),
            "popularity": next((m.popularity for m in members if m.popularity is not None), None),
            "provider_mappings": provider_mappings,
            "created_at": "2024-01-01T00:00:00Z",
            "updated_at": None,
        })
    
    return series


def is_eligible(classification: AdultClassification) -> bool:
    if classification == "confirmed_adult":
        return settings.allow_confirmed_adult
    if classification == "mature_non_explicit":
        return settings.allow_mature
    if classification == "unknown":
        return settings.allow_unknown
    return False


# Chapter reconciliation
def parse_chapter_label(label: str) -> Dict[str, Any]:
    raw = (label or "").strip()
    lower = raw.lower()
    
    vol_match = re.search(r'\b(?:vol|volume)\.?\s*(\d+(?:\.\d+)?)', lower)
    volume = vol_match.group(1) if vol_match else None
    
    num_match = re.search(r'\b(?:chapter|ch)\.?\s*(\d+(?:\.\d+)?)', lower) or \
                re.match(r'^\s*(\d+(?:\.\d+)?)\s*$', raw)
    number = float(num_match.group(1)) if num_match else None
    
    ctype = "main"
    if number is not None:
        if "prologue" in lower: ctype = "prologue"
        elif "epilogue" in lower: ctype = "epilogue"
        elif "side" in lower and "story" in lower: ctype = "side_story"
        elif any(w in lower for w in ["extra", "bonus", "special"]): ctype = "extra"
        elif "oneshot" in lower: ctype = "oneshot"
    else:
        if "prologue" in lower: ctype = "prologue"
        elif "epilogue" in lower: ctype = "epilogue"
        elif "side" in lower and "story" in lower: ctype = "side_story"
        elif any(w in lower for w in ["extra", "bonus", "special"]): ctype = "extra"
        elif "oneshot" in lower: ctype = "oneshot"
        else: ctype = "unknown"
    
    return {"number": number, "type": ctype, "volume": volume}


def reconcile_chapters(series_id: str, inputs: List[Dict[str, Any]]) -> List[CanonicalChapter]:
    """Merge chapter records from multiple providers into canonical chapters."""
    buckets = {}
    
    for c in inputs:
        lang = c.get("language") or "und"
        parsed = parse_chapter_label(c.get("label", ""))
        number = parsed["number"]
        volume = c.get("volume_number") or parsed["volume"]
        
        if number is not None:
            key = f"{lang}::num::{number}"
        else:
            norm = re.sub(r'[^a-z0-9]+', ' ', c.get("label", "").lower()).strip()
            key = f"{lang}::{parsed['type']}::{norm}" if norm else f"{lang}::{parsed['type']}::idx{len(buckets)}"
        
        version = ChapterSourceVersion(
            provider_id=c["provider_id"],
            provider_series_id=c["provider_series_id"],
            provider_chapter_id=c["provider_chapter_id"],
            chapter_number=str(number) if number else None,
            volume_number=volume,
            title=c.get("title"),
            language=lang,
            release_group=c.get("release_group"),
            source_url=c.get("source_url"),
            page_access_capability=c.get("page_access_capability", "metadata_only"),
            page_count=c.get("page_count"),
            published_at=c.get("published_at"),
        )
        
        if key in buckets:
            buckets[key]["versions"].append(version)
        else:
            buckets[key] = {
                "key": key, "language": lang, "number": number,
                "type": parsed["type"], "label": c.get("label", ""),
                "versions": [version], "input_index": len(buckets),
            }
    
    # Sort keys
    items = list(buckets.values())
    nums = [i["number"] for i in items if i["number"] is not None]
    min_n = min(nums) if nums else 0
    max_n = max(nums) if nums else 0
    
    TIER = {"prologue": -1, "main": 0, "special": 0, "epilogue": 1, "side_story": 2, "extra": 3, "oneshot": 4, "unknown": 5}
    
    sort_keys = []
    for item in items:
        if item["number"] is not None:
            sort_keys.append(item["number"])
        else:
            tier = TIER.get(item["type"], 5)
            if tier < 0:
                sort_keys.append(min_n - 1 + item["input_index"] * 0.0001)
            else:
                sort_keys.append(max_n + 1 + tier + item["input_index"] * 0.0001)
    
    chapters = []
    for item, sk in zip(items, sort_keys):
        chapters.append(CanonicalChapter(
            id=f"{series_id}:ch:{item['key']}",
            series_id=series_id,
            chapter_number=item["number"],
            label=item["label"],
            volume_number=item["versions"][0].volume_number,
            title=next((v.title for v in item["versions"] if v.title), None),
            language=item["language"],
            chapter_type=item["type"],
            source_versions=item["versions"],
            sort_key=sk,
        ))
    
    chapters.sort(key=lambda c: (c.sort_key, c.label, c.id))
    return chapters