"""EU AI Act risk classification engine.

The engine is deterministic and rule-based: given the questionnaire answers it
walks the Act's decision order and returns a risk level plus the evidence that
led to it.

Decision order (Regulation (EU) 2024/1689):

1. Article 5   - prohibited practices, which override everything else.
2. Article 6(1) - AI as a safety component of a product covered by Annex I.
3. Article 6(2) + Annex III - the eight listed high-risk areas.
4. Article 6(3) - derogation for narrow, preparatory or purely procedural tasks.
5. Article 50  - transparency obligations => limited risk.
6. Otherwise   - minimal risk.
"""

from dataclasses import dataclass
from typing import Callable, List

from app.models.ai_system import RiskLevel
from app.schemas.ai_system import RiskClassificationRequest, RiskClassificationResponse
from app.services.requirements import requirements_for


@dataclass(frozen=True)
class Rule:
    """A single questionnaire flag mapped onto a provision of the Act."""

    field: str
    article: str
    label: str
    reason: str

    def triggered_by(self, data: RiskClassificationRequest) -> bool:
        return bool(getattr(data, self.field, False))


# --- Article 5: prohibited practices -------------------------------------- #

PROHIBITED_RULES: List[Rule] = [
    Rule(
        field="social_scoring",
        article="Article 5(1)(c)",
        label="Social scoring",
        reason=(
            "Evaluating or classifying people over time based on social "
            "behaviour or personal characteristics, leading to detrimental "
            "treatment, is a prohibited practice"
        ),
    ),
    Rule(
        field="subliminal_manipulation",
        article="Article 5(1)(a)",
        label="Subliminal or manipulative techniques",
        reason=(
            "Deploying subliminal, purposefully manipulative or deceptive "
            "techniques that materially distort behaviour and cause significant "
            "harm is prohibited"
        ),
    ),
    Rule(
        field="exploits_vulnerabilities",
        article="Article 5(1)(b)",
        label="Exploitation of vulnerabilities",
        reason=(
            "Exploiting vulnerabilities due to age, disability or a specific "
            "social or economic situation is prohibited"
        ),
    ),
    Rule(
        field="realtime_remote_biometric_id",
        article="Article 5(1)(h)",
        label="Real-time remote biometric identification in public spaces",
        reason=(
            "Real-time remote biometric identification in publicly accessible "
            "spaces for law enforcement is prohibited outside the narrow, "
            "judicially authorised exceptions"
        ),
    ),
    Rule(
        field="predictive_policing_profiling",
        article="Article 5(1)(d)",
        label="Predictive policing based on profiling",
        reason=(
            "Assessing the risk that a person commits a criminal offence based "
            "solely on profiling or personality traits is prohibited"
        ),
    ),
    Rule(
        field="untargeted_facial_scraping",
        article="Article 5(1)(e)",
        label="Untargeted scraping of facial images",
        reason=(
            "Building or expanding facial recognition databases through "
            "untargeted scraping of the internet or CCTV footage is prohibited"
        ),
    ),
    Rule(
        field="emotion_recognition_workplace",
        article="Article 5(1)(f)",
        label="Emotion inference in the workplace or education",
        reason=(
            "Inferring emotions of a natural person in the workplace or in "
            "education institutions is prohibited outside medical and safety "
            "purposes"
        ),
    ),
    Rule(
        field="biometric_categorization_sensitive",
        article="Article 5(1)(g)",
        label="Biometric categorisation of sensitive attributes",
        reason=(
            "Categorising people by biometric data to deduce race, political "
            "opinions, trade union membership, religious beliefs, sex life or "
            "sexual orientation is prohibited"
        ),
    ),
]


# --- Annex III: high-risk areas ------------------------------------------- #

ANNEX_III_RULES: List[Rule] = [
    Rule(
        field="uses_biometric_data",
        article="Annex III, point 1",
        label="Biometrics",
        reason=(
            "Remote biometric identification, biometric categorisation and "
            "emotion recognition systems fall under Annex III point 1"
        ),
    ),
    Rule(
        field="critical_infrastructure",
        article="Annex III, point 2",
        label="Critical infrastructure",
        reason=(
            "Safety components in the management and operation of critical "
            "digital infrastructure, traffic, water, gas, heating or "
            "electricity are high risk"
        ),
    ),
    Rule(
        field="education_access_or_evaluation",
        article="Annex III, point 3",
        label="Education and vocational training",
        reason=(
            "Determining access to education, evaluating learning outcomes or "
            "monitoring prohibited behaviour during tests is high risk"
        ),
    ),
    Rule(
        field="hr_recruitment_screening",
        article="Annex III, point 4(a)",
        label="Recruitment and candidate selection",
        reason=(
            "AI used to place targeted job adverts, filter applications or "
            "evaluate candidates is high risk under Annex III point 4(a)"
        ),
    ),
    Rule(
        field="hr_promotion_termination",
        article="Annex III, point 4(b)",
        label="Employment decisions and worker management",
        reason=(
            "AI influencing promotion, termination, task allocation or "
            "monitoring of worker performance is high risk under Annex III "
            "point 4(b)"
        ),
    ),
    Rule(
        field="essential_services_access",
        article="Annex III, point 5(a)",
        label="Access to essential public services",
        reason=(
            "Evaluating eligibility for essential public assistance benefits "
            "and services is high risk"
        ),
    ),
    Rule(
        field="credit_worthiness",
        article="Annex III, point 5(b)",
        label="Creditworthiness assessment",
        reason=(
            "Evaluating creditworthiness or establishing a credit score is high "
            "risk, except where used to detect financial fraud"
        ),
    ),
    Rule(
        field="insurance_risk_assessment",
        article="Annex III, point 5(c)",
        label="Life and health insurance pricing",
        reason=(
            "Risk assessment and pricing for life and health insurance is high "
            "risk under Annex III point 5(c)"
        ),
    ),
    Rule(
        field="law_enforcement",
        article="Annex III, point 6",
        label="Law enforcement",
        reason=(
            "Use by or on behalf of law enforcement authorities, including "
            "victim risk assessment and evidence reliability evaluation, is "
            "high risk"
        ),
    ),
    Rule(
        field="border_control",
        article="Annex III, point 7",
        label="Migration, asylum and border control",
        reason=(
            "Migration, asylum and border control management applications are "
            "high risk under Annex III point 7"
        ),
    ),
    Rule(
        field="justice_system",
        article="Annex III, point 8(a)",
        label="Administration of justice",
        reason=(
            "Assisting a judicial authority in researching and interpreting "
            "facts and the law is high risk"
        ),
    ),
    Rule(
        field="democratic_processes",
        article="Annex III, point 8(b)",
        label="Democratic processes",
        reason=(
            "Influencing the outcome of an election or referendum, or the "
            "voting behaviour of natural persons, is high risk"
        ),
    ),
]


# --- Article 50: transparency obligations --------------------------------- #

TRANSPARENCY_RULES: List[Rule] = [
    Rule(
        field="interacts_with_humans",
        article="Article 50(1)",
        label="Direct interaction with people",
        reason=(
            "The system interacts directly with natural persons, so they must "
            "be told they are dealing with an AI system"
        ),
    ),
    Rule(
        field="generates_synthetic_content",
        article="Article 50(2)",
        label="Synthetic content generation",
        reason=(
            "The system produces synthetic audio, image, video or text, which "
            "must be marked in a machine-readable format"
        ),
    ),
    Rule(
        field="emotion_recognition",
        article="Article 50(3)",
        label="Emotion recognition",
        reason=(
            "People exposed to an emotion recognition system must be informed "
            "that it is operating"
        ),
    ),
    Rule(
        field="biometric_categorization",
        article="Article 50(3)",
        label="Biometric categorisation",
        reason=(
            "People exposed to a biometric categorisation system must be "
            "informed that it is operating"
        ),
    ),
]


# Use-case categories that on their own point at an Annex III area. They are a
# weaker signal than the explicit checkboxes, so they only nudge confidence.
USE_CASE_ANNEX_HINTS = {
    "hr_recruitment": "Annex III, point 4",
    "credit_scoring": "Annex III, point 5(b)",
    "education": "Annex III, point 3",
    "law_enforcement": "Annex III, point 6",
    "insurance": "Annex III, point 5(c)",
}


NEXT_STEPS: dict = {
    RiskLevel.UNACCEPTABLE: [
        "Stop any EU rollout of the prohibited capability immediately",
        "Confirm the analysis with legal counsel and record the decision",
        "Scope a redesign that removes the prohibited practice",
        "Re-run the classification once the design has changed",
    ],
    RiskLevel.HIGH: [
        "Register the system and complete the compliance checklist",
        "Stand up a risk management system covering the whole lifecycle",
        "Document training data provenance and the bias examination",
        "Write the Annex IV technical documentation",
        "Define and test the human oversight measures",
        "Complete the Annex VI conformity assessment and sign the declaration",
        "Register the system in the EU database before going to market",
    ],
    RiskLevel.LIMITED: [
        "Add an AI disclosure to the first interaction with each user",
        "Mark generated content in a machine-readable format",
        "Document where and how each disclosure is presented",
        "Re-run the classification if the intended purpose changes",
    ],
    RiskLevel.MINIMAL: [
        "Record why the system falls outside Annex III",
        "Adopt a voluntary code of conduct if you sell to regulated buyers",
        "Set a calendar reminder to re-assess after major feature changes",
        "Give staff working with the system basic AI literacy training",
    ],
}


def _matched(rules: List[Rule], data: RiskClassificationRequest) -> List[Rule]:
    return [rule for rule in rules if rule.triggered_by(data)]


def _confidence(base: float, adjustments: List[Callable[[], float]]) -> float:
    value = base
    for adjust in adjustments:
        value += adjust()
    return round(min(max(value, 0.3), 0.99), 2)


def classify_risk(data: RiskClassificationRequest) -> RiskClassificationResponse:
    """Classify an AI system against the EU AI Act."""
    reasons: List[str] = []
    articles: List[str] = []
    annex_areas: List[str] = []

    # 1. Article 5 - prohibited practices trump every other consideration.
    prohibited = _matched(PROHIBITED_RULES, data)
    if prohibited:
        for rule in prohibited:
            reasons.append(f"{rule.reason} ({rule.article})")
            articles.append(rule.article)
        return _build_response(
            risk_level=RiskLevel.UNACCEPTABLE,
            confidence=0.95 if len(prohibited) == 1 else 0.98,
            reasons=reasons,
            articles=articles,
            annex_areas=[],
            data=data,
        )

    # 2. Article 6(1) - safety component of a product covered by Annex I.
    high_risk_reasons: List[str] = []
    if data.is_safety_component:
        high_risk_reasons.append(
            "The system is a safety component of a product covered by Union "
            "harmonisation legislation and requires third-party conformity "
            "assessment (Article 6(1))"
        )
        articles.append("Article 6(1)")

    # 3. Article 6(2) + Annex III.
    annex_matches = _matched(ANNEX_III_RULES, data)
    for rule in annex_matches:
        high_risk_reasons.append(f"{rule.reason} ({rule.article})")
        articles.append(rule.article)
        annex_areas.append(rule.label)

    if data.affects_fundamental_rights and not annex_matches:
        high_risk_reasons.append(
            "The system was reported to affect fundamental rights such as "
            "access to employment, education or essential services, which is "
            "the hallmark of the Annex III areas"
        )
        articles.append("Annex III")

    if high_risk_reasons:
        # 4. Article 6(3) - derogation for narrow procedural or preparatory
        #    tasks that do not materially influence the decision outcome.
        derogation = (
            data.purely_preparatory_task
            and data.human_reviews_every_decision
            and not data.is_safety_component
            and not data.uses_biometric_data
        )
        if derogation:
            reasons.append(
                "The Annex III area applies, but the system only performs a "
                "narrow preparatory task under meaningful human review, so the "
                "Article 6(3) derogation may remove it from the high-risk "
                "category. This must be documented and notified before market "
                "placement"
            )
            reasons.extend(high_risk_reasons)
            articles.append("Article 6(3)")
            level, transparency_reasons, transparency_articles = _transparency_level(data)
            reasons.extend(transparency_reasons)
            articles.extend(transparency_articles)
            return _build_response(
                risk_level=level,
                confidence=0.55,
                reasons=reasons,
                articles=articles,
                annex_areas=annex_areas,
                data=data,
            )

        reasons.extend(high_risk_reasons)
        if data.makes_automated_decisions:
            reasons.append(
                "Decisions are produced without meaningful human review, which "
                "raises the bar for the Article 14 human oversight measures"
            )
            articles.append("Article 14")

        # Article 50 duties stack on top of the high-risk regime.
        for rule in _matched(TRANSPARENCY_RULES, data):
            reasons.append(f"{rule.reason} ({rule.article})")
            articles.append(rule.article)

        hint = USE_CASE_ANNEX_HINTS.get(data.use_case_category)
        confidence = _confidence(
            0.80,
            [
                lambda: 0.10 if annex_matches else 0.0,
                lambda: 0.05 if len(annex_matches) > 1 else 0.0,
                lambda: 0.04 if hint else 0.0,
                lambda: -0.15 if not annex_matches and not data.is_safety_component else 0.0,
            ],
        )
        return _build_response(
            risk_level=RiskLevel.HIGH,
            confidence=confidence,
            reasons=reasons,
            articles=articles,
            annex_areas=annex_areas,
            data=data,
        )

    # 5. Article 50 - transparency obligations, or 6. minimal risk.
    level, transparency_reasons, transparency_articles = _transparency_level(data)
    reasons.extend(transparency_reasons)
    articles.extend(transparency_articles)
    confidence = 0.85 if level == RiskLevel.LIMITED else 0.75
    return _build_response(
        risk_level=level,
        confidence=confidence,
        reasons=reasons,
        articles=articles,
        annex_areas=annex_areas,
        data=data,
    )


def _transparency_level(data: RiskClassificationRequest):
    """Decide between limited and minimal risk from the Article 50 triggers."""
    matches = _matched(TRANSPARENCY_RULES, data)
    if matches:
        reasons = [f"{rule.reason} ({rule.article})" for rule in matches]
        articles = [rule.article for rule in matches]
        return RiskLevel.LIMITED, reasons, articles

    return (
        RiskLevel.MINIMAL,
        [
            "No prohibited practice, Annex III area or Article 50 transparency "
            "trigger was reported, so the system falls outside the regulated "
            "categories"
        ],
        [],
    )


def _build_response(
    risk_level: RiskLevel,
    confidence: float,
    reasons: List[str],
    articles: List[str],
    annex_areas: List[str],
    data: RiskClassificationRequest,
) -> RiskClassificationResponse:
    requirements = [
        requirement.label
        for requirement in requirements_for(risk_level, data.is_general_purpose_model)
    ]

    next_steps = list(NEXT_STEPS[risk_level])
    if data.is_general_purpose_model and risk_level != RiskLevel.UNACCEPTABLE:
        next_steps.append(
            "Publish the Article 53 training content summary and copyright policy"
        )

    return RiskClassificationResponse(
        risk_level=risk_level,
        confidence=confidence,
        reasons=_dedupe(reasons),
        requirements=requirements,
        next_steps=next_steps,
        applicable_articles=_dedupe(articles),
        annex_iii_areas=_dedupe(annex_areas),
        prohibited=risk_level == RiskLevel.UNACCEPTABLE,
    )


def _dedupe(values: List[str]) -> List[str]:
    """Preserve order while removing repeats."""
    seen = set()
    result = []
    for value in values:
        if value not in seen:
            seen.add(value)
            result.append(value)
    return result
