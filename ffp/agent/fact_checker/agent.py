"""
Fact-checking agent for Palestine-related posts using Claude Code SDK.
"""

import time
import uuid
from typing import Optional

from claude_code_sdk import ClaudeCodeOptions, query

from .claim_extractor import ClaimExtractor
from .database import FactCheckDatabase
from .models import Claim, ClaimType, ConfidenceLevel, FactCheckVerdict, PalestineFactCheckContext, PostAnalysis
from .tools import VerificationOrchestrator


class PalestineFactCheckAgent:
    """Main fact-checking agent for Palestine/Israel conflict-related posts."""

    def __init__(self, api_key: Optional[str] = None, db_path: str = 'fact_check.db'):
        self.claim_extractor = ClaimExtractor()
        self.verifier = VerificationOrchestrator(api_key)
        self.database = FactCheckDatabase(db_path)

        # Claude Code SDK options with specialized Palestine fact-checking prompt
        self.claude_options = ClaudeCodeOptions(
            system_prompt=self._get_fact_check_prompt(), permission_mode='acceptEdits', cwd='.'
        )

    def _get_fact_check_prompt(self) -> str:
        """Get the specialized fact-checking prompt for Palestine/Israel content."""
        return """You are a specialized fact-checking agent focused on verifying claims about the Palestine-Israel conflict. Your role is to:

1. **Analyze Evidence Objectively**: Evaluate all sources without bias, considering multiple perspectives while prioritizing factual accuracy.

2. **Verify Statistical Claims**: Cross-reference casualty figures, displacement numbers, and demographic data with:
   - UN OCHA (Office for the Coordination of Humanitarian Affairs)
   - WHO (World Health Organization)
   - UNRWA (UN Relief and Works Agency)
   - Credible international NGOs (Human Rights Watch, Amnesty International, B'Tselem)
   - Official government sources when appropriate

3. **Historical Context Verification**: For historical claims, consult:
   - Academic sources and peer-reviewed research
   - Official UN resolutions and documentation
   - Multiple historical archives and testimonies
   - International court decisions (ICJ, ICC)

4. **Legal Claims Assessment**: For international law references:
   - Geneva Conventions and their interpretations
   - UN Security Council resolutions
   - International Court of Justice rulings
   - Expert legal analysis from international law scholars

5. **Source Credibility Evaluation**: Consider the following factors:
   - Source methodology and transparency
   - Historical accuracy record
   - Potential bias and conflicts of interest
   - Verification by independent sources
   - Proximity to events (primary vs secondary sources)

6. **Sensitive Content Guidelines**:
   - Acknowledge the complexity and sensitivity of the conflict
   - Avoid inflammatory language while maintaining factual accuracy
   - Distinguish between verified facts and disputed claims
   - Highlight when claims require additional context
   - Flag content that may be propaganda or deliberately misleading

7. **Verdict Categories**:
   - TRUE: Verified by multiple credible sources
   - FALSE: Contradicted by reliable evidence
   - PARTIALLY_TRUE: Contains some accurate elements but misleading overall
   - DISPUTED: Sources contradict each other significantly
   - UNVERIFIABLE: Insufficient evidence available
   - MISLEADING: Technically accurate but lacks crucial context

8. **Special Considerations for Palestine/Israel Content**:
   - Casualty figures: Verify methodology and source reliability
   - Settlement activity: Cross-reference with UN monitoring reports
   - Military operations: Distinguish between official statements and verified facts
   - Human rights violations: Require documentation from credible monitoring organizations
   - Legal status claims: Reference international law and court decisions
   - Historical events: Verify with multiple academic and archival sources

9. **Red Flags to Watch For**:
   - Unverified social media videos or images
   - Emotional language designed to inflame rather than inform
   - Claims without specific dates, locations, or sources
   - Statistics without methodology or source attribution
   - One-sided narratives that ignore complexity
   - Conspiracy theories or antisemitic/islamophobic content

10. **Output Requirements**:
    - Provide clear, evidence-based verdicts
    - Cite specific sources for verification
    - Explain limitations in available evidence
    - Suggest additional context when helpful
    - Maintain professional, neutral tone
    - Be transparent about confidence levels

Remember: Your goal is to provide accurate, nuanced fact-checking that helps readers understand the factual basis of claims while acknowledging the complexity of this conflict. Prioritize truth and evidence over any particular political narrative."""

    async def setup(self):
        """Initialize the fact-checking agent."""
        await self.database.setup_database()

    async def analyze_post(self, post_text: str, post_url: Optional[str] = None) -> PostAnalysis:
        """Analyze a complete social media post for factual claims."""
        start_time = time.time()

        # Generate unique post ID
        post_id = str(uuid.uuid4())

        # Extract claims from the post
        claims = await self.claim_extractor.extract_claims(post_text)

        if not claims:
            # No factual claims found
            return PostAnalysis(
                post_id=post_id,
                post_url=post_url,
                post_text=post_text,
                claims=[],
                verdicts=[],
                overall_credibility=ConfidenceLevel.HIGH,
                topic_sensitivity='normal',
            )

        # Get Palestine-specific context
        palestine_context = self.claim_extractor.get_palestine_context(claims)

        # Verify each claim
        verdicts = []
        for claim in claims:
            verdict = await self._verify_claim_with_claude(claim, palestine_context)
            verdicts.append(verdict)

        # Calculate overall credibility and determine flags
        overall_credibility = self._calculate_overall_credibility(verdicts)
        warning_flags = self._generate_warning_flags(claims, verdicts, palestine_context)

        # Determine if human review is needed
        requires_review = self._requires_human_review(verdicts, palestine_context)

        # Determine topic sensitivity
        topic_sensitivity = self._assess_topic_sensitivity(palestine_context)

        analysis = PostAnalysis(
            post_id=post_id,
            post_url=post_url,
            post_text=post_text,
            claims=claims,
            verdicts=verdicts,
            overall_credibility=overall_credibility,
            potential_misinformation=any(v.verdict in ['FALSE', 'MISLEADING'] for v in verdicts),
            requires_human_review=requires_review,
            topic_sensitivity=topic_sensitivity,
            warning_flags=warning_flags,
        )

        # Store analysis in database
        await self.database.store_post_analysis(analysis)

        processing_time = time.time() - start_time
        print(f'Fact-check completed in {processing_time:.2f} seconds')

        return analysis

    async def _verify_claim_with_claude(self, claim: Claim, context: PalestineFactCheckContext) -> FactCheckVerdict:
        """Verify a single claim using Claude and external sources."""

        # Check database cache first
        cached_verdict = await self.database.lookup_claim(claim.text)
        if cached_verdict and cached_verdict.confidence in [ConfidenceLevel.HIGH, ConfidenceLevel.MEDIUM]:
            return cached_verdict

        # Gather evidence from external sources
        evidence = await self.verifier.verify_claim(claim.text, claim.claim_type.value)

        # Prepare context for Claude
        context_info = self._format_context_for_claude(claim, context, evidence)

        # Query Claude for fact-checking analysis
        prompt = f"""Fact-check this claim: "{claim.text}"

Context: {context_info}

Evidence found: {self._format_evidence_for_claude(evidence)}

Please provide a structured fact-check verdict with:
1. Verdict (TRUE/FALSE/PARTIALLY_TRUE/DISPUTED/UNVERIFIABLE/MISLEADING)
2. Confidence level (HIGH/MEDIUM/LOW/INSUFFICIENT)
3. Detailed explanation (minimum 100 words)
4. Evidence summary
5. Any limitations in verification
6. Additional context needed (if any)

Format your response as JSON with these exact keys: verdict, confidence, explanation, evidence_summary, limitations, context_needed"""

        try:
            response_text = ''
            async for message in query(prompt=prompt, options=self.claude_options):
                response_text += str(message)

            # Parse Claude's response and create verdict
            verdict = self._parse_claude_response(response_text, claim, evidence)

            # Store in database for future reference
            await self.database.store_verification(verdict)

            return verdict

        except Exception as e:
            # Fallback verdict if Claude fails
            return FactCheckVerdict(
                claim_id=claim.id,
                verdict='UNVERIFIABLE',
                confidence=ConfidenceLevel.INSUFFICIENT,
                explanation=f'Unable to verify claim due to technical error: {str(e)}',
                evidence_summary='No evidence could be gathered',
                sources_consulted=[],
                sensitive_topic=self._is_sensitive_claim(claim, context),
            )

    def _format_context_for_claude(self, claim: Claim, context: PalestineFactCheckContext, evidence) -> str:
        """Format context information for Claude analysis."""
        context_parts = []

        if claim.location_context:
            context_parts.append(f'Location: {claim.location_context}')

        if claim.temporal_context:
            context_parts.append(f'Time period: {claim.temporal_context}')

        if context.involves_casualties:
            context_parts.append('Involves casualty figures')

        if context.involves_settlements:
            context_parts.append('Involves settlement activity')

        if context.involves_international_law:
            context_parts.append('Involves international law')

        if context.geographical_scope:
            context_parts.append(f'Geographic scope: {context.geographical_scope}')

        return '; '.join(context_parts) if context_parts else 'General Palestine/Israel conflict context'

    def _format_evidence_for_claude(self, evidence) -> str:
        """Format evidence sources for Claude analysis."""
        if not evidence.sources:
            return 'No external sources found'

        source_summaries = []
        for source in evidence.sources[:10]:  # Limit to top 10 sources
            summary = (
                f'- {source.domain} (credibility: {source.credibility_score:.2f}): {source.relevant_excerpt[:200]}'
            )
            source_summaries.append(summary)

        return '\n'.join(source_summaries)

    def _parse_claude_response(self, response: str, claim: Claim, evidence) -> FactCheckVerdict:
        """Parse Claude's response into a structured verdict."""
        import json
        import re

        try:
            # Try to extract JSON from response
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group())

                return FactCheckVerdict(
                    claim_id=claim.id,
                    verdict=data.get('verdict', 'UNVERIFIABLE'),
                    confidence=ConfidenceLevel(data.get('confidence', 'insufficient').lower()),
                    explanation=data.get('explanation', 'No explanation provided'),
                    evidence_summary=data.get('evidence_summary', 'No evidence summary'),
                    sources_consulted=[s.url for s in evidence.sources],
                    limitations=data.get('limitations'),
                    context_needed=data.get('context_needed'),
                    sensitive_topic=self._is_sensitive_claim(claim, None),
                )
        except Exception:
            pass

        # Fallback parsing if JSON fails
        lines = response.split('\n')
        verdict = 'UNVERIFIABLE'
        confidence = ConfidenceLevel.INSUFFICIENT
        explanation = response[:500]  # Take first 500 chars as explanation

        # Try to extract verdict from text
        for line in lines:
            if 'verdict:' in line.lower():
                verdict_match = re.search(
                    r'(TRUE|FALSE|PARTIALLY_TRUE|DISPUTED|UNVERIFIABLE|MISLEADING)', line, re.IGNORECASE
                )
                if verdict_match:
                    verdict = verdict_match.group().upper()
            elif 'confidence:' in line.lower():
                conf_match = re.search(r'(HIGH|MEDIUM|LOW|INSUFFICIENT)', line, re.IGNORECASE)
                if conf_match:
                    confidence = ConfidenceLevel(conf_match.group().lower())

        return FactCheckVerdict(
            claim_id=claim.id,
            verdict=verdict,
            confidence=confidence,
            explanation=explanation,
            evidence_summary=f'Found {len(evidence.sources)} sources',
            sources_consulted=[s.url for s in evidence.sources],
            sensitive_topic=self._is_sensitive_claim(claim, None),
        )

    def _calculate_overall_credibility(self, verdicts: list[FactCheckVerdict]) -> ConfidenceLevel:
        """Calculate overall credibility based on individual verdicts."""
        if not verdicts:
            return ConfidenceLevel.HIGH

        false_count = sum(1 for v in verdicts if v.verdict in ['FALSE', 'MISLEADING'])
        disputed_count = sum(1 for v in verdicts if v.verdict in ['DISPUTED', 'UNVERIFIABLE'])

        total_verdicts = len(verdicts)

        if false_count / total_verdicts > 0.5:
            return ConfidenceLevel.LOW
        elif (false_count + disputed_count) / total_verdicts > 0.3:
            return ConfidenceLevel.MEDIUM
        else:
            return ConfidenceLevel.HIGH

    def _generate_warning_flags(
        self, claims: list[Claim], verdicts: list[FactCheckVerdict], context: PalestineFactCheckContext
    ) -> list[str]:
        """Generate warning flags for the post."""
        flags = []

        if any(v.verdict == 'FALSE' for v in verdicts):
            flags.append('Contains false information')

        if any(v.verdict == 'MISLEADING' for v in verdicts):
            flags.append('Contains misleading claims')

        if context.involves_casualties and any(c.claim_type == ClaimType.CASUALTY for c in claims):
            flags.append('Contains casualty figures - verify with official sources')

        if len([v for v in verdicts if v.verdict == 'DISPUTED']) > 1:
            flags.append('Multiple disputed claims')

        if any(v.confidence == ConfidenceLevel.INSUFFICIENT for v in verdicts):
            flags.append('Some claims could not be verified')

        return flags

    def _requires_human_review(self, verdicts: list[FactCheckVerdict], context: PalestineFactCheckContext) -> bool:
        """Determine if human review is required."""
        # Require review for sensitive or complex cases
        if context.involves_human_rights or context.involves_international_law:
            return True

        if any(v.verdict in ['DISPUTED', 'MISLEADING'] for v in verdicts):
            return True

        if len([v for v in verdicts if v.confidence == ConfidenceLevel.INSUFFICIENT]) > 2:
            return True

        return False

    def _assess_topic_sensitivity(self, context: PalestineFactCheckContext) -> str:
        """Assess the sensitivity level of the topic."""
        if context.involves_casualties or context.involves_human_rights:
            return 'highly_sensitive'
        elif context.involves_settlements or context.involves_international_law:
            return 'sensitive'
        else:
            return 'normal'

    def _is_sensitive_claim(self, claim: Claim, context: Optional[PalestineFactCheckContext]) -> bool:
        """Determine if a claim involves sensitive topics."""
        sensitive_keywords = [
            'killed',
            'dead',
            'murdered',
            'massacre',
            'genocide',
            'ethnic cleansing',
            'war crime',
            'torture',
            'children',
            'civilians',
            'hospital',
            'school',
        ]

        return any(keyword in claim.text.lower() for keyword in sensitive_keywords)

    async def get_analysis_summary(self, days: int = 7) -> dict:
        """Get a summary of recent fact-checking activity."""
        history = await self.database.get_analysis_history(days)
        cache_stats = await self.database.get_cache_statistics()
        trending = await self.database.get_trending_claims(days)

        return {
            'recent_analyses': len(history),
            'high_credibility_posts': len([h for h in history if h['overall_credibility'] == 'high']),
            'potential_misinformation': len([h for h in history if h['potential_misinformation']]),
            'sensitive_topics': len([h for h in history if h['topic_sensitivity'] != 'normal']),
            'cache_statistics': cache_stats,
            'trending_claims': trending[:5],  # Top 5 trending claims
        }
