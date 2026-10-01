"""Load the Excel traceability dataset into an empty database.

Rows that break the application's rules are not loaded; each one is listed in the ImportReport
(missing relationships are reported, never inferred). The one deliberate repair: a cone whose drum is
missing from the Drum sheet gets that drum created on the cone's own Autoconer_ID, and this is noted.
"""
import uuid
from dataclasses import dataclass, field

import pandas as pd

import config
from database import queries as q
from database.database import DEMO_USERS
from utils.dates import now_local, to_db
from utils.security import hash_password
from utils.validators import normalize_id

ROLE_MAP = {
    "administrator": "admin",
    "production user": "operator",
    "quality user": "supervisor",
    "supervisor": "supervisor",
}
AUDIT_ACTION_MAP = {
    "SEARCH_CY": ("SEARCH", "CY"), "SEARCH_COB": ("SEARCH", "COB"),
    "REPORT_CY": ("REPORT", "CY"), "REPORT_COB": ("REPORT", "COB"),
}


@dataclass
class ImportReport:
    counts: dict[str, int] = field(default_factory=dict)
    notes: list[str] = field(default_factory=list)      # repairs and mappings applied
    rejected: list[str] = field(default_factory=list)   # rows that broke a rule
    skipped: list[str] = field(default_factory=list)    # rows that could not be stored as-is

    def as_text(self) -> str:
        lines = ["Loaded rows:"] + [f"  {table:18} {n}" for table, n in self.counts.items()]
        for title, items in (("Notes", self.notes), ("Rejected", self.rejected), ("Skipped", self.skipped)):
            lines.append(f"{title} ({len(items)}):")
            lines += [f"  - {item}" for item in items] or ["  (none)"]
        return "\n".join(lines)


def _rows(sheets: dict[str, pd.DataFrame], name: str) -> list[dict]:
    df = sheets[name].astype(str).apply(lambda col: col.str.strip())
    return df.to_dict("records")


def _ts(value: str) -> str:
    return to_db(pd.Timestamp(value).to_pydatetime().replace(microsecond=0))


def import_dataset(engine, sheets: dict[str, pd.DataFrame],
                   bcrypt_rounds: int = config.BCRYPT_ROUNDS) -> ImportReport:
    """Import all sheets in one transaction into a database that has the schema but no data."""
    report = ImportReport()
    txn_id = f"import-{uuid.uuid4()}"
    created_at = to_db(now_local())

    with engine.begin() as conn:
        # --- users -------------------------------------------------------------------
        user_ids: dict[str, int] = {}   # dataset User_ID -> users.user_id
        usernames: dict[str, int] = {}  # username -> users.user_id
        for row in _rows(sheets, "Users"):
            role = ROLE_MAP.get(row["Role"].lower())
            if role is None:
                report.rejected.append(f"User {row['Username']}: unknown role '{row['Role']}'")
                continue
            status = "active" if row["Status"].lower() == "active" else "disabled"
            uid = conn.execute(q.IMPORT_USER, {
                "username": row["Username"], "role": role, "status": status,
                "password_hash": hash_password(f"{row['Username']}123", bcrypt_rounds)}).lastrowid
            user_ids[row["User_ID"]] = usernames[row["Username"]] = uid
            report.notes.append(f"User {row['Username']}: role '{row['Role']}' -> {role}, "
                                f"password '{row['Username']}123'")
        for _, username, password, role in DEMO_USERS:
            if username not in usernames:
                usernames[username] = conn.execute(q.IMPORT_USER, {
                    "username": username, "role": role, "status": "active",
                    "password_hash": hash_password(password, bcrypt_rounds)}).lastrowid
                report.notes.append(f"Demo account {username} kept (password '{password}')")
        creator = usernames.get("admin") or next(iter(usernames.values()))

        # --- machine masters ---------------------------------------------------------
        autoconers = set()
        for row in _rows(sheets, "Autoconer"):
            active = row["Machine_Status"].lower() == "running"
            conn.execute(q.IMPORT_AUTOCONER, {"autoconer_id": normalize_id(row["Autoconer_ID"]),
                                              "machine_name": row["Autoconer_Name"], "is_active": int(active)})
            autoconers.add(normalize_id(row["Autoconer_ID"]))
            if not active:
                report.notes.append(f"Autoconer {row['Autoconer_ID']} imported as inactive "
                                    f"(Machine_Status={row['Machine_Status']})")

        drum_owner: dict[str, str] = {}
        for row in _rows(sheets, "Drum"):
            drum, ac = normalize_id(row["Drum_ID"]), normalize_id(row["Autoconer_ID"])
            if ac not in autoconers:
                report.rejected.append(f"Drum {drum}: Autoconer {ac} does not exist")
                continue
            conn.execute(q.INSERT_DRUM, {"drum_id": drum, "autoconer_id": ac})
            drum_owner[drum] = ac

        speedframes = set()
        for row in _rows(sheets, "Speedframe"):
            active = row["Machine_Status"].lower() == "running"
            conn.execute(q.IMPORT_SPEEDFRAME, {"speedframe_id": normalize_id(row["Speedframe_ID"]),
                                               "machine_name": row["Speedframe_Name"], "is_active": int(active)})
            speedframes.add(normalize_id(row["Speedframe_ID"]))
            if not active:
                report.notes.append(f"Speedframe {row['Speedframe_ID']} imported as inactive "
                                    f"(Machine_Status={row['Machine_Status']})")

        spindle_owner: dict[str, str] = {}
        for row in _rows(sheets, "Spindle"):
            spindle, sf = normalize_id(row["Spindle_ID"]), normalize_id(row["Speedframe_ID"])
            if sf not in speedframes:
                report.rejected.append(f"Spindle {spindle}: Speedframe {sf} does not exist")
                continue
            conn.execute(q.INSERT_SPINDLE, {"spindle_id": spindle, "speedframe_id": sf})
            spindle_owner[spindle] = sf

        # --- yarn cones ----------------------------------------------------------------
        cones = set()
        for row in _rows(sheets, "Yarn_Cone"):
            cy, ac, drum = normalize_id(row["CY_ID"]), normalize_id(row["Autoconer_ID"]), normalize_id(row["Drum_ID"])
            if drum not in drum_owner:
                if ac not in autoconers:
                    report.rejected.append(f"Yarn Cone {cy}: Drum {drum} and Autoconer {ac} do not exist")
                    continue
                conn.execute(q.INSERT_DRUM, {"drum_id": drum, "autoconer_id": ac})
                drum_owner[drum] = ac
                report.notes.append(f"Drum {drum} was missing from the Drum sheet; created on {ac} "
                                    f"(from Yarn Cone {cy})")
            if drum_owner[drum] != ac:
                report.rejected.append(f"Yarn Cone {cy}: Drum {drum} belongs to {drum_owner[drum]}, not {ac}")
                continue
            conn.execute(q.INSERT_CONE, {
                "cy_id": cy, "drum_id": drum, "cone_scan_datetime": _ts(row["Cone_Scan_DateTime"]),
                "receive_txn_id": txn_id, "created_by": creator, "created_at": created_at})
            cones.add(cy)

        # --- COBs and links (COB scan time lives on the link sheet) --------------------
        cob_spindle: dict[str, str] = {}
        for row in _rows(sheets, "COB"):
            cob, sf, spindle = normalize_id(row["COB_ID"]), normalize_id(row["Speedframe_ID"]), normalize_id(row["Spindle_ID"])
            if spindle not in spindle_owner:
                report.rejected.append(f"COB {cob}: Spindle {spindle} does not exist")
            elif spindle_owner[spindle] != sf:
                report.rejected.append(f"COB {cob}: Spindle {spindle} belongs to {spindle_owner[spindle]}, not {sf}")
            else:
                cob_spindle[cob] = spindle

        links: dict[str, tuple[str, str]] = {}  # cob -> (cy, scan time)
        trace_rows = sorted(_rows(sheets, "COB_Traceability"), key=lambda r: int(r["Trace_ID"]))
        for row in trace_rows:
            tid, cy, cob = row["Trace_ID"], normalize_id(row["CY_ID"]), normalize_id(row["COB_ID"])
            if cy not in cones:
                report.rejected.append(f"Trace_ID {tid}: Yarn Cone {cy} was not loaded; link to {cob} skipped")
            elif cob not in cob_spindle:
                report.rejected.append(f"Trace_ID {tid}: COB {cob} was not loaded; link to {cy} skipped")
            elif cob in links:
                report.rejected.append(f"Trace_ID {tid}: COB {cob} is already linked to {links[cob][0]}; "
                                       f"link to {cy} not loaded (one cone per COB)")
            else:
                links[cob] = (cy, _ts(row["COB_Scan_DateTime"]))

        for cob, spindle in cob_spindle.items():
            if cob not in links:
                report.skipped.append(f"COB {cob}: not linked to any Yarn Cone, so it has no scan time; not loaded")
                continue
            conn.execute(q.INSERT_COB, {
                "cob_id": cob, "spindle_id": spindle, "cob_scan_datetime": links[cob][1],
                "receive_txn_id": txn_id, "created_by": creator, "created_at": created_at})
        for cob, (cy, _) in links.items():
            conn.execute(q.INSERT_TRACE, {"cy_id": cy, "cob_id": cob,
                                          "receive_txn_id": txn_id, "created_at": created_at})

        # --- audit history ----------------------------------------------------------------
        audit_rows = 0
        for row in _rows(sheets, "Audit_Log"):
            mapped = AUDIT_ACTION_MAP.get(row["Action"].upper())
            if mapped is None or row["User_ID"] not in user_ids:
                report.rejected.append(f"Audit {row['Audit_ID']}: unknown action or user")
                continue
            action, id_type = mapped
            conn.execute(q.INSERT_AUDIT, {
                "user_id": user_ids[row["User_ID"]], "action": action, "id_type": id_type,
                "id_value": normalize_id(row["Search_ID"]), "result": row["Result"],
                "detail": f"imported {row['Audit_ID']}", "event_datetime": _ts(row["Action_DateTime"])})
            audit_rows += 1

    report.counts = {
        "users": len(usernames), "autoconer": len(autoconers), "drum": len(drum_owner),
        "speedframe": len(speedframes), "spindle": len(spindle_owner), "yarn_cone": len(cones),
        "cob": len(links), "cob_traceability": len(links), "audit_log": audit_rows,
    }
    return report
