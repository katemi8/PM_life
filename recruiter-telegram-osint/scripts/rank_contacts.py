#!/usr/bin/env python3
"""Ранжирование после verify: prior из discover + обязательная проверка био."""
from __future__ import annotations

import datetime
import json
import re
import sys
from pathlib import Path

_SCRIPTS = Path(__file__).resolve().parent
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

from company_match import MatchTier, build_company_profile, match_company  # noqa: E402
from profile_signals import (
    bio_adjustments,
    bio_blob,
    detect_channel,
    has_person_title,
    hr_intent,
    is_platform_account,
    is_spam_username,
)

TYPE_RANK = {"рекрутер": 0, "сотрудник": 1, "канал": 2}
PASS_SCORE = 70

RECR_MARK = ("recruiter", "рекрут", " hr", "hr ", "talent", "кадр", "подбор", "hiring")


def source_prior(reason: str, discover_score: int) -> int:
    r = (reason or "").casefold()
    if r.startswith("seed"):
        return 100
    if "productcamp" in r or "нетворк" in r or r == "network":
        return max(discover_score, 88)
    if r.startswith("--url"):
        return max(discover_score, 85)
    if "hrhub ddg snippet" in r or ("snippet" in r and "hirehi" not in r):
        return min(discover_score, 35)
    if r.startswith("сценарий: ddg"):
        return min(discover_score, 50)
    if "hr-канал @" in r:
        return min(discover_score, 72)
    if "hirehi" in r:
        return min(discover_score, 65)
    return discover_score


def profile_employer_conflicts(v: dict, company_cf: str) -> bool:
    if (v.get("match_reason") or "").startswith("seed"):
        return False
    text = bio_blob(v)
    if len(re.sub(r"\s+", " ", text).strip()) < 15:
        return False
    target = [company_cf, *company_cf.split()]
    if "домклик" in company_cf or company_cf == "domclick":
        target.extend(["domclick", "домклик", "сбер", "sber"])
    if any(t and t in text for t in dict.fromkeys(target)):
        return False
    other_employers = (
        "ozon",
        "wildberries",
        "яндекс",
        "yandex",
        "avito",
        "tinkoff",
        "тинькофф",
        "т-банк",
        "kaspersky",
        "lamoda",
        "vk team",
        "вконтакте",
        "kion",
        "x5 digital",
        "сбермаркет",
    )
    return any(m in text for m in other_employers)


def is_brand_channel(v: dict, company_cf: str) -> bool:
    un = v["username"].casefold()
    if un.endswith(("_official", "_pr", "_admin")):
        return True
    text = bio_blob(v)
    if "официальн" in text and "канал" in text:
        return True
    if "неофициальн" in text and "канал" in text:
        return True
    slug = re.sub(r"[^a-z0-9]+", "", company_cf)
    if slug and len(slug) > 4 and un.startswith(slug) and not (v.get("title") or "").strip():
        return True
    return False


def classify_contact_type(v: dict, company_cf: str) -> str:
    reason = (v.get("match_reason") or "").casefold()
    text = bio_blob(v)
    if detect_channel(v) or is_spam_username(v["username"]) or is_brand_channel(v, company_cf):
        return "канал"
    if (v.get("match_reason") or "").startswith("seed"):
        return "рекрутер"
    hr_profile = any(
        x in text
        for x in ("recruiter", "рекрут", " hr ", "hiring", "кадр", "talent", "подбор")
    )
    hr_reason = any(
        x in reason
        for x in (
            "t.me профиль hr",
            "сверка профиля hr",
            "hr-канал @",
            "вакансия в tg",
        )
    )
    if (hr_profile or hr_reason) and has_person_title(v):
        if "hrhub ddg snippet" not in reason:
            return "рекрутер"
    if "productcamp" in reason or "нетворк" in reason or reason == "network":
        return "сотрудник"
    if reason.startswith("--url") and has_person_title(v):
        return "сотрудник"
    if has_person_title(v) and any(
        x in (v.get("role") or "").casefold()
        for x in ("продакт", "product", "менеджер", "директор", "lead", "cpo", "cje", "сje")
    ):
        return "сотрудник"
    if reason.startswith("сценарий: ddg") and not has_person_title(v):
        return "канал"
    if "snippet" in reason and not has_person_title(v):
        return "канал"
    if has_person_title(v):
        return "сотрудник"
    return "канал"


def sort_contacts(contacts: list[dict]) -> list[dict]:
    return sorted(
        contacts,
        key=lambda x: (
            TYPE_RANK.get(x.get("contact_type"), 2),
            0 if (x.get("match_reason") or "").startswith("seed") else 1,
            -(x.get("score") or 0),
            x.get("username", "").casefold(),
        ),
    )


def finalize_score(v: dict, profile, company_cf: str) -> None:
    reason = v.get("match_reason") or ""
    prior = source_prior(reason, int(v.get("score") or 0))
    if reason.startswith("seed"):
        if is_spam_username(v["username"]):
            v["score"] = -100
            v["signal_notes"] = ["seed_blocked_scam"]
            return
        v["score"] = prior
        v["signal_notes"] = ["seed_prior"]
        return
    tier = match_company(bio_blob(v), v["username"], profile)
    delta, notes = bio_adjustments(v, tier_value=int(tier), ambiguous=profile.ambiguous)
    score = prior + delta
    text = bio_blob(v)
    if int(tier) >= MatchTier.TOKEN and hr_intent(text):
        score += 8
    if profile.ambiguous and int(tier) <= MatchTier.WEAK_SUBSTR and prior < 80:
        score -= 20
        notes.append("ambiguous_bio_gate")
    v["score"] = score
    v["company_match_tier"] = tier.name
    v["signal_notes"] = notes


def rank_and_pick(
    company: str,
    extra: str,
    disc: dict,
    verified: list[dict],
    skip_cf: set[str],
) -> dict:
    meta = {c["username"].casefold(): c for c in disc.get("candidates") or []}
    alive = [v for v in verified if v.get("alive")]
    company_cf = company.casefold()

    has_seed = any(
        (c.get("reason") or "").startswith("seed") for c in disc.get("candidates") or []
    )
    has_network = any(
        (c.get("reason") or "") in ("network",)
        or "нетворк" in (c.get("reason") or "").casefold()
        or "productcamp" in (c.get("reason") or "").casefold()
        for c in disc.get("candidates") or []
    )
    profile = build_company_profile(company, has_seed=has_seed, has_network=has_network)

    filtered_out: list[dict] = []
    for v in alive:
        m = meta.get(v["username"].casefold(), {})
        v["source_url"] = m.get("source")
        v["match_reason"] = m.get("reason")
        v["score"] = m.get("score", 0)
        v["role"] = m.get("role") or ""
        v["display_name"] = m.get("display_name") or ""
        finalize_score(v, profile, company_cf)
        if not (v.get("role") or "").strip():
            td = f"{v.get('title', '')} {v.get('description', '')}".strip()
            if "recruiter" in td.casefold() or "рекрут" in td.casefold():
                v["role"] = td[:80]

    survivors = []
    for v in alive:
        reasons = []
        if is_spam_username(v["username"]):
            reasons.append("spam_username")
        if v.get("is_bot"):
            reasons.append("bot")
        if v.get("score", 0) < PASS_SCORE:
            reasons.append("score_below_70")
        if is_platform_account(v):
            reasons.append("platform")
        if is_brand_channel(v, company_cf):
            reasons.append("brand_channel")
        if profile_employer_conflicts(v, company_cf):
            reasons.append("employer_conflict")
        if v["username"].casefold() in skip_cf:
            reasons.append("skipped")
        if reasons:
            filtered_out.append({"username": v["username"], "reject_reason": reasons})
            continue
        survivors.append(v)

    for v in survivors:
        v["contact_type"] = classify_contact_type(v, company_cf)

    people = [v for v in survivors if v["contact_type"] != "канал"]
    pool = people if people else survivors
    recruiters = [v for v in pool if v["contact_type"] == "рекрутер"]
    insiders = [v for v in pool if v["contact_type"] == "сотрудник"]
    ordered_recruiters = sort_contacts(recruiters)
    ordered_insiders = sort_contacts(insiders)
    ordered_channels = sort_contacts([v for v in survivors if v["contact_type"] == "канал"])
    if ordered_recruiters:
        picked = ordered_recruiters[:1]
        rest = ordered_recruiters[1:3] + ordered_insiders + ordered_channels
    elif ordered_insiders:
        picked = ordered_insiders[:1]
        rest = ordered_insiders[1:3] + ordered_channels
    else:
        picked = ordered_channels[:1]
        rest = ordered_channels[1:6]
    alternates = [v for v in rest if v != (picked[0] if picked else None)][:6]
    found = (picked + alternates) if picked else []
    best = found[0] if found else None

    return {
        "company": company,
        "queried_at": datetime.datetime.now(datetime.timezone.utc)
        .replace(microsecond=0)
        .isoformat(),
        "hh_employer_id": None,
        "extra_url": extra or None,
        "best_contact": best,
        "contacts": found,
        "alternates": found[1:],
        "skipped_usernames": sorted(skip_cf),
        "rejected_usernames": [v for v in verified if not v.get("alive")],
        "filtered_contacts": filtered_out,
    }


def main() -> int:
    if len(sys.argv) < 6:
        print(
            "Usage: rank_contacts.py COMPANY EXTRA_URL discover.json verified.json skip_csv",
            file=sys.stderr,
        )
        return 2
    company, extra, disc_path, vpath, skip_csv = sys.argv[1:6]
    skip_cf = {s.casefold() for s in skip_csv.split(",") if s.strip()}
    disc = json.loads(Path(disc_path).read_text(encoding="utf-8"))
    verified = json.loads(Path(vpath).read_text(encoding="utf-8"))
    out = rank_and_pick(company, extra, disc, verified, skip_cf)
    print(json.dumps(out, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())