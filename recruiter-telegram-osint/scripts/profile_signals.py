"""Сигналы из био t.me и минимальные спам-приоритеты (не бесконечный deny)."""
from __future__ import annotations

import re

from company_match import MatchTier, build_company_profile, company_terms, match_company

# Агрегаторы / спам — редкий жёсткий список (источники сканирования, не контакты).
# Подтверждённый скам / фишинг под бренд (не сниппет DDG).
SCAM_USERNAMES = frozenset(
    {
        "hr_departamentc",
    }
)

SPAM_USERNAMES = frozenset(
    {
        "work4writers",
        "writeforwork",
        "hrhubvacancy",
        "hrhubvacancy300",
        "hrhubjunior",
        "hrhublibrary",
        "hrhubresume",
        "jobs_for_products",
        "forproducts",
        "otzuvw4w",
        "vacancy_hrhub",
        "essaywork",
    }
)

HR_TERMS = (
    "рекрут",
    "recruit",
    " hr",
    "hr ",
    "кадр",
    "talent",
    "hiring",
    "ваканс",
    "подбор",
    "резюме",
    "resume",
    "career",
    "карьер",
)

INDUSTRY_MISMATCH = (
    "гранит",
    "памятник",
    "плитка",
    "брусчат",
    "оптом",
    "поставщик",
    "essay",
    "курсов",
    "диплом",
)

AGGREGATOR_BIO = (
    "размещение вакансий",
    "размещение рекламы",
    "вакансии для",
    "канал ваканс",
    "чужие резюме",
)

SPAM_BIO = (
    "essay",
    "эссе",
    "курсовых",
    "дипломн",
    "напишем",
)

SCAM_BIO = (
    "1000$",
    "1000 $",
    "$1000",
    "1 000 $",
    "1000 usd",
    "заработ",
    "без опыта",
    "лёгк",
    "легк",
)

TG_PLATFORM = (
    "official telegram on telegram",
    "much recursion",
    "very telegram",
)

PLATFORM_USER = frozenset(
    {"telegram", "boost", "premium", "telegramtips", "contest", "spambot", "botfather"}
)

GENERIC_USERNAMES = frozenset(
    {
        "junior",
        "senior",
        "admin",
        "support",
        "help",
        "info",
        "channel",
        "official",
    }
)


def bio_blob(v: dict) -> str:
    return f"{v.get('title', '')} {v.get('description', '')}".casefold()


def has_person_title(v: dict) -> bool:
    title = (v.get("display_name") or v.get("title") or "").strip()
    return len(title) > 2 and title not in ("—", "-") and (
        " " in title or len(title) > 12
    )


def detect_channel(v: dict) -> bool:
    if v.get("is_channel"):
        return True
    blob = bio_blob(v)
    if "подписчик" in blob and "канал" in blob:
        return True
    if "channel" in blob and not has_person_title(v):
        return True
    if any(x in blob for x in ("официальный канал", "наш канал", "подписывайтесь")):
        return not has_person_title(v)
    return False


def is_scam_username(username: str) -> bool:
    return username.casefold() in SCAM_USERNAMES


def is_spam_username(username: str) -> bool:
    if is_scam_username(username):
        return True
    return username.casefold() in SPAM_USERNAMES


def is_platform_account(v: dict) -> bool:
    un = v["username"].casefold()
    if un in PLATFORM_USER:
        return True
    return any(m in bio_blob(v) for m in TG_PLATFORM)


def hr_intent(blob: str) -> bool:
    return any(h in blob for h in HR_TERMS)


# Сильный сигнал другого работодателя в био (не раздуваем deny-ники).
BIO_EMPLOYER_MARKERS: tuple[tuple[str, ...], ...] = (
    ("самокат", "samokat", "samokat.tech"),
    ("ozon", "озон"),
    ("wildberries", "вайлдберриз"),
    ("яндекс", "yandex"),
    ("тинькофф", "tinkoff", "т-банк", "tinkoff"),
    ("avito", "авито"),
    ("сбер", "sber", "сбермаркет"),
    ("kaspersky", "касперск"),
    ("lamoda", "ламода"),
    ("kion", "кион"),
)


def bio_claims_other_employer(blob: str, company: str) -> bool:
    profile = build_company_profile(company)
    if int(match_company(blob, "", profile)) >= int(MatchTier.TOKEN):
        return False
    qt = " ".join(company_terms(company))
    for group in BIO_EMPLOYER_MARKERS:
        if not any(m in blob for m in group):
            continue
        if any(m in qt for m in group):
            continue
        return True
    return False


def bio_adjustments(v: dict, *, tier_value: int, ambiguous: bool) -> tuple[int, list[str]]:
    """Δ к prior; tier_value — MatchTier."""
    blob = bio_blob(v)
    un = v["username"].casefold()
    notes: list[str] = []
    delta = 0

    if is_scam_username(v["username"]):
        notes.append("confirmed_scam")
        return -150, notes

    if any(x in blob for x in SCAM_BIO):
        delta -= 90
        notes.append("scam_bio_pattern")

    if is_spam_username(v["username"]):
        notes.append("spam_aggregator")
        return -120, notes

    if detect_channel(v):
        delta -= 45
        notes.append("channel_bio")

    if any(x in blob for x in AGGREGATOR_BIO):
        delta -= 70
        notes.append("vacancy_aggregator")

    if any(x in blob for x in SPAM_BIO):
        delta -= 80
        notes.append("spam_bio")

    if any(x in blob for x in INDUSTRY_MISMATCH) and not hr_intent(blob):
        delta -= 35
        notes.append("unrelated_industry")

    if tier_value >= 4:
        delta += 28
    elif tier_value == 3:
        delta += 12
    elif tier_value == 2:
        delta += 22
    elif tier_value == 1 and not ambiguous:
        delta += 0
    elif tier_value == 1 and ambiguous:
        delta -= 15
        notes.append("weak_company_match")

    if hr_intent(blob):
        delta += 25
    if any(x in blob for x in ("присылайте резюме", "отклик", "в лс", " напиши ")):
        delta += 10

    if has_person_title(v):
        delta += 12
    elif un in GENERIC_USERNAMES:
        delta -= 25
        notes.append("generic_username")

    return delta, notes