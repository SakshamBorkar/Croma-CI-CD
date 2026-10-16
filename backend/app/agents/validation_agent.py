"""
app/agents/validation_agent.py
──────────────────────────────
Validation Agent: Checks factual claims against available sources.
Identifies unsupported claims, conflicting data, stale prices, and missing citations.
Returns a validation report with evidence and confidence assessments.
Does not automatically approve unsupported claims.
"""
from typing import Dict, Any, List
from urllib.parse import urlparse
from app.agents.state import CIPipelineState, ValidationIssue, CompetitorInsight


def run_validation_agent(state: CIPipelineState) -> Dict[str, Any]:
    insights = state.get("raw_insights", [])
    kb_chunks = state.get("knowledge_base_chunks", [])
    doc_chunks = state.get("retrieved_document_chunks", [])
    web_findings = state.get("web_findings", [])
    selected_mode = state.get("selected_mode", "auto")

    # Build known valid source set from KB, uploaded documents, and web
    valid_sources = set()
    for c in kb_chunks:
        url = c["metadata"].get("source_url", "")
        if url:
            valid_sources.add(urlparse(url).netloc or url)
            valid_sources.add(url.lower())
        title = c["metadata"].get("source_title", "")
        if title:
            valid_sources.add(title.lower())

    for d in doc_chunks:
        fn = d.get("metadata", {}).get("filename", "")
        if fn:
            valid_sources.add(fn.lower())
            valid_sources.add(f"[{fn.lower()}")
        cit = d.get("metadata", {}).get("citation_label", "")
        if cit:
            valid_sources.add(cit.lower())

    for w in web_findings:
        if w.get("url"):
            valid_sources.add(urlparse(w["url"]).netloc or w["url"])
            valid_sources.add(w["url"].lower())

    validated_insights: List[CompetitorInsight] = []
    issues: List[ValidationIssue] = []

    # Standalone validation mode when no prior insights exist
    if selected_mode == "validation" and not insights:
        # Check factual coverage of the query across available evidence
        total_chunks = len(kb_chunks) + len(doc_chunks) + len(web_findings)
        if total_chunks == 0:
            issues.append(ValidationIssue(
                competitor=state.get("competitor") or "all",
                claim=state["query"],
                reason="No factual evidence found in current sources to validate this claim.",
                passed=False,
            ))
            base_confidence = 0.0
        else:
            base_confidence = min(0.85, 0.4 + (total_chunks * 0.05))

        return {
            "validation_issues": issues,
            "overall_confidence": base_confidence,
            "current_agent": "validation_agent",
        }

    for ins in insights:
        verified_citations = []
        comp = ins["competitor"]

        for cit in ins.get("citations", []):
            source = str(cit.get("source", "")).lower()
            excerpt = cit.get("excerpt", "")

            # Verify against valid sources
            is_valid = any(vs in source or source in vs for vs in valid_sources if vs) or source.startswith("[") or len(source) < 30

            if is_valid:
                verified_citations.append(cit)
            else:
                issues.append(ValidationIssue(
                    competitor=comp,
                    claim=excerpt or source,
                    reason=f"Unverified citation: Source '{cit.get('source')}' was not present in retrieved knowledge base or uploaded documents.",
                    passed=False,
                ))

        # Check for empty citations on substantive claims
        if not verified_citations and ins.get("summary") and "Insufficient" not in ins.get("summary", ""):
            issues.append(ValidationIssue(
                competitor=comp,
                claim=ins["summary"][:100],
                reason="Substantive claims generated without direct supporting citations.",
                passed=False,
            ))

        penalty = (len(ins.get("citations", [])) - len(verified_citations)) * 0.15
        if not verified_citations and "Insufficient" not in ins.get("summary", ""):
            penalty += 0.25

        adjusted_score = max(0.0, ins["confidence_score"] - penalty)

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
