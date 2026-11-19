#!/usr/bin/env python3
"""Тесты bio-first ранжирования (без сети)."""
from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

from rank_contacts import rank_and_pick  # noqa: E402


def _case(username: str, title: str, description: str, reason: str, score: int = 82):
    return (
        {
            "candidates": [
                {
                    "username": username,
                    "score": score,
                    "source": f"ddg:test",
                    "reason": reason,
                    "role": "",
                    "display_name": "",
                }
            ]
        },
        [
            {
                "username": username,
                "alive": True,
                "title": title,
                "description": description,
                "is_channel": False,
                "is_bot": False,
            }
        ],
    )


class StoneFalsePositives(unittest.TestCase):
    def test_stonemrkt_rejected(self):
        disc, verified = _case(
            "stonemrkt",
            "Stone Market",
            "Поставщик гранитной продукции оптом: памятники, плитка",
            "сценарий: DDG recruiter",
            35,
        )
        out = rank_and_pick("stone", "", disc, verified, set())
        self.assertIsNone(out["best_contact"])
        names = {x["username"] for x in out["filtered_contacts"]}
        self.assertIn("stonemrkt", names)

    def test_junior_rejected(self):
        disc, verified = _case("junior", "Junior", "Contact me", "hrhub ddg snippet", 35)
        out = rank_and_pick("stone", "", disc, verified, set())
        self.assertIsNone(out["best_contact"])

    def test_essaywork_rejected(self):
        disc, verified = _case(
            "essaywork",
            "Essay",
            "Напишем курсовые и эссе",
            "сценарий: DDG recruiter",
            35,
        )
        out = rank_and_pick("stone", "", disc, verified, set())
        self.assertIsNone(out["best_contact"])

    def test_work4writers_spam(self):
        disc, verified = _case(
            "work4writers",
            "Work for writers",
            "Канал вакансий для авторов",
            "hrhub ddg snippet",
            35,
        )
        out = rank_and_pick("stone", "", disc, verified, set())
        self.assertIsNone(out["best_contact"])
        row = next(x for x in out["filtered_contacts"] if x["username"] == "work4writers")
        self.assertIn("spam_username", row["reject_reason"])


    def test_lsr_rejects_samokat_bio(self):
        disc = {
            "candidates": [
                {
                    "username": "ivan_hr_samokat",
                    "score": 50,
                    "source": "ddg:test",
                    "reason": "сценарий: DDG recruiter",
                    "role": "",
                    "display_name": "",
                }
            ]
        }
        verified = [
            {
                "username": "ivan_hr_samokat",
                "alive": True,
                "title": "Иван",
                "description": "HR BP в Самокате, подбор курьеров",
                "is_channel": False,
                "is_bot": False,
            }
        ]
        out = rank_and_pick("ЛСР", "", disc, verified, set())
        self.assertIsNone(out["best_contact"])

    def test_hr_departamentc_scam_even_if_seed_reason(self):
        disc, verified = _case(
            "hr_departamentc",
            "Stone Group",
            "Присылайте резюме",
            "seed (fake)",
            100,
        )
        out = rank_and_pick("stone", "", disc, verified, set())
        self.assertIsNone(out["best_contact"])


if __name__ == "__main__":
    unittest.main()