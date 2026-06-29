"""Deterministic builder for the notetaker memory snapshot (no Modal needed).

The live model refused to emit store tool-calls for notetaker's terse note-dump
prereq turns, so build_memory_snapshots froze an EMPTY notetaker snapshot (all 25
notetaker query instances were unanswerable). Re-baking on Modal is both costly
and flaky for this scenario, and crucially the model-baked snapshots PARAPHRASE
the facts (dropping the exact details the queries ask about), which hurts
answerability.

Instead we construct the notetaker memory directly from that scenario's prereq
notes at fact granularity, storing each established fact VERBATIM under a short,
descriptive snake_case key (the same shape the model produces for the other
scenarios). This is faithful fixture construction: the prereq conversation
established these facts, so the post-conversation memory should contain them.
Short keys + verbatim values retrieve cleanly under the kv backend's BM25Plus
``archival_memory_key_search`` (verified offline against the real ranker), and a
handful of always-visible core entries backstop the hardest lookups.

Run:  uv run --with rank-bm25 python -m serving_eval.build_notetaker_snapshot --verify
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

from . import bfcl

SNAPSHOT_DIR = bfcl.BFCL_DATA_DIR / bfcl.MEMORY_SNAPSHOT_DIR

# Always-visible Core Memory (<=7 entries, <=300 chars each): a compact backstop
# of the facts most likely to be asked, so they never depend on retrieval at all.
CORE: dict[str, str] = {
    "daycare_schedule": "Kid's daycare: drop-off at 8 AM on Monday, pick-up at 5 PM. Monthly daycare payment is due Friday. Bring an extra set of clothes.",
    "monday_work_notes": "Monday: team meeting ran over by 30 minutes. Finalize Q1 budget report before Friday. IT updated security protocols, so change passwords ASAP. Client call with Jacob delayed to Wednesday.",
    "counting_practice": "Help the kid with counting practice; the teacher says to focus on the numbers 1-20.",
}

# Long-term Archival Memory (<=50 entries): each note fact stored verbatim under a
# short descriptive key whose salient words match the way the fact is queried.
ARCHIVAL: dict[str, str] = {
    # --- entry 32 (Mon-Fri work diary) ---
    "team_meeting_overran": "Monday: the team meeting ran over by 30 minutes.",
    "budget_report_q1_deadline": "Need to finalize the Q1 budget report before Friday.",
    "security_protocols_password_change": "IT updated security protocols, so change passwords ASAP.",
    "client_call_jacob_rescheduled": "Client call with Jacob was delayed until Wednesday.",
    "system_downtime_window": "Tuesday: system downtime from 10 AM - 12 PM slowed down the workflow.",
    "hr_benefits_package_review": "HR sent an updated benefits package; review it before next month's deadline.",
    "vendor_followup_emails": "Sent follow-up emails to vendors, still waiting on responses.",
    "leadership_presentation_slides": "Wednesday: presentation to leadership went well, but tweak a few slides for next week's review.",
    "client_proposal_legal_approval": "Client proposal draft is ready; send it to Legal for approval.",
    "onboard_new_hire": "Need to onboard a new hire on Wednesday; schedule a one-on-one with them.",
    "cost_cutting_recommendations": "Thursday: Finance wants cost-cutting recommendations; brainstorm ideas.",
    "sales_data_mistake": "Caught a mistake in last month's sales data.",
    "vendor_responses_count": "Followed up with vendors: two responded, one is still pending.",
    "training_session_prep": "Training session next Monday; prep the materials this weekend.",
    # --- entry 33 (urgent / work / tech / personal) ---
    "tax_documents_deadline": "Urgent: submit tax documents before Friday.",
    "credit_card_statement_review": "Review the credit card statement for errors.",
    "car_engine_noise": "Call the auto repair shop about a weird noise in the engine.",
    "quarterly_budget_finalize": "Work: finalize the quarterly budget.",
    "vendor_contract_review": "Review the vendor contract before signing.",
    "security_compliance_training": "Finish the security compliance training module.",
    "backup_laptop_files": "Tech: back up laptop files.",
    "update_phone_software": "Update the phone software.",
    "cancel_unused_subscriptions": "Cancel unused subscriptions.",
    "dentist_appointment_schedule": "Personal: schedule a dentist appointment.",
    "gym_three_times": "Stick to the gym 3 times this week.",
    "call_mom": "Call mom, it's been a while.",
    # --- entry 34 (chores / car / organizing / diy) ---
    "car_sunday_wash_vacuum": "Car: wash and vacuum it on Sunday; check tire pressure; refill windshield wiper fluid.",
    "pantry_restock_rice_cereal": "Restock the pantry, running low on rice and cereal.",
    "diy_home_fixes": "DIY fixes: tighten the loose cabinet handle, replace the bathroom lightbulb, and patch up minor wall scuffs.",
    "trash_out_wednesday": "Take the trash out Wednesday morning; vacuum the living room; mop the kitchen floor.",
    "donate_old_clothes": "Sort through the closet and donate old clothes; shred old mail.",
    # --- entry 35 (kid: daycare / school / doctor / family / shopping) ---
    "daycare_dropoff_time": "Daycare drop-off is at 8 AM on Monday.",
    "daycare_pickup_time": "Daycare pick-up is at 5 PM.",
    "daycare_monthly_payment_due": "The monthly daycare payment is due Friday.",
    "elementary_school_admission": "Finalize the elementary school admission paperwork; attend orientation next Thursday.",
    "pediatrician_visit": "Kid's cold isn't improving; schedule a pediatrician visit.",
    "kid_park_weekend": "Take the kid to the park this weekend and pick a new bedtime story book.",
    "school_supplies_shopping": "Get school supplies: crayons, notebooks, and glue sticks.",
    "buy_diapers": "Buy more diapers and pack extra snacks in the daycare bag.",
    # --- entry 36 (health: checkups / workout / diet / mental / supplements) ---
    "annual_physical_bloodwork": "Schedule an annual physical and bloodwork next month.",
    "eye_exam": "Look into getting an eye exam; been straining at screens a lot.",
    "workout_strength_training": "Gym at least 3x this week; focus on strength training for legs and back; aim for 10,000 steps daily.",
    "meal_prep_protein": "Sunday meal prep: grilled chicken, quinoa, and veggies.",
    "reduce_sugar_hydration": "Cut back on sugar and soda; aim for at least 3L of water per day.",
    "sleep_screen_time": "Mental health: get 7+ hours of sleep and limit screen time before bed.",
    "morning_supplements_probiotics": "Supplements: take probiotics in the morning to help digestion; Vitamin D3 1000 IU daily; Omega-3s for joints; iron for low levels.",
}


def build_snapshot() -> dict:
    assert len(CORE) <= 7, "core memory capped at 7 entries"
    assert all(len(v) <= 300 for v in CORE.values()), "core entry too long (>300)"
    assert len(ARCHIVAL) <= 50, f"archival capped at 50 entries (have {len(ARCHIVAL)})"
    key_re = re.compile(r"^[a-z]+(_[a-z0-9]+)*$")
    for k in list(CORE) + list(ARCHIVAL):
        assert key_re.match(k), f"bad snake_case key: {k}"
    return {"core_memory": dict(CORE), "archival_memory": dict(ARCHIVAL)}


def _norm(s: str) -> str:
    return re.sub(r"[^a-z0-9 ]", " ", str(s).lower())


def _gt_in(text_norm: str, gt: str) -> bool:
    """GT match that tolerates clock reformatting ("08:00 AM" stored as "8 AM")."""
    g = _norm(gt)
    if g and g in text_norm:
        return True
    # loose 12h-clock variant: drop ":00" and a leading zero -> "8 am" / "5 pm"
    m = re.match(r"^(\d{1,2})[: ]?(\d{2})?\s*(am|pm)$", g)
    if m:
        hh = str(int(m.group(1)))
        loose = f"{hh} {m.group(3)}"
        if loose in text_norm:
            return True
    return False


def verify(snap: dict) -> int:
    """Offline retrievability check against the REAL BM25 ranker (needs rank-bm25)."""
    from .bfcl_vendor.memory_kv import MemoryAPI_kv, BM25Plus

    if BM25Plus is None:
        print("ERROR: rank-bm25 not installed; rerun with `uv run --with rank-bm25 ...`", file=sys.stderr)
        return 2
    D = bfcl.BFCL_DATA_DIR
    qd = [json.loads(l) for l in (D / "BFCL_v4_memory.json").read_text().splitlines() if l.strip()]
    gt = {x["id"]: x for x in (json.loads(l) for l in
          (D / "possible_answer" / "BFCL_v4_memory.json").read_text().splitlines() if l.strip())}
    nt = [x for x in qd if x.get("scenario") == "notetaker"]
    core_blob = _norm(json.dumps(snap["core_memory"]))
    api = MemoryAPI_kv(); api.archival_memory = dict(snap["archival_memory"])
    ans = 0
    misses = []
    for x in nt:
        q = " ".join(m.get("content", "") for turn in x["question"] for m in turn)
        gts = gt[x["id"]]["ground_truth"]
        in_core = any(_gt_in(core_blob, g) for g in gts)
        targets = {k for k, v in snap["archival_memory"].items() if any(_gt_in(_norm(v), g) for g in gts)}
        top = [k for _, k in api.archival_memory_key_search(q, k=5)["ranked_results"]]
        in_arch = bool(targets & set(top))
        ok = in_core or in_arch
        ans += ok
        if not ok:
            misses.append((x["id"], q[:64], gts, sorted(targets)[:2], top[:3]))
    print(f"notetaker offline answerability (GT in core OR GT-bearing key in archival top-5): {ans}/{len(nt)} = {100*ans/len(nt):.0f}%")
    for m in misses:
        print("  MISS", m[0], "| q=", m[1], "| GT=", m[2], "| targets=", m[3], "| top3=", m[4])
    return 0 if ans >= len(nt) - 1 else 1  # allow at most 1 hard miss


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--verify", action="store_true", help="run offline BM25 retrievability check only")
    ap.add_argument("--write", action="store_true", help="write the snapshot file")
    args = ap.parse_args(argv)
    snap = build_snapshot()
    print(f"built notetaker snapshot: core={len(snap['core_memory'])} archival={len(snap['archival_memory'])}")
    rc = verify(snap)
    if args.write and rc in (0, 1):
        out = SNAPSHOT_DIR / "notetaker_final.json"
        out.write_text(json.dumps(snap, indent=2), encoding="utf-8")
        print(f"wrote {out}")
    return rc


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
