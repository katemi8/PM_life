"""Сопоставление компании с текстом био (без раздувания alias-листов)."""
from __future__ import annotations

import re
from dataclasses import dataclass
from enum import IntEnum


class MatchTier(IntEnum):
    NONE = 0
    WEAK_SUBSTR = 1
    TOKEN = 2
    SLUG_IN_USERNAME = 3
    EXACT_ALIAS = 4


@dataclass
class CompanyProfile:
    raw: str
    key: str
    tokens: list[str]
    ambiguous: bool


def company_key(name: str) -> str:
    k = re.sub(r"[^a-z0-9а-яё]+", "-", name.casefold().strip())
    return k.strip("-") or "unknown"


COMPANY_ALIASES: dict[str, list[str]] = {
    "домклик": ["domclick", "domclick.ru"],
    "domclick": ["домклик"],
    "аэрофлот": ["aeroflot", "aflt", "афлт", "aflt-systems"],
    "aeroflot": ["аэрофлот", "aflt"],
}


def company_terms(company: str) -> list[str]:
    c = company.casefold().strip()
    terms = [c]
    for key, extras in COMPANY_ALIASES.items():
        if c == key or key in c.replace(" ", ""):
            terms.extend(extras)
    return list(dict.fromkeys(terms))


def build_company_profile(company: str, *, has_seed: bool = False, has_network: bool = False) -> CompanyProfile:
    key = company_key(company)
    tokens = [t for t in re.split(r"[\s\-]+", company.casefold().strip()) if t]
    ambiguous = len(tokens) <= 1 and len(key.replace("-", "")) <= 6 and not has_seed and not has_network
    return CompanyProfile(raw=company, key=key, tokens=tokens, ambiguous=ambiguous)


def _word_in_text(term: str, text: str) -> bool:
    if len(term) <= 2:
        return False
    return re.search(rf"(?<![a-zа-яё0-9]){re.escape(term)}(?![a-zа-яё0-9])", text) is not None


def match_company(text: str, username: str, profile: CompanyProfile) -> MatchTier:
    t = text.casefold()
    un = username.casefold()
    slug = re.sub(r"[^a-z0-9]+", "", profile.key)

    for term in company_terms(profile.raw):
        if term and _word_in_text(term, t):
            if term in COMPANY_ALIASES or term in {a for xs in COMPANY_ALIASES.values() for a in xs}:
                return MatchTier.EXACT_ALIAS
            return MatchTier.TOKEN

    for term in company_terms(profile.raw):
        if len(term) >= 4 and term in t and not profile.ambiguous:
            return MatchTier.WEAK_SUBSTR

    if slug and len(slug) > 4 and slug in un:
        return MatchTier.SLUG_IN_USERNAME

    if profile.ambiguous:
        return MatchTier.NONE

    for part in profile.tokens:
        if len(part) > 3 and part in t:
            return MatchTier.WEAK_SUBSTR
    if profile.key.replace("-", "") in un:
        return MatchTier.SLUG_IN_USERNAME

    return MatchTier.NONE