"""The EU AI Act requirement catalogue.

This is the single source of truth for "what does an AI system at risk level X
actually have to do". Both the classification engine (which reports the
obligations attached to a verdict) and the compliance checklist (which tracks
them per system) read from here.

Article numbering follows Regulation (EU) 2024/1689.
"""

from dataclasses import dataclass
from typing import Dict, List

from app.models.ai_system import RiskLevel
from app.models.compliance import RequirementCategory


@dataclass(frozen=True)
class Requirement:
    """A single obligation, keyed by a stable ``code``."""

    code: str
    article: str
    title: str
    description: str
    category: RequirementCategory

    @property
    def label(self) -> str:
        return f"{self.title} ({self.article})"


UNACCEPTABLE_RISK_REQUIREMENTS: List[Requirement] = [
    Requirement(
        code="art5_cease_placing",
        article="Article 5",
        title="Cease placing the system on the EU market",
        description=(
            "Practices listed in Article 5 are prohibited outright. The system "
            "may not be placed on the market, put into service or used in the EU "
            "in its current form."
        ),
        category=RequirementCategory.GOVERNANCE,
    ),
    Requirement(
        code="art5_redesign",
        article="Article 5",
        title="Redesign or withdraw the prohibited functionality",
        description=(
            "Remove the prohibited capability, or restrict the system to a use "
            "that falls outside Article 5, then re-run the classification."
        ),
        category=RequirementCategory.GOVERNANCE,
    ),
    Requirement(
        code="art5_legal_review",
        article="Article 5",
        title="Obtain a legal review before any further deployment",
        description=(
            "Penalties for prohibited practices reach EUR 35 000 000 or 7% of "
            "worldwide annual turnover. Have counsel confirm the analysis and "
            "document the outcome."
        ),
        category=RequirementCategory.GOVERNANCE,
    ),
]


HIGH_RISK_REQUIREMENTS: List[Requirement] = [
    Requirement(
        code="art4_ai_literacy",
        article="Article 4",
        title="Ensure a sufficient level of AI literacy",
        description=(
            "Applies at every risk level: staff operating or overseeing the "
            "system need AI literacy adequate for their role and context."
        ),
        category=RequirementCategory.GOVERNANCE,
    ),
    Requirement(
        code="art9_risk_management",
        article="Article 9",
        title="Establish a risk management system",
        description=(
            "Run a continuous, iterative process across the full lifecycle: "
            "identify foreseeable risks to health, safety and fundamental "
            "rights, estimate them, evaluate post-market data, and adopt "
            "targeted mitigation measures."
        ),
        category=RequirementCategory.RISK_MANAGEMENT,
    ),
    Requirement(
        code="art10_data_governance",
        article="Article 10",
        title="Apply data and data governance practices",
        description=(
            "Training, validation and testing data must be relevant, "
            "sufficiently representative and as far as possible free of errors. "
            "Document collection, provenance, preparation, assumptions and the "
            "examination for possible biases."
        ),
        category=RequirementCategory.DATA_GOVERNANCE,
    ),
    Requirement(
        code="art11_technical_documentation",
        article="Article 11",
        title="Draw up technical documentation",
        description=(
            "Produce Annex IV documentation before the system is placed on the "
            "market and keep it up to date: general description, design "
            "specification, monitoring and control, performance metrics and the "
            "risk management system."
        ),
        category=RequirementCategory.DOCUMENTATION,
    ),
    Requirement(
        code="art12_record_keeping",
        article="Article 12",
        title="Enable automatic logging of events",
        description=(
            "The system must technically allow automatic recording of events "
            "over its lifetime, at a level of traceability appropriate to its "
            "intended purpose."
        ),
        category=RequirementCategory.RECORD_KEEPING,
    ),
    Requirement(
        code="art13_transparency",
        article="Article 13",
        title="Provide instructions for use to deployers",
        description=(
            "Deployers must be able to interpret the output and use it "
            "appropriately: provide capabilities and limitations, expected "
            "accuracy, known risks, human oversight measures and expected "
            "lifetime."
        ),
        category=RequirementCategory.TRANSPARENCY,
    ),
    Requirement(
        code="art14_human_oversight",
        article="Article 14",
        title="Design effective human oversight",
        description=(
            "Build in measures that let a natural person understand the "
            "system's capacity and limits, stay aware of automation bias, "
            "correctly interpret output, disregard it, and stop the system."
        ),
        category=RequirementCategory.HUMAN_OVERSIGHT,
    ),
    Requirement(
        code="art15_accuracy_robustness",
        article="Article 15",
        title="Ensure accuracy, robustness and cybersecurity",
        description=(
            "Achieve an appropriate level of accuracy and declare the metrics "
            "in the instructions for use. Be resilient to errors, faults and "
            "attempts to alter the system's use or performance, including data "
            "poisoning and adversarial examples."
        ),
        category=RequirementCategory.ROBUSTNESS,
    ),
    Requirement(
        code="art17_quality_management",
        article="Article 17",
        title="Operate a quality management system",
        description=(
            "Document a strategy for regulatory compliance, design control, "
            "testing, data management, post-market monitoring, incident "
            "reporting and an accountability framework."
        ),
        category=RequirementCategory.GOVERNANCE,
    ),
    Requirement(
        code="art43_conformity_assessment",
        article="Article 43",
        title="Complete the conformity assessment",
        description=(
            "Most Annex III systems use the internal control procedure of "
            "Annex VI. Verify the quality management system, review the "
            "technical documentation and confirm design consistency."
        ),
        category=RequirementCategory.DOCUMENTATION,
    ),
    Requirement(
        code="art47_declaration_of_conformity",
        article="Article 47",
        title="Draw up the EU declaration of conformity",
        description=(
            "Sign a written, machine-readable declaration per system, keep it "
            "for 10 years after the system is placed on the market, and affix "
            "the CE marking under Article 48."
        ),
        category=RequirementCategory.DOCUMENTATION,
    ),
    Requirement(
        code="art49_registration",
        article="Article 49",
        title="Register the system in the EU database",
        description=(
            "Providers of Annex III high-risk systems must register themselves "
            "and the system in the EU database before placing it on the market."
        ),
        category=RequirementCategory.REGISTRATION,
    ),
    Requirement(
        code="art72_post_market_monitoring",
        article="Article 72",
        title="Run post-market monitoring",
        description=(
            "Collect and analyse performance data from deployers throughout the "
            "system's lifetime against a documented monitoring plan."
        ),
        category=RequirementCategory.RISK_MANAGEMENT,
    ),
    Requirement(
        code="art73_incident_reporting",
        article="Article 73",
        title="Report serious incidents",
        description=(
            "Report serious incidents to the market surveillance authority of "
            "the Member State where they occurred, immediately and no later "
            "than 15 days after becoming aware of them."
        ),
        category=RequirementCategory.RECORD_KEEPING,
    ),
]


LIMITED_RISK_REQUIREMENTS: List[Requirement] = [
    Requirement(
        code="art50_disclose_ai_interaction",
        article="Article 50(1)",
        title="Tell people they are interacting with an AI system",
        description=(
            "Inform natural persons that they are interacting with an AI "
            "system, unless it is obvious to a reasonably well-informed person. "
            "The disclosure must be given at the first interaction."
        ),
        category=RequirementCategory.TRANSPARENCY,
    ),
    Requirement(
        code="art50_mark_synthetic_content",
        article="Article 50(2)",
        title="Machine-readably mark synthetic content",
        description=(
            "Outputs that are synthetic audio, image, video or text must be "
            "marked in a machine-readable format and detectable as artificially "
            "generated or manipulated."
        ),
        category=RequirementCategory.TRANSPARENCY,
    ),
    Requirement(
        code="art50_emotion_biometric_notice",
        article="Article 50(3)",
        title="Notify people subject to emotion or biometric analysis",
        description=(
            "Inform the exposed natural persons that an emotion recognition or "
            "biometric categorisation system is operating, and process their "
            "personal data in line with the GDPR."
        ),
        category=RequirementCategory.TRANSPARENCY,
    ),
    Requirement(
        code="art50_deepfake_labelling",
        article="Article 50(4)",
        title="Label deep fakes and AI-generated public-interest text",
        description=(
            "Deployers must disclose that content has been artificially "
            "generated or manipulated where it depicts real people, places or "
            "events, or informs the public on matters of public interest."
        ),
        category=RequirementCategory.TRANSPARENCY,
    ),
    Requirement(
        code="art4_ai_literacy",
        article="Article 4",
        title="Ensure a sufficient level of AI literacy",
        description=(
            "Providers and deployers must take measures to ensure staff dealing "
            "with the system have adequate AI literacy for their role and "
            "context."
        ),
        category=RequirementCategory.GOVERNANCE,
    ),
]


MINIMAL_RISK_REQUIREMENTS: List[Requirement] = [
    Requirement(
        code="art4_ai_literacy",
        article="Article 4",
        title="Ensure a sufficient level of AI literacy",
        description=(
            "Applies regardless of risk level: staff operating or using the "
            "system need adequate AI literacy for their role and context."
        ),
        category=RequirementCategory.GOVERNANCE,
    ),
    Requirement(
        code="art95_code_of_conduct",
        article="Article 95",
        title="Consider a voluntary code of conduct",
        description=(
            "Voluntarily applying the high-risk requirements (or parts of them) "
            "is encouraged and is a credible signal to enterprise buyers."
        ),
        category=RequirementCategory.GOVERNANCE,
    ),
    Requirement(
        code="internal_reclassification_watch",
        article="Article 6",
        title="Re-run classification when the intended purpose changes",
        description=(
            "A change of intended purpose, or a substantial modification, can "
            "move a minimal-risk system into the high-risk category."
        ),
        category=RequirementCategory.RISK_MANAGEMENT,
    ),
]


# Obligations attached to general-purpose AI models (Chapter V). These are
# additive: they apply on top of whatever risk level the system lands in.
GPAI_REQUIREMENTS: List[Requirement] = [
    Requirement(
        code="art53_gpai_documentation",
        article="Article 53",
        title="Maintain general-purpose model documentation",
        description=(
            "Keep technical documentation of the model (training and testing "
            "process, evaluation results) and make information available to "
            "downstream providers who integrate the model."
        ),
        category=RequirementCategory.DOCUMENTATION,
    ),
    Requirement(
        code="art53_training_data_summary",
        article="Article 53(1)(d)",
        title="Publish a summary of training content",
        description=(
            "Draw up and make publicly available a sufficiently detailed "
            "summary of the content used to train the model, following the AI "
            "Office template."
        ),
        category=RequirementCategory.TRANSPARENCY,
    ),
    Requirement(
        code="art53_copyright_policy",
        article="Article 53(1)(c)",
        title="Put a copyright policy in place",
        description=(
            "Adopt a policy to comply with Union copyright law, including "
            "identifying and respecting reservations of rights under the text "
            "and data mining exception."
        ),
        category=RequirementCategory.GOVERNANCE,
    ),
]


REQUIREMENTS_BY_RISK: Dict[RiskLevel, List[Requirement]] = {
    RiskLevel.UNACCEPTABLE: UNACCEPTABLE_RISK_REQUIREMENTS,
    RiskLevel.HIGH: HIGH_RISK_REQUIREMENTS,
    RiskLevel.LIMITED: LIMITED_RISK_REQUIREMENTS,
    RiskLevel.MINIMAL: MINIMAL_RISK_REQUIREMENTS,
}


def requirements_for(
    risk_level: RiskLevel,
    is_general_purpose_model: bool = False,
) -> List[Requirement]:
    """Return the obligations that apply at ``risk_level``.

    High-risk systems inherit the Article 50 transparency duties too whenever
    they also interact with people, but that pairing is decided by the caller;
    what is unconditional here is the Chapter V add-on for GPAI models.
    """
    requirements = list(REQUIREMENTS_BY_RISK.get(risk_level, MINIMAL_RISK_REQUIREMENTS))
    if is_general_purpose_model and risk_level != RiskLevel.UNACCEPTABLE:
        known = {req.code for req in requirements}
        requirements.extend(req for req in GPAI_REQUIREMENTS if req.code not in known)
    return requirements


def requirement_by_code(code: str) -> Requirement:
    """Look up a requirement across every catalogue."""
    for group in (
        UNACCEPTABLE_RISK_REQUIREMENTS,
        HIGH_RISK_REQUIREMENTS,
        LIMITED_RISK_REQUIREMENTS,
        MINIMAL_RISK_REQUIREMENTS,
        GPAI_REQUIREMENTS,
    ):
        for requirement in group:
            if requirement.code == code:
                return requirement
    raise KeyError(f"Unknown requirement code: {code}")
