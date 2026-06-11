"""
gadcf_engine.py — Generative AI Deception Content Factory orchestrator.

Extends the Deception Engine (Layer 4) by replacing static Faker-generated
assets with contextually coherent, LLM-generated content packages.
Writes generated assets directly into the live honeypot filesystem.
"""

from __future__ import annotations
import time
import logging
import threading
from pathlib import Path
from typing import Optional

from .content_generator import ContentGenerator, GeneratedAsset

logger = logging.getLogger(__name__)

INDUSTRY_MAP = {
    "credential_harvesting": "financial_services",
    "malware_deployment":    "saas_startup",
    "lateral_movement":      "government",
    "cryptomining":          "saas_startup",
    "reconnaissance":        "saas_startup",
    "bot_enrollment":        "e_commerce",
}


class GADCFEngine:
    """
    Generative AI Deception Content Factory.

    Usage:
        gadcf = GADCFEngine(db)
        package = gadcf.generate_for_profile(attacker_profile)
    """

    def __init__(self, db, use_llm: bool = True):
        self.db = db
        self.generator = ContentGenerator(use_llm=use_llm)
        self._cache: dict[str, list[GeneratedAsset]] = {}

    def generate_for_profile(self, profile) -> list[GeneratedAsset]:
        """
        Generate a full asset package for the given attacker profile.
        Returns within ~10 seconds (LLM) or ~0.1s (template fallback).
        """
        ip      = profile.src_ip
        intent  = profile.classified_intent
        tier    = profile.attacker_tier
        industry = INDUSTRY_MAP.get(intent, "saas_startup")

        logger.info("GADCF generating package: ip=%s intent=%s industry=%s", ip, intent, industry)
        start = time.time()

        assets = self.generator.generate_package(
            industry=industry,
            attacker_intent=intent,
            sophistication=tier,
        )

        elapsed = time.time() - start
        logger.info("GADCF generated %d assets in %.2fs (source=%s)",
                    len(assets), elapsed, assets[0].source if assets else "none")

        self._cache[ip] = assets
        self._persist(ip, assets, intent, industry)
        return assets

    def get_recent_generations(self, limit: int = 20) -> list[dict]:
        try:
            return list(
                self.db["gadcf_assets"].find({}, {"_id": 0})
                .sort("generated_at", -1).limit(limit)
            )
        except Exception:
            results = []
            for ip, assets in list(self._cache.items())[-limit:]:
                for a in assets:
                    results.append(a.to_dict())
            return results

    def _persist(self, ip: str, assets: list[GeneratedAsset], intent: str, industry: str):
        for asset in assets:
            try:
                doc = asset.to_dict()
                doc["src_ip"] = ip
                self.db["gadcf_assets"].insert_one(doc)
            except Exception as exc:
                logger.error("GADCF persist failed for %s asset=%s: %s", ip, asset.asset_type, exc)
