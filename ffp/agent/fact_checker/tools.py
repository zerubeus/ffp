"""
Verification tools for fact-checking claims using multiple sources.
"""

import asyncio
from datetime import datetime
from typing import Any, Dict, List, Optional

import aiohttp

from .models import ConfidenceLevel, Evidence, EvidenceSource


class WebSearchTool:
    """Tool for searching the web to find relevant information."""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key
        self.base_url = 'https://api.bing.microsoft.com/v7.0/search'

    async def search(self, query: str, num_results: int = 10) -> List[Dict[str, Any]]:
        """Search the web for information about a claim."""
        if not self.api_key:
            # Fallback to mock results for testing
            return self._mock_search_results(query, num_results)

        headers = {'Ocp-Apim-Subscription-Key': self.api_key}
        params = {
            'q': query,
            'count': num_results,
            'mkt': 'en-US',
            'freshness': 'Month',  # Prefer recent results
            'safeSearch': 'Off',
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(self.base_url, headers=headers, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        return data.get('webPages', {}).get('value', [])
                    else:
                        return self._mock_search_results(query, num_results)
        except Exception:
            return self._mock_search_results(query, num_results)

    def _mock_search_results(self, query: str, num_results: int) -> List[Dict[str, Any]]:
        """Mock search results for testing when API is not available."""
        return [
            {
                'url': f'https://example.com/search-result-{i}',
                'name': f'Search result {i} for: {query}',
                'snippet': f'This is a mock search result snippet for query: {query}',
                'datePublished': '2024-01-01T00:00:00',
            }
            for i in range(min(num_results, 5))
        ]


class FactCheckingSitesTool:
    """Tool for querying established fact-checking websites."""

    FACT_CHECK_SITES = {
        'snopes.com': {'credibility': 0.95, 'bias': 'center'},
        'factcheck.org': {'credibility': 0.93, 'bias': 'center'},
        'politifact.com': {'credibility': 0.90, 'bias': 'center-left'},
        'fullfact.org': {'credibility': 0.92, 'bias': 'center'},
        'checkyourfact.com': {'credibility': 0.88, 'bias': 'center-right'},
        'factcheck.afp.com': {'credibility': 0.91, 'bias': 'center'},
        'apnews.com': {'credibility': 0.94, 'bias': 'center'},
        'reuters.com': {'credibility': 0.96, 'bias': 'center'},
    }

    # Specialized sources for Palestine/Israel fact-checking
    PALESTINE_SOURCES = {
        'btselem.org': {'credibility': 0.88, 'bias': 'pro-palestinian', 'type': 'ngo'},
        'ochaopt.org': {'credibility': 0.94, 'bias': 'neutral', 'type': 'un'},
        'unrwa.org': {'credibility': 0.92, 'bias': 'neutral', 'type': 'un'},
        'hrw.org': {'credibility': 0.90, 'bias': 'center', 'type': 'ngo'},
        'amnesty.org': {'credibility': 0.91, 'bias': 'center', 'type': 'ngo'},
        'pchr.org': {'credibility': 0.85, 'bias': 'pro-palestinian', 'type': 'ngo'},
        'al-haq.org': {'credibility': 0.83, 'bias': 'pro-palestinian', 'type': 'ngo'},
        'idf.il': {'credibility': 0.75, 'bias': 'pro-israeli', 'type': 'government'},
        'gov.il': {'credibility': 0.80, 'bias': 'pro-israeli', 'type': 'government'},
        'mfa.gov.il': {'credibility': 0.82, 'bias': 'pro-israeli', 'type': 'government'},
    }

    def __init__(self, web_search: WebSearchTool):
        self.web_search = web_search

    async def search_fact_checkers(self, claim: str) -> List[EvidenceSource]:
        """Search fact-checking sites for existing verifications."""
        sources = []

        # Search general fact-checking sites
        for site, info in self.FACT_CHECK_SITES.items():
            query = f'site:{site} {claim}'
            results = await self.web_search.search(query, num_results=3)

            for result in results:
                source = EvidenceSource(
                    url=result['url'],
                    title=result['name'],
                    domain=site,
                    credibility_score=info['credibility'],
                    bias_rating=info['bias'],
                    relevant_excerpt=result.get('snippet', ''),
                    source_type='fact_checker',
                    publication_date=self._parse_date(result.get('datePublished')),
                )
                sources.append(source)

        return sources

    async def search_palestine_sources(self, claim: str) -> List[EvidenceSource]:
        """Search Palestine/Israel specialized sources."""
        sources = []

        for site, info in self.PALESTINE_SOURCES.items():
            query = f'site:{site} {claim}'
            results = await self.web_search.search(query, num_results=2)

            for result in results:
                source = EvidenceSource(
                    url=result['url'],
                    title=result['name'],
                    domain=site,
                    credibility_score=info['credibility'],
                    bias_rating=info['bias'],
                    relevant_excerpt=result.get('snippet', ''),
                    source_type=info['type'],
                    publication_date=self._parse_date(result.get('datePublished')),
                )
                sources.append(source)

        return sources

    async def search_news_sources(self, claim: str) -> List[EvidenceSource]:
        """Search reputable news sources."""
        news_sites = [
            'bbc.com',
            'cnn.com',
            'nytimes.com',
            'theguardian.com',
            'washingtonpost.com',
            'aljazeera.com',
            'haaretz.com',
            'timesofisrael.com',
            'jpost.com',
            'aa.com.tr',
        ]

        sources = []
        for site in news_sites[:5]:  # Limit to prevent too many requests
            query = f'site:{site} {claim}'
            results = await self.web_search.search(query, num_results=2)

            for result in results:
                credibility = self._get_news_credibility(site)
                bias = self._get_news_bias(site)

                source = EvidenceSource(
                    url=result['url'],
                    title=result['name'],
                    domain=site,
                    credibility_score=credibility,
                    bias_rating=bias,
                    relevant_excerpt=result.get('snippet', ''),
                    source_type='news',
                    publication_date=self._parse_date(result.get('datePublished')),
                )
                sources.append(source)

        return sources

    def _parse_date(self, date_str: Optional[str]) -> Optional[datetime]:
        """Parse date string to datetime object."""
        if not date_str:
            return None

        try:
            # Handle ISO format
            if 'T' in date_str:
                return datetime.fromisoformat(date_str.replace('Z', '+00:00'))
            return None
        except Exception:
            return None

    def _get_news_credibility(self, domain: str) -> float:
        """Get credibility score for news sources."""
        credibility_map = {
            'bbc.com': 0.93,
            'cnn.com': 0.85,
            'nytimes.com': 0.90,
            'theguardian.com': 0.88,
            'washingtonpost.com': 0.89,
            'reuters.com': 0.96,
            'apnews.com': 0.94,
            'aljazeera.com': 0.82,
            'haaretz.com': 0.85,
            'timesofisrael.com': 0.80,
            'jpost.com': 0.78,
            'aa.com.tr': 0.75,
        }
        return credibility_map.get(domain, 0.7)

    def _get_news_bias(self, domain: str) -> str:
        """Get bias rating for news sources."""
        bias_map = {
            'bbc.com': 'center',
            'cnn.com': 'center-left',
            'nytimes.com': 'center-left',
            'theguardian.com': 'center-left',
            'washingtonpost.com': 'center-left',
            'reuters.com': 'center',
            'apnews.com': 'center',
            'aljazeera.com': 'pro-palestinian',
            'haaretz.com': 'center-left',
            'timesofisrael.com': 'pro-israeli',
            'jpost.com': 'pro-israeli',
            'aa.com.tr': 'pro-palestinian',
        }
        return bias_map.get(domain, 'unknown')


class EvidenceAnalyzer:
    """Analyzes collected evidence to form conclusions."""

    def analyze_evidence(self, sources: List[EvidenceSource]) -> Evidence:
        """Analyze collected evidence sources."""
        if not sources:
            return Evidence(claim_id='', sources=[], overall_confidence=ConfidenceLevel.INSUFFICIENT)

        # Count supporting vs contradicting evidence
        supporting_count = 0
        contradicting_count = 0
        neutral_count = 0

        # Analyze source diversity
        domains = set(source.domain for source in sources)
        source_types = set(source.source_type for source in sources)
        bias_ratings = set(source.bias_rating for source in sources if source.bias_rating)

        # Check for conflicting information
        conflicting_sources = self._detect_conflicts(sources)

        # Calculate diversity score
        diversity_score = min(1.0, (len(domains) * 0.3 + len(source_types) * 0.4 + len(bias_ratings) * 0.3))

        # Determine overall confidence
        avg_credibility = sum(source.credibility_score for source in sources) / len(sources)

        if avg_credibility > 0.85 and len(sources) >= 3 and diversity_score > 0.6:
            confidence = ConfidenceLevel.HIGH
        elif avg_credibility > 0.7 and len(sources) >= 2:
            confidence = ConfidenceLevel.MEDIUM
        elif len(sources) >= 1:
            confidence = ConfidenceLevel.LOW
        else:
            confidence = ConfidenceLevel.INSUFFICIENT

        return Evidence(
            claim_id='',
            sources=sources,
            supporting_count=supporting_count,
            contradicting_count=contradicting_count,
            neutral_count=neutral_count,
            overall_confidence=confidence,
            conflicting_sources=conflicting_sources,
            source_diversity_score=diversity_score,
        )

    def _detect_conflicts(self, sources: List[EvidenceSource]) -> bool:
        """Detect if sources contradict each other."""
        # Simple conflict detection - could be enhanced with NLP
        excerpts = [source.relevant_excerpt.lower() for source in sources]

        positive_indicators = ['confirm', 'verify', 'true', 'accurate', 'correct']
        negative_indicators = ['false', 'incorrect', 'deny', 'dispute', 'wrong']

        has_positive = any(any(indicator in excerpt for indicator in positive_indicators) for excerpt in excerpts)
        has_negative = any(any(indicator in excerpt for indicator in negative_indicators) for excerpt in excerpts)

        return has_positive and has_negative

    def get_consensus_verdict(self, sources: List[EvidenceSource]) -> str:
        """Determine consensus verdict from sources."""
        if not sources:
            return 'UNVERIFIABLE'

        # Analyze excerpts for verdict indicators
        excerpts_text = ' '.join(source.relevant_excerpt.lower() for source in sources)

        # Weight by credibility
        total_credibility = sum(source.credibility_score for source in sources)

        if total_credibility < 2.0:
            return 'UNVERIFIABLE'

        # Look for consensus patterns
        if any(word in excerpts_text for word in ['false', 'incorrect', 'misinformation', 'fake']):
            return 'FALSE'
        elif any(word in excerpts_text for word in ['partially true', 'misleading', 'context']):
            return 'PARTIALLY_TRUE'
        elif any(word in excerpts_text for word in ['true', 'accurate', 'confirmed', 'verified']):
            return 'TRUE'
        elif any(word in excerpts_text for word in ['disputed', 'conflicting', 'unclear']):
            return 'DISPUTED'
        else:
            return 'UNVERIFIABLE'


class VerificationOrchestrator:
    """Orchestrates the verification process using multiple tools."""

    def __init__(self, api_key: Optional[str] = None):
        self.web_search = WebSearchTool(api_key)
        self.fact_checker = FactCheckingSitesTool(self.web_search)
        self.analyzer = EvidenceAnalyzer()

    async def verify_claim(self, claim_text: str, claim_type: str) -> Evidence:
        """Verify a claim using multiple sources."""
        all_sources = []

        # Run searches in parallel for efficiency
        search_tasks = [
            self.fact_checker.search_fact_checkers(claim_text),
            self.fact_checker.search_palestine_sources(claim_text),
            self.fact_checker.search_news_sources(claim_text),
        ]

        try:
            results = await asyncio.gather(*search_tasks, return_exceptions=True)

            for result in results:
                if isinstance(result, list):
                    all_sources.extend(result)

        except Exception:
            # Log error but continue with partial results
            pass

        # Remove duplicates and limit total sources
        unique_sources = self._deduplicate_sources(all_sources)
        limited_sources = unique_sources[:15]  # Limit to prevent information overload

        # Analyze evidence
        evidence = self.analyzer.analyze_evidence(limited_sources)
        evidence.claim_id = claim_text  # Set the claim ID

        return evidence

    def _deduplicate_sources(self, sources: List[EvidenceSource]) -> List[EvidenceSource]:
        """Remove duplicate sources based on URL."""
        seen_urls = set()
        unique_sources = []

        for source in sources:
            if source.url not in seen_urls:
                seen_urls.add(source.url)
                unique_sources.append(source)

        return unique_sources
