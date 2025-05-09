# Experiment Configuration
NUM_CASES_PER_PARTICIPANT = 2  # or 3
TOTAL_BONUS_PER_CASE = 10.00   # €10 bonus "pot" per case
FACT_CHECK_COST_RATE = 0.50    # 50% of current endowment if fact-check chosen

# Cases with high and low stakes text
CASES = [
    {
        "id": 1,
        "text_high": "A major tech company is considering acquiring your startup for €50 million. They've offered favorable terms, but you've heard rumors about their aggressive acquisition strategy.",
        "text_low": "A small tech company is considering acquiring your startup for €500,000. They've offered favorable terms, but you've heard rumors about their aggressive acquisition strategy.",
        "correctAction": "pursue",
        "opponent_variants": [
            "Sie erfahren, dass das Start Up auf Grund der finanziellen Schwierigkeiten sich nicht anwaltlich vertreten lässt und bloß auf Informationen von ChatGPT zugreift.",
            "Sie erfahren, dass das Start Up anwaltlich vertreten ist."
        ]
    },
    {
        "id": 2,
        "text_high": "You've been offered a €1 million investment in your AI startup from a prominent venture capital firm. However, they're known for taking large equity stakes.",
        "text_low": "You've been offered a €10,000 investment in your AI startup from a small investment group. However, they're known for taking large equity stakes.",
        "correctAction": "drop",
        "opponent_variants": [
            "Sie erfahren, dass das Start Up auf Grund der finanziellen Schwierigkeiten sich nicht anwaltlich vertreten lässt und bloß auf Informationen von ChatGPT zugreift.",
            "Sie erfahren, dass das Start Up anwaltlich vertreten ist."
        ]
    },
    {
        "id": 3,
        "text_high": "A Fortune 500 company wants to license your patented technology for €2 million annually. They have a history of litigation with their partners.",
        "text_low": "A small business wants to license your patented technology for €20,000 annually. They have a history of litigation with their partners.",
        "correctAction": "pursue",
        "opponent_variants": [
            "Sie erfahren, dass das Start Up auf Grund der finanziellen Schwierigkeiten sich nicht anwaltlich vertreten lässt und bloß auf Informationen von ChatGPT zugreift.",
            "Sie erfahren, dass das Start Up anwaltlich vertreten ist."
        ]
    }
]

# AI advice pool for each case
AI_ADVICE_POOL = [
    # Case 1 advice
    {
        "caseId": 1,
        "advice_text": "Sie sollten auf ihre Kündigungsentschädigung beharren. Ein einmaliges, unverschuldetes Zuspätkommen aufgrund höherer Gewalt – wie etwa einer Straßenblockade durch Umweltaktivisten – rechtfertigt keine fristlose Entlassung gemäß § 27 Z 4 Fall 1 AngG. Die Entlassung dürfte daher rechtswidrig sein, und ein Anspruch auf Kündigungsentschädigung besteht.",
        "isTrue": True
    },
    {
        "caseId": 1,
        "advice_text": "Sie sollten nicht auf eine Kündigungsentschädigung beharren, weil die Arbeitgeberin das Vertrauen in ihre Zuverlässigkeit verlieren durfte. Die Arbeitgeberin muss sich, gerade dann, wenn Ihre Dienste besonders benötigt werden, auf das rechtzeitige Erscheinen verlassen können. In solchen Fällen wiegt nicht nur das objektive Fernbleiben schwer, sondern auch der Vertrauensbruch – was eine sofortige Entlassung gemäß § 27 Z 4 Fall 1 AngG rechtfertigen kann.",
        "isTrue": False
    },
    # Case 2 advice
    {
        "caseId": 2,
        "advice_text": "The VC firm typically takes 40% equity but provides extensive support and connections to help startups scale.",
        "isTrue": True
    },
    {
        "caseId": 2,
        "advice_text": "The VC firm takes 40% equity but rarely provides additional support beyond the initial investment.",
        "isTrue": False
    },
    # Case 3 advice
    {
        "caseId": 3,
        "advice_text": "The company has successfully resolved all previous litigation cases through mediation without going to court.",
        "isTrue": True
    },
    {
        "caseId": 3,
        "advice_text": "The company has lost several major lawsuits against their partners in the past year.",
        "isTrue": False
    }
]

def calculate_qsr(p: float, is_correct: bool) -> float:
    """
    Calculate Quadratic Scoring Rule (QSR) score.
    p: confidence as probability [0.0-1.0]
    is_correct: whether the decision was correct
    """
    if is_correct:
        return 1 - (1 - p) * (1 - p)
    else:
        return 1 - p * p
