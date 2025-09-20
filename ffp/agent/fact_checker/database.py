"""
Database integration for fact-checking agent using SQLite.
"""

import hashlib
import json
from datetime import datetime, timedelta
from typing import Any

import aiosqlite

from .models import Claim, ConfidenceLevel, FactCheckVerdict, PostAnalysis


class FactCheckDatabase:
    """Database handler for fact-checking operations."""

    def __init__(self, db_path: str = 'fact_check.db'):
        self.db_path = db_path

    async def setup_database(self):
        """Initialize the fact-checking database schema."""
        async with aiosqlite.connect(self.db_path) as db:
            await db.executescript("""
                -- Verified facts cache
                CREATE TABLE IF NOT EXISTS verified_facts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    claim_hash TEXT UNIQUE NOT NULL,
                    original_claim TEXT NOT NULL,
                    verdict TEXT NOT NULL,
                    confidence TEXT NOT NULL,
                    explanation TEXT,
                    evidence_summary TEXT,
                    sources_json TEXT,
                    sensitive_topic BOOLEAN DEFAULT FALSE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    access_count INTEGER DEFAULT 0,
                    last_accessed TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );

                -- Entity facts for quick lookups
                CREATE TABLE IF NOT EXISTS entity_facts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    entity_name TEXT NOT NULL,
                    entity_type TEXT,
                    fact_statement TEXT NOT NULL,
                    source_url TEXT,
                    credibility_score REAL,
                    bias_rating TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );

                -- Post analysis results
                CREATE TABLE IF NOT EXISTS post_analyses (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    post_id TEXT UNIQUE NOT NULL,
                    post_url TEXT,
                    post_text TEXT NOT NULL,
                    overall_credibility TEXT NOT NULL,
                    claims_count INTEGER DEFAULT 0,
                    verdicts_count INTEGER DEFAULT 0,
                    potential_misinformation BOOLEAN DEFAULT FALSE,
                    requires_human_review BOOLEAN DEFAULT FALSE,
                    topic_sensitivity TEXT DEFAULT 'normal',
                    warning_flags_json TEXT,
                    analysis_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );

                -- Claims extracted from posts
                CREATE TABLE IF NOT EXISTS claims (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    post_analysis_id INTEGER,
                    claim_id TEXT UNIQUE NOT NULL,
                    claim_text TEXT NOT NULL,
                    claim_type TEXT NOT NULL,
                    confidence REAL,
                    context TEXT,
                    entities_json TEXT,
                    keywords_json TEXT,
                    location_context TEXT,
                    temporal_context TEXT,
                    FOREIGN KEY (post_analysis_id) REFERENCES post_analyses(id)
                );

                -- Verdicts for claims
                CREATE TABLE IF NOT EXISTS verdicts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    claim_id TEXT NOT NULL,
                    verdict TEXT NOT NULL,
                    confidence TEXT NOT NULL,
                    explanation TEXT,
                    evidence_summary TEXT,
                    sources_consulted_json TEXT,
                    limitations TEXT,
                    context_needed TEXT,
                    verification_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    sensitive_topic BOOLEAN DEFAULT FALSE,
                    FOREIGN KEY (claim_id) REFERENCES claims(claim_id)
                );

                -- Palestine-specific context tracking
                CREATE TABLE IF NOT EXISTS palestine_context (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    post_analysis_id INTEGER,
                    involves_casualties BOOLEAN DEFAULT FALSE,
                    involves_settlements BOOLEAN DEFAULT FALSE,
                    involves_international_law BOOLEAN DEFAULT FALSE,
                    involves_historical_events BOOLEAN DEFAULT FALSE,
                    involves_territory_claims BOOLEAN DEFAULT FALSE,
                    involves_human_rights BOOLEAN DEFAULT FALSE,
                    time_period TEXT,
                    geographical_scope TEXT,
                    source_perspective TEXT,
                    FOREIGN KEY (post_analysis_id) REFERENCES post_analyses(id)
                );

                -- Source reliability tracking
                CREATE TABLE IF NOT EXISTS source_reliability (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    domain TEXT UNIQUE NOT NULL,
                    credibility_score REAL,
                    bias_rating TEXT,
                    source_type TEXT,
                    verification_count INTEGER DEFAULT 0,
                    accuracy_rate REAL,
                    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );

                -- Performance metrics
                CREATE TABLE IF NOT EXISTS fact_check_metrics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    date DATE NOT NULL,
                    total_claims_processed INTEGER DEFAULT 0,
                    high_confidence_verdicts INTEGER DEFAULT 0,
                    medium_confidence_verdicts INTEGER DEFAULT 0,
                    low_confidence_verdicts INTEGER DEFAULT 0,
                    cache_hit_rate REAL DEFAULT 0.0,
                    average_processing_time REAL DEFAULT 0.0,
                    palestine_related_claims INTEGER DEFAULT 0
                );

                -- Indexes for performance
                CREATE INDEX IF NOT EXISTS idx_claim_hash ON verified_facts(claim_hash);
                CREATE INDEX IF NOT EXISTS idx_entity_name ON entity_facts(entity_name);
                CREATE INDEX IF NOT EXISTS idx_post_id ON post_analyses(post_id);
                CREATE INDEX IF NOT EXISTS idx_claim_id ON claims(claim_id);
                CREATE INDEX IF NOT EXISTS idx_verdict_claim_id ON verdicts(claim_id);
                CREATE INDEX IF NOT EXISTS idx_source_domain ON source_reliability(domain);
                CREATE INDEX IF NOT EXISTS idx_created_at ON verified_facts(created_at);
                CREATE INDEX IF NOT EXISTS idx_analysis_timestamp ON post_analyses(analysis_timestamp);
            """)
            await db.commit()

    def _hash_claim(self, claim_text: str) -> str:
        """Generate a hash for claim text to enable fast lookups."""
        # Normalize the claim text for consistent hashing
        normalized = claim_text.lower().strip()
        return hashlib.sha256(normalized.encode()).hexdigest()

    async def lookup_claim(self, claim_text: str) -> FactCheckVerdict | None:
        """Look up a previously verified claim."""
        claim_hash = self._hash_claim(claim_text)

        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute(
                """
                SELECT original_claim, verdict, confidence, explanation,
                       evidence_summary, sources_json, sensitive_topic, created_at
                FROM verified_facts
                WHERE claim_hash = ? AND created_at > datetime('now', '-30 days')
                ORDER BY created_at DESC LIMIT 1
            """,
                (claim_hash,),
            ) as cursor:
                row = await cursor.fetchone()
                if row:
                    # Update access tracking
                    await db.execute(
                        """
                        UPDATE verified_facts
                        SET access_count = access_count + 1, last_accessed = CURRENT_TIMESTAMP
                        WHERE claim_hash = ?
                    """,
                        (claim_hash,),
                    )
                    await db.commit()

                    # Parse sources
                    sources = json.loads(row[5]) if row[5] else []

                    return FactCheckVerdict(
                        claim_id=claim_text,
                        verdict=row[1],
                        confidence=ConfidenceLevel(row[2]),
                        explanation=row[3] or '',
                        evidence_summary=row[4] or '',
                        sources_consulted=sources,
                        verification_timestamp=datetime.fromisoformat(row[7]),
                        sensitive_topic=bool(row[6]),
                    )
        return None

    async def store_verification(self, verdict: FactCheckVerdict):
        """Store a completed fact-check for future reference."""
        claim_hash = self._hash_claim(verdict.claim_id)
        sources_json = json.dumps(verdict.sources_consulted)

        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """
                INSERT OR REPLACE INTO verified_facts
                (claim_hash, original_claim, verdict, confidence, explanation,
                 evidence_summary, sources_json, sensitive_topic, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            """,
                (
                    claim_hash,
                    verdict.claim_id,
                    verdict.verdict,
                    verdict.confidence.value,
                    verdict.explanation,
                    verdict.evidence_summary,
                    sources_json,
                    verdict.sensitive_topic,
                ),
            )
            await db.commit()

    async def store_post_analysis(self, analysis: PostAnalysis) -> int:
        """Store a complete post analysis."""
        warning_flags_json = json.dumps(analysis.warning_flags)

        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                """
                INSERT OR REPLACE INTO post_analyses
                (post_id, post_url, post_text, overall_credibility, claims_count,
                 verdicts_count, potential_misinformation, requires_human_review,
                 topic_sensitivity, warning_flags_json, analysis_timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    analysis.post_id,
                    analysis.post_url,
                    analysis.post_text,
                    analysis.overall_credibility.value,
                    len(analysis.claims),
                    len(analysis.verdicts),
                    analysis.potential_misinformation,
                    analysis.requires_human_review,
                    analysis.topic_sensitivity,
                    warning_flags_json,
                    analysis.analysis_timestamp,
                ),
            )

            post_analysis_id = cursor.lastrowid

            # Store claims
            for claim in analysis.claims:
                await self._store_claim(db, post_analysis_id, claim)

            # Store verdicts
            for verdict in analysis.verdicts:
                await self._store_verdict(db, verdict)

            await db.commit()
            return post_analysis_id

    async def _store_claim(self, db: aiosqlite.Connection, post_analysis_id: int, claim: Claim):
        """Store a claim in the database."""
        entities_json = json.dumps(claim.extracted_entities)
        keywords_json = json.dumps(claim.keywords)

        await db.execute(
            """
            INSERT OR REPLACE INTO claims
            (post_analysis_id, claim_id, claim_text, claim_type, confidence,
             context, entities_json, keywords_json, location_context, temporal_context)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
            (
                post_analysis_id,
                claim.id,
                claim.text,
                claim.claim_type.value,
                claim.confidence,
                claim.context,
                entities_json,
                keywords_json,
                claim.location_context,
                claim.temporal_context,
            ),
        )

    async def _store_verdict(self, db: aiosqlite.Connection, verdict: FactCheckVerdict):
        """Store a verdict in the database."""
        sources_json = json.dumps(verdict.sources_consulted)

        await db.execute(
            """
            INSERT OR REPLACE INTO verdicts
            (claim_id, verdict, confidence, explanation, evidence_summary,
             sources_consulted_json, limitations, context_needed,
             verification_timestamp, sensitive_topic)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
            (
                verdict.claim_id,
                verdict.verdict,
                verdict.confidence.value,
                verdict.explanation,
                verdict.evidence_summary,
                sources_json,
                verdict.limitations,
                verdict.context_needed,
                verdict.verification_timestamp,
                verdict.sensitive_topic,
            ),
        )

    async def get_analysis_history(self, days: int = 7) -> list[dict[str, Any]]:
        """Get recent analysis history."""
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute(
                f"""
                SELECT post_id, post_url, overall_credibility, claims_count,
                       potential_misinformation, topic_sensitivity, analysis_timestamp
                FROM post_analyses
                WHERE analysis_timestamp > datetime('now', '-{days} days')
                ORDER BY analysis_timestamp DESC
            """
            ) as cursor:
                rows = await cursor.fetchall()

                return [
                    {
                        'post_id': row[0],
                        'post_url': row[1],
                        'overall_credibility': row[2],
                        'claims_count': row[3],
                        'potential_misinformation': bool(row[4]),
                        'topic_sensitivity': row[5],
                        'analysis_timestamp': row[6],
                    }
                    for row in rows
                ]

    async def get_cache_statistics(self) -> dict[str, Any]:
        """Get cache hit statistics."""
        async with aiosqlite.connect(self.db_path) as db:
            # Total cached claims
            async with db.execute('SELECT COUNT(*) FROM verified_facts') as cursor:
                total_cached = (await cursor.fetchone())[0]

            # Recent access patterns
            async with db.execute("""
                SELECT AVG(access_count), COUNT(*)
                FROM verified_facts
                WHERE last_accessed > datetime('now', '-7 days')
            """) as cursor:
                row = await cursor.fetchone()
                avg_access = row[0] or 0
                recent_accessed = row[1] or 0

            # Confidence distribution
            async with db.execute("""
                SELECT confidence, COUNT(*)
                FROM verified_facts
                GROUP BY confidence
            """) as cursor:
                confidence_dist = {row[0]: row[1] for row in await cursor.fetchall()}

            return {
                'total_cached_claims': total_cached,
                'average_access_count': avg_access,
                'recently_accessed': recent_accessed,
                'confidence_distribution': confidence_dist,
            }

    async def update_source_reliability(
        self, domain: str, credibility_score: float, bias_rating: str, source_type: str
    ):
        """Update reliability tracking for a source domain."""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """
                INSERT OR REPLACE INTO source_reliability
                (domain, credibility_score, bias_rating, source_type,
                 verification_count, last_updated)
                VALUES (?, ?, ?, ?,
                        COALESCE((SELECT verification_count FROM source_reliability WHERE domain = ?) + 1, 1),
                        CURRENT_TIMESTAMP)
            """,
                (domain, credibility_score, bias_rating, source_type, domain),
            )
            await db.commit()

    async def cleanup_old_data(self, days_to_keep: int = 90):
        """Clean up old fact-check data to maintain database size."""
        cutoff_date = datetime.now() - timedelta(days=days_to_keep)

        async with aiosqlite.connect(self.db_path) as db:
            # Clean up old verified facts with low access count
            await db.execute(
                """
                DELETE FROM verified_facts
                WHERE created_at < ? AND access_count < 2
            """,
                (cutoff_date,),
            )

            # Clean up old post analyses
            await db.execute(
                """
                DELETE FROM post_analyses
                WHERE analysis_timestamp < ?
            """,
                (cutoff_date,),
            )

            await db.commit()

    async def record_daily_metrics(self, metrics: dict[str, Any]):
        """Record daily performance metrics."""
        today = datetime.now().date()

        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """
                INSERT OR REPLACE INTO fact_check_metrics
                (date, total_claims_processed, high_confidence_verdicts,
                 medium_confidence_verdicts, low_confidence_verdicts,
                 cache_hit_rate, average_processing_time, palestine_related_claims)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    today,
                    metrics.get('total_claims', 0),
                    metrics.get('high_confidence', 0),
                    metrics.get('medium_confidence', 0),
                    metrics.get('low_confidence', 0),
                    metrics.get('cache_hit_rate', 0.0),
                    metrics.get('avg_processing_time', 0.0),
                    metrics.get('palestine_claims', 0),
                ),
            )
            await db.commit()

    async def get_trending_claims(self, days: int = 7, limit: int = 10) -> list[dict[str, Any]]:
        """Get trending/frequently appearing claims."""
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute(
                f"""
                SELECT original_claim, verdict, confidence, COUNT(*) as frequency
                FROM verified_facts
                WHERE created_at > datetime('now', '-{days} days')
                GROUP BY claim_hash
                HAVING frequency > 1
                ORDER BY frequency DESC, created_at DESC
                LIMIT ?
            """,
                (limit,),
            ) as cursor:
                rows = await cursor.fetchall()

                return [{'claim': row[0], 'verdict': row[1], 'confidence': row[2], 'frequency': row[3]} for row in rows]
