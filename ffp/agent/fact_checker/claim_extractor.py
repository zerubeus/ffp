"""
Claim extraction module for identifying factual claims in social media posts.
"""

import re
import uuid

from .models import Claim, ClaimType, PalestineFactCheckContext


class ClaimExtractor:
    """Extracts factual claims from social media posts using pattern matching and heuristics."""

    def __init__(self):
        self.palestine_keywords = {
            'locations': [
                'gaza',
                'west bank',
                'jerusalem',
                'hebron',
                'ramallah',
                'bethlehem',
                'tel aviv',
                'haifa',
                'beersheva',
                'acre',
                'nazareth',
                'jaffa',
                'rafah',
                'khan younis',
                'jabalia',
                'sheikh jarrah',
                'silwan',
            ],
            'organizations': [
                'idf',
                'hamas',
                'fatah',
                'plo',
                'un',
                'unrwa',
                'icj',
                'icc',
                'human rights watch',
                'amnesty international',
                "b'tselem",
            ],
            'conflict_terms': [
                'occupation',
                'blockade',
                'siege',
                'settlement',
                'apartheid',
                'intifada',
                'ceasefire',
                'violation',
                'war crime',
                'ethnic cleansing',
            ],
        }

    async def extract_claims(self, text: str) -> list[Claim]:
        """Extract factual claims from input text with Palestine/Israel context awareness."""
        # Split text into sentences for analysis
        sentences = self._split_sentences(text)
        claims = []

        for sentence in sentences:
            if self._is_factual_claim(sentence):
                claim = await self._create_claim_object(sentence, text)
                if claim:
                    claims.append(claim)

        return claims

    def _split_sentences(self, text: str) -> list[str]:
        """Split text into sentences for individual analysis."""
        # Simple sentence splitting - could be enhanced with spaCy
        sentence_endings = r'[.!?]+\s+'
        sentences = re.split(sentence_endings, text.strip())
        return [s.strip() for s in sentences if len(s.strip()) > 10]

    def _is_factual_claim(self, sentence: str) -> bool:
        """Determine if a sentence contains a factual claim."""
        sentence_lower = sentence.lower()

        # Skip subjective statements
        subjective_markers = [
            'i think',
            'i believe',
            'in my opinion',
            'i feel',
            'it seems',
            'personally',
            'i would say',
            'i guess',
            'maybe',
            'perhaps',
        ]
        if any(marker in sentence_lower for marker in subjective_markers):
            return False

        # Check for statistical claims
        if self._contains_statistics(sentence):
            return True

        # Check for temporal/historical claims
        if self._contains_temporal_markers(sentence):
            return True

        # Check for causal claims
        if self._contains_causal_language(sentence):
            return True

        # Check for quotes and attributions
        if self._contains_quotes(sentence):
            return True

        # Check for conflict-specific claims
        if self._contains_palestine_conflict_claims(sentence):
            return True

        return False

    def _contains_statistics(self, text: str) -> bool:
        """Check for statistical claims (percentages, numbers, etc.)."""
        patterns = [
            r'\d+%',  # percentages
            r'\d+(\.\d+)?\s*(million|billion|thousand|hundred)',  # large numbers
            r'\d+(\.\d+)?\s*(times|fold)',  # multipliers
            r'(increased|decreased|rose|fell|dropped)\s+by\s+\d+',  # changes
            r'\d+\s*(killed|dead|injured|wounded|casualties)',  # casualty figures
            r'\d+\s*(civilians|children|women|men)',  # demographic numbers
            r'over\s+\d+|more than\s+\d+|less than\s+\d+|approximately\s+\d+',  # approximations
        ]
        return any(re.search(pattern, text, re.IGNORECASE) for pattern in patterns)

    def _contains_temporal_markers(self, text: str) -> bool:
        """Check for temporal/historical claims."""
        patterns = [
            r'(since|from|until|between)\s+\d{4}',  # years
            r'(yesterday|today|last week|last month|last year)',  # recent time
            r'(during|after|before)\s+(the\s+)?\w+\s+(war|conflict|intifada)',  # historical events
            r'(in|on)\s+(19|20)\d{2}',  # specific years
            r'(first|second|third)\s+intifada',  # specific historical periods
        ]
        return any(re.search(pattern, text, re.IGNORECASE) for pattern in patterns)

    def _contains_causal_language(self, text: str) -> bool:
        """Check for causal claims."""
        causal_markers = [
            'because of',
            'due to',
            'caused by',
            'resulted in',
            'led to',
            'as a result of',
            'consequently',
            'therefore',
            'thus',
        ]
        return any(marker in text.lower() for marker in causal_markers)

    def _contains_quotes(self, text: str) -> bool:
        """Check for quotes and attributions."""
        quote_patterns = [
            r'"[^"]*"',  # quoted text
            r"'[^']*'",  # single quoted text
            r'\w+\s+said\s+',  # attribution
            r'according to\s+\w+',  # attribution
            r'\w+\s+stated\s+',  # statements
        ]
        return any(re.search(pattern, text, re.IGNORECASE) for pattern in quote_patterns)

    def _contains_palestine_conflict_claims(self, text: str) -> bool:
        """Check for Palestine/Israel conflict-specific claims."""
        text_lower = text.lower()

        # Check for any Palestine/Israel related keywords
        all_keywords = (
            self.palestine_keywords['locations']
            + self.palestine_keywords['organizations']
            + self.palestine_keywords['conflict_terms']
        )

        return any(keyword in text_lower for keyword in all_keywords)

    async def _create_claim_object(self, sentence: str, full_text: str) -> Claim:
        """Create a Claim object from a factual sentence."""
        claim_id = str(uuid.uuid4())

        # Determine claim type
        claim_type = self._classify_claim_type(sentence)

        # Extract entities and keywords
        entities = self._extract_entities(sentence)
        keywords = self._extract_keywords(sentence)

        # Determine confidence based on patterns
        confidence = self._calculate_extraction_confidence(sentence)

        # Extract location and temporal context
        location_context = self._extract_location_context(sentence)
        temporal_context = self._extract_temporal_context(sentence)

        return Claim(
            id=claim_id,
            text=sentence,
            claim_type=claim_type,
            confidence=confidence,
            context=full_text,
            extracted_entities=entities,
            keywords=keywords,
            location_context=location_context,
            temporal_context=temporal_context,
        )

    def _classify_claim_type(self, text: str) -> ClaimType:
        """Classify the type of claim based on content."""
        text_lower = text.lower()

        # Check for specific patterns
        if self._contains_statistics(text) and any(
            word in text_lower for word in ['killed', 'dead', 'casualties', 'injured']
        ):
            return ClaimType.CASUALTY
        elif self._contains_statistics(text):
            return ClaimType.STATISTICAL
        elif any(word in text_lower for word in ['said', 'stated', 'according', '"']):
            return ClaimType.QUOTE
        elif any(word in text_lower for word in ['war', 'conflict', 'intifada', '1948', '1967', 'oslo']):
            return ClaimType.HISTORICAL
        elif any(word in text_lower for word in ['settlement', 'territory', 'border', 'land']):
            return ClaimType.GEOGRAPHICAL
        elif any(word in text_lower for word in ['law', 'legal', 'court', 'resolution', 'violation']):
            return ClaimType.LEGAL
        elif any(word in text_lower for word in ['attack', 'strike', 'operation', 'military', 'idf', 'rocket']):
            return ClaimType.MILITARY
        elif any(word in text_lower for word in ['policy', 'government', 'decision', 'announce']):
            return ClaimType.POLICY
        elif any(word in text_lower for word in ['yesterday', 'today', 'occurred', 'happened']):
            return ClaimType.EVENT
        else:
            return ClaimType.EVENT  # Default fallback

    def _extract_entities(self, text: str) -> list[str]:
        """Extract named entities from text."""
        entities = []
        text_lower = text.lower()

        # Extract Palestine-related entities
        for category, keywords in self.palestine_keywords.items():
            for keyword in keywords:
                if keyword in text_lower:
                    entities.append(keyword.title())

        # Extract numbers
        numbers = re.findall(r'\d+(?:,\d{3})*(?:\.\d+)?', text)
        entities.extend(numbers)

        # Extract dates
        dates = re.findall(r'\b(?:19|20)\d{2}\b', text)
        entities.extend(dates)

        return list(set(entities))  # Remove duplicates

    def _extract_keywords(self, text: str) -> list[str]:
        """Extract key terms from the claim."""
        # Simple keyword extraction - could be enhanced with TF-IDF
        words = re.findall(r'\b\w{4,}\b', text.lower())

        # Filter out common words
        stop_words = {
            'that',
            'this',
            'with',
            'from',
            'they',
            'were',
            'been',
            'have',
            'will',
            'would',
            'could',
            'should',
            'there',
            'where',
            'when',
        }

        keywords = [word for word in words if word not in stop_words]
        return keywords[:10]  # Limit to top 10 keywords

    def _calculate_extraction_confidence(self, text: str) -> float:
        """Calculate confidence in claim extraction."""
        confidence = 0.5  # Base confidence

        # Increase confidence for specific patterns
        if self._contains_statistics(text):
            confidence += 0.2
        if self._contains_temporal_markers(text):
            confidence += 0.1
        if self._contains_quotes(text):
            confidence += 0.15
        if len(text.split()) > 5:  # Longer claims tend to be more substantial
            confidence += 0.05

        return min(confidence, 1.0)

    def _extract_location_context(self, text: str) -> str | None:
        """Extract geographical context from the claim."""
        text_lower = text.lower()

        for location in self.palestine_keywords['locations']:
            if location in text_lower:
                return location.title()

        return None

    def _extract_temporal_context(self, text: str) -> str | None:
        """Extract temporal context from the claim."""
        # Check for recent time references
        recent_patterns = [
            (r'\byesterday\b', 'recent'),
            (r'\btoday\b', 'current'),
            (r'\blast week\b', 'recent'),
            (r'\blast month\b', 'recent'),
            (r'\b(19|20)\d{2}\b', 'historical'),
            (r'\bsince \d{4}\b', 'ongoing'),
        ]

        for pattern, context in recent_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                return context

        return None

    def get_palestine_context(self, claims: list[Claim]) -> PalestineFactCheckContext:
        """Analyze claims for Palestine-specific context."""
        context = PalestineFactCheckContext()

        for claim in claims:
            text_lower = claim.text.lower()

            # Check for different types of content
            if any(word in text_lower for word in ['killed', 'dead', 'casualties', 'injured']):
                context.involves_casualties = True

            if any(word in text_lower for word in ['settlement', 'settler', 'colony']):
                context.involves_settlements = True

            if any(word in text_lower for word in ['international law', 'geneva', 'violation', 'war crime']):
                context.involves_international_law = True

            if any(word in text_lower for word in ['1948', '1967', 'nakba', 'oslo', 'camp david']):
                context.involves_historical_events = True

            if any(word in text_lower for word in ['territory', 'border', 'land', 'annexation']):
                context.involves_territory_claims = True

            if any(word in text_lower for word in ['human rights', 'torture', 'detention', 'discrimination']):
                context.involves_human_rights = True

            # Determine geographical scope
            if claim.location_context:
                if claim.location_context.lower() in ['gaza', 'rafah', 'khan younis']:
                    context.geographical_scope = 'gaza'
                elif claim.location_context.lower() in ['west bank', 'hebron', 'ramallah', 'bethlehem']:
                    context.geographical_scope = 'west_bank'
                elif claim.location_context.lower() in ['jerusalem', 'sheikh jarrah', 'silwan']:
                    context.geographical_scope = 'jerusalem'

            # Determine time period
            if claim.temporal_context:
                if claim.temporal_context in ['current', 'recent']:
                    context.time_period = 'current'
                elif claim.temporal_context == 'historical':
                    context.time_period = 'historical'
                elif claim.temporal_context == 'ongoing':
                    context.time_period = 'ongoing'

        return context
