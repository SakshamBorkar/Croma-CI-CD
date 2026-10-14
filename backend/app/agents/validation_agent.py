"""
app/agents/validation_agent.py
Validation Agent: Inspects citations, eliminates hallucinations, and calibrates confidence score.
"""
from typing import Dict, Any, List
from urllib.parse import urlparse
from app.agents.state import CIPipelineState, ValidationIssue, CompetitorInsight


def run_validation_agent(state: CIPipelineState) -> Dict[str, Any]:
    insights = state.get("raw_insights", [])
    kb_chunks = state.get("knowledge_base_chunks", [])
    web_findings = state.get("web_findings", [])

    valid_domains = set()
    for c in kb_chunks:
        url = c["metadata"].get("source_url", "")
        if url:
            valid_domains.add(urlparse(url).netloc or url)
    for w in web_findings:
        if w["url"]:
            valid_domains.add(urlparse(w["url"]).netloc or w["url"])

    validated_insights: List[CompetitorInsight] = []
    issues: List[ValidationIssue] = []

    for ins in insights:
        verified_citations = []
        comp = ins["competitor"]

        for cit in ins.get("citations", []):
            source = cit.get("source", "")
            source_domain = urlparse(source).netloc or source

            if any(vd in source or source in vd for vd in valid_domains) or len(source) < 30:
                verified_citations.append(cit)
            else:
                issues.append(ValidationIssue(
                    competitor=comp,
                    claim=cit.get("excerpt", ""),
                    reason=f"Citation not found in retrieved evidence: {source}",
                    passed=False,
                ))

        penalty = len(ins.get("citations", [])) - len(verified_citations)
        adjusted_score = max(0.0, ins["confidence_score"] - (penalty * 0.15))

        validated_insights.append(CompetitorInsight(
            competitor=comp,
            ci_dimension=ins["ci_dimension"],
            summary=ins["summary"],
            key_metrics=ins["key_metrics"],
            citations=verified_citations,
            confidence_score=round(adjusted_score, 2),
        ))

    return {
        "raw_insights": validated_insights,
        "validation_issues": issues,
        "current_agent": "validation_agent",
    }
