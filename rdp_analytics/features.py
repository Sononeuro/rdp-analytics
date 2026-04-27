"""Feature decomposition for the RDP person-level dataset.

Two RDP fields with semicolon-delimited multi-select content carry the bulk of
the analytic signal:

- `Reason for Referral` -> 10 binary need indicators (housing, employment, etc.)
- `Pathways`            -> 8 binary pathway-component indicators

Plus a 5-item clinical severity composite from history of seizures, lifetime
naloxone administration, lifetime ER visits, active suicidal ideation, and
overdose-as-stated-need.

Plus an `intake_complete` flag derived from the presence of any non-null answer
to the ethnicity question. This is a data-completeness proxy that turned out
to be the strongest single predictor of engagement in our random forest.
"""

from __future__ import annotations

import pandas as pd
import numpy as np

# === Controlled vocabulary for need decomposition ===
NEED_DOMAINS = [
    "Housing",
    "Employment",
    "Education",
    "Connection to treatment",
    "Connection to recovery community",
    "Recovery support",
    "Probation",
    "Overdose",
    "Co-occurring",
    "Multiple treatment episodes",
]

# === Controlled vocabulary for pathway decomposition ===
PATHWAY_COMPONENTS = [
    "Abstinence",
    "12-Step Recovery",
    "Support groups",
    "Natural Recovery",
    "Peer Recovery support",
    "Medication-assisted Recovery",
    "Harm Reduction",
    "Alternative/Holistic Recovery",
]

# === 5-item clinical severity composite ===
SEVERITY_COMPONENTS = [
    "sev_seizures",
    "sev_nlx",
    "sev_er",
    "sev_ideation",
    "sev_overdose_need",
]


def _path_col(name: str) -> str:
    """Sanitize a pathway component name into a valid column suffix."""
    return f"path_{name.replace(' ', '_').replace('-', '_').replace('/', '_')}"


def add_need_indicators(person: pd.DataFrame, source_col: str = "All Referrals") -> pd.DataFrame:
    """Decompose the aggregated referral text into 10 binary need indicators.

    Adds columns `need_<Domain>` and a `need_complexity` integer (sum across
    domains, range 0-10). Missing referral data yields NaN complexity.

    Parameters
    ----------
    person : pd.DataFrame
        Person-level DataFrame from `data.build_person_dataset`.
    source_col : str
        Name of the column containing aggregated referral text.

    Returns
    -------
    pd.DataFrame
        Same DataFrame with columns added in place (also returned).
    """
    s = person[source_col].fillna("")
    for domain in NEED_DOMAINS:
        person[f"need_{domain}"] = s.str.contains(
            domain, case=False, regex=False, na=False
        ).astype(int)

    need_cols = [f"need_{d}" for d in NEED_DOMAINS]
    person["need_complexity"] = person[need_cols].sum(axis=1)
    has_ref = (s != "")
    person.loc[~has_ref, "need_complexity"] = np.nan
    return person


def add_pathway_indicators(person: pd.DataFrame, source_col: str = "Pathways") -> pd.DataFrame:
    """Decompose the Pathways field into 8 binary pathway-component indicators.

    Adds columns `path_<Component>` (sanitized names) and a `pathway_diversity`
    integer (sum across components, range 0-8). Missing pathway data yields NaN.
    """
    s = person[source_col]
    for comp in PATHWAY_COMPONENTS:
        person[_path_col(comp)] = s.str.contains(
            comp, case=False, regex=False, na=False
        ).astype(int)

    path_cols = [_path_col(c) for c in PATHWAY_COMPONENTS]
    person["pathway_diversity"] = person[path_cols].sum(axis=1)
    person.loc[s.isna(), "pathway_diversity"] = np.nan
    return person


def add_severity_composite(person: pd.DataFrame) -> pd.DataFrame:
    """Construct a 5-item clinical severity composite (range 0-5).

    Components:
    - History of Seizures == "Yes"
    - Times given Naloxone/Narcan >= 1
    - Emergency Room Visits >= 2
    - Active suicidal ideation in `Ideations (Active)` field
    - Overdose endorsed as need (`need_Overdose` == 1)

    Missing values are treated as zero, biasing the composite downward.
    Use `severity_complete` mask for complete-case sensitivity analyses.
    """
    person["sev_seizures"] = (person.get("History of Seizures") == "Yes").astype(int)

    nlx = pd.to_numeric(person.get("Times given Naloxone/Narcan"), errors="coerce")
    person["sev_nlx"] = (nlx >= 1).fillna(False).astype(int)

    er = pd.to_numeric(person.get("Emergency Room Visits"), errors="coerce")
    person["sev_er"] = (er >= 2).fillna(False).astype(int)

    ideations = person.get("Ideations (Active)", pd.Series(dtype=object)).astype(str)
    person["sev_ideation"] = ideations.str.contains("Suicidal", case=False, na=False).astype(int)

    person["sev_overdose_need"] = person.get("need_Overdose", 0)

    person["severity_score"] = person[SEVERITY_COMPONENTS].sum(axis=1)

    # Mask for complete-case sensitivity analysis: all components observed
    person["severity_complete"] = (
        person.get("History of Seizures").notna()
        & nlx.notna()
        & er.notna()
        & person.get("Ideations (Active)").notna()
    ).astype(int)

    return person


def add_demographics(person: pd.DataFrame) -> pd.DataFrame:
    """Add coded demographic indicators used in the ML feature matrix.

    KNOWN PITFALL: the Hispanic indicator must use exact match on the value
    "Yes, Hispanic or Latino", NOT substring matching on the literal text
    "Hispanic", because the latter incorrectly includes participants who
    answered "No, Not Hispanic or Latino".
    """
    person["gender_male"] = (person.get("Gender") == "Male").astype(int)
    person["gender_tgnb"] = person.get("Gender", pd.Series(dtype=object)).isin(
        ["Transgender Male", "Transgender Female", "Non-Binary", "Genderqueer/Genderfluid"]
    ).astype(int)

    # Hispanic: exact match required. See README and tests for the bug history.
    person["hispanic"] = (person.get("Ethnicity") == "Yes, Hispanic or Latino").astype(int)

    # Intake completion proxy: any non-null answer to the ethnicity question.
    person["intake_complete"] = person.get("Ethnicity").notna().astype(int)

    person["veteran"] = (person.get("Veteran Status") == "Veteran").astype(int)
    person["Age_num"] = pd.to_numeric(person.get("Age"), errors="coerce")

    # Race, collapsed to top categories
    race_top = [
        "White",
        "Black or African American",
        "Native American",
        "Asian",
        "Native Hawaiian/Pacific Islander",
    ]

    def _collapse_race(r):
        if pd.isna(r):
            return "Missing"
        if isinstance(r, str) and ";" in r:
            return "Multiracial"
        return r if r in race_top else "Other"

    person["race_cat"] = person.get("Race").apply(_collapse_race)
    for r in ["White", "Black or African American", "Native American", "Multiracial", "Other"]:
        col = f"race_{r.replace(' ', '_').replace('/', '_')}"
        person[col] = (person["race_cat"] == r).astype(int)

    return person


def add_living_situation(person: pd.DataFrame) -> pd.DataFrame:
    """Add living-situation one-hot indicators.

    Living situation is preserved in its native 7-category form rather than
    collapsed to binary, because pilot inspection revealed substantial
    inter-category variation in retention (the recovery capital inversion).
    """
    lives_top = ["Recovery Residence", "Housed", "Residential Treatment", "Unhoused", "Halfway House"]
    for L in lives_top:
        person[f"lives_{L.replace(' ', '_')}"] = (person.get("Lives In") == L).astype(int)
    return person


def add_service_intensity(person: pd.DataFrame) -> pd.DataFrame:
    """Add service-intensity numeric features.

    `# of Supports` is the cumulative count of service contacts and is the
    proper service-intensity measure (100% complete in our cohort, range 0-253).
    """
    person["Supports_num"] = pd.to_numeric(
        person.get("# of Supports"), errors="coerce"
    ).fillna(0)
    person["NoShows_num"] = pd.to_numeric(
        person.get("# of No Shows"), errors="coerce"
    ).fillna(0)
    person["HasPeer_num"] = pd.to_numeric(
        person.get("Has Peer"), errors="coerce"
    ).fillna(0).astype(int)
    person["ins_medicaid"] = (person.get("Insurance Type") == "Medicaid").astype(int)
    return person


def build_full_feature_matrix(person: pd.DataFrame) -> pd.DataFrame:
    """Add all feature decompositions in the canonical order.

    Equivalent to:
        add_need_indicators -> add_pathway_indicators -> add_severity_composite
        -> add_demographics -> add_living_situation -> add_service_intensity
    """
    person = add_need_indicators(person)
    person = add_pathway_indicators(person)
    person = add_severity_composite(person)
    person = add_demographics(person)
    person = add_living_situation(person)
    person = add_service_intensity(person)
    # Defragment after many column insertions
    return person.copy()


def get_feature_lists() -> dict:
    """Return the canonical feature-name lists used in Step 2 ML analyses."""
    need_features = [f"need_{d}" for d in NEED_DOMAINS]
    path_cols = [_path_col(c) for c in PATHWAY_COMPONENTS]
    sev_features = ["sev_seizures", "sev_nlx", "sev_er", "sev_ideation"]
    demographic_features = [
        "Age_num", "gender_male", "gender_tgnb", "hispanic", "veteran",
        "race_White", "race_Black_or_African_American", "race_Native_American",
        "race_Multiracial", "race_Other",
    ]
    structural_features = [
        "lives_Recovery_Residence", "lives_Housed", "lives_Residential_Treatment",
        "lives_Unhoused", "lives_Halfway_House", "ins_medicaid",
    ]
    service_features = ["HasPeer_num", "Supports_num", "NoShows_num"]

    return {
        "need_features": need_features,
        "path_cols": path_cols,
        "sev_features": sev_features,
        "demographic_features": demographic_features,
        "structural_features": structural_features,
        "service_features": service_features,
        "features_for_pathway": (
            need_features + sev_features + demographic_features + structural_features
        ),
        "features_for_engagement": (
            need_features + path_cols + sev_features + demographic_features
            + structural_features + service_features + ["intake_complete"]
        ),
    }
