"""Load Recovery Data Platform Excel exports and aggregate to one row per participant.

The RDP exports contain one row per assessment record. A participant typically has
multiple records (median ~5 per person in our cohort, range 1-13). This module
collapses to person-level by:
- Sorting by SAFEID and assessment date
- Taking the most recent non-null value per field for snapshot fields
- Aggregating multi-select fields (Reason for Referral) across all records

This per-participant collapse is the foundation for all downstream analyses.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import pandas as pd


SAFEID_COL = "SAFEID"
DATE_COL = "As of Date"
REFERRAL_COL = "Reason for Referral"


def load_rdp_extract(path: str | Path) -> pd.DataFrame:
    """Load a single RDP Excel export, parsing dates and sorting.

    Parameters
    ----------
    path : str or Path
        Path to the .xlsx file as exported from the Recovery Data Platform.

    Returns
    -------
    pd.DataFrame
        Sorted DataFrame with parsed assessment dates.
    """
    df = pd.read_excel(path)
    df[DATE_COL] = pd.to_datetime(df[DATE_COL], errors="coerce")
    df = df.sort_values([SAFEID_COL, DATE_COL]).reset_index(drop=True)
    return df


def aggregate_referrals(df: pd.DataFrame) -> pd.Series:
    """Aggregate Reason for Referral across all records per participant.

    Returns a Series indexed by SAFEID, where each value is a semicolon-joined
    list of unique referral reasons across all records for that participant.

    Need-domain indicators built from this aggregated string capture the
    participant's lifetime referral profile, not just the most-recent snapshot.
    """
    return (
        df.groupby(SAFEID_COL)[REFERRAL_COL]
        .apply(lambda s: ";".join(s.dropna().astype(str).unique()))
        .rename("All Referrals")
    )


def build_person_dataset(
    primary_path: str | Path,
    paired_path: Optional[str | Path] = None,
) -> pd.DataFrame:
    """Build the person-level analytic dataset from one or two RDP exports.

    Each participant becomes a single row with their most recent values for
    snapshot fields and an aggregated referral profile.

    Parameters
    ----------
    primary_path : str or Path
        Path to the primary (most recent) RDP export.
    paired_path : str or Path, optional
        Path to an earlier RDP export. If provided, a `paired` boolean column
        is added to the result indicating which participants appear in both.

    Returns
    -------
    pd.DataFrame
        Person-level DataFrame, one row per unique SAFEID, with `All Referrals`
        column added. No need or pathway indicators are added here; see
        `rdp_analytics.features`.
    """
    df = load_rdp_extract(primary_path)
    person = df.groupby(SAFEID_COL).last().reset_index()
    person = person.merge(aggregate_referrals(df).reset_index(), on=SAFEID_COL, how="left")

    if paired_path is not None:
        df_paired = load_rdp_extract(paired_path)
        paired_ids = set(df_paired[SAFEID_COL].unique())
        person["paired"] = person[SAFEID_COL].isin(paired_ids)

    # Engagement outcomes
    person["engaged"] = (person.get("Status", pd.Series(dtype=object)) == "Engaged").astype(int)
    if "Days Engaged" in person.columns:
        person["Days Engaged"] = pd.to_numeric(person["Days Engaged"], errors="coerce")
    if "# of Supports" in person.columns:
        person["# of Supports"] = pd.to_numeric(person["# of Supports"], errors="coerce")

    return person


def paired_pathway_change(
    primary_path: str | Path,
    earlier_path: str | Path,
    pathway_col: str = "Pathways",
) -> pd.DataFrame:
    """Compute pathway-string change between two RDP extracts.

    Returns a DataFrame indexed by SAFEID with columns:
    - earlier:  most-recent pathway string in the earlier extract
    - later:    most-recent pathway string in the later extract
    - changed:  whether the strings differ

    Used to document that pathway endorsement is approximately stable over time
    (~1% of paired participants showed any change in our cohort).
    """
    df_late = load_rdp_extract(primary_path)
    df_early = load_rdp_extract(earlier_path)

    def _last_nonnull(s: pd.Series) -> Optional[str]:
        s = s.dropna()
        return s.iloc[-1] if len(s) else None

    late = df_late.groupby(SAFEID_COL)[pathway_col].apply(_last_nonnull).rename("later")
    early = df_early.groupby(SAFEID_COL)[pathway_col].apply(_last_nonnull).rename("earlier")
    paired = pd.concat([early, late], axis=1).dropna()
    paired["changed"] = paired["earlier"] != paired["later"]
    return paired
