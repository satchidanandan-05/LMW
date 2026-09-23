"""RECEIVE module: capture a Yarn Cone and its COBs, validate, and save in one transaction."""
from datetime import datetime

import pandas as pd
import streamlit as st

from database.database import get_engine
from services import master_service, receive_service
from services.receive_service import CobEntry, ReceivePayload, ReceiveRejected, ValidationError
from ui.components import require_role
from utils.dates import now_local
from utils.validators import normalize_id

GRID_COLUMNS = ["COB ID", "Speedframe", "Spindle", "Scan date & time"]


def grid_to_entries(df: pd.DataFrame) -> list[CobEntry]:
    entries = []
    for record in df.to_dict("records"):
        values = {k: (None if pd.isna(v) else v) for k, v in record.items()}
        if all(v in (None, "") for v in values.values()):
            continue
        ts = values.get("Scan date & time")
        entries.append(CobEntry(
            cob_id=str(values.get("COB ID") or ""),
            speedframe_id=str(values.get("Speedframe") or ""),
            spindle_id=str(values.get("Spindle") or ""),
            cob_scan_datetime=pd.Timestamp(ts).to_pydatetime().replace(microsecond=0) if ts is not None else None,
        ))
    return entries


def format_errors(errors: list[ValidationError]) -> str:
    return "\n".join(
        f"- **{'Yarn Cone' if e.row is None else f'COB row {e.row}'}:** {e.message}" for e in errors
    )


def _key(name: str) -> str:
    # Bumping receive_form_id after a successful save gives every widget a fresh key, i.e. a clean form.
    return f"{name}_{st.session_state.setdefault('receive_form_id', 0)}"


def render() -> None:
    user = require_role("receive")
    engine = get_engine()
    st.header("Receive")
    if "receive_success" in st.session_state:
        st.success(st.session_state.pop("receive_success"))

    now = now_local()
    autoconers = [a["autoconer_id"] for a in master_service.list_autoconers(engine)]
    speedframes = [s["speedframe_id"] for s in master_service.list_speedframes(engine)]
    spindles = [s["spindle_id"] for s in master_service.list_spindles(engine)]

    st.subheader("Yarn Cone")
    c1, c2, c3 = st.columns(3)
    cy_id = c1.text_input("Yarn Cone ID", placeholder="YC006", key=_key("cy"))
    autoconer = c2.selectbox("Autoconer", autoconers, index=None, placeholder="Select autoconer", key=_key("ac"))
    drums = [d["drum_id"] for d in master_service.list_drums(engine, autoconer)] if autoconer else []
    drum = c3.selectbox("Drum", drums, index=None, placeholder="Select drum", key=_key("drum"),
                        disabled=autoconer is None)
    d1, d2, _ = st.columns(3)
    cone_date = d1.date_input("Cone scan date", value=now.date(), format="DD-MM-YYYY", key=_key("date"))
    cone_time = d2.time_input("Cone scan time", value=now.time(), step=60, key=_key("time"))

    st.subheader("COBs")
    empty = pd.DataFrame({
        "COB ID": pd.Series(dtype="object"), "Speedframe": pd.Series(dtype="object"),
        "Spindle": pd.Series(dtype="object"), "Scan date & time": pd.Series(dtype="datetime64[ns]"),
    }, columns=GRID_COLUMNS)
    grid = st.data_editor(
        empty, num_rows="dynamic", key=_key("cobs"), hide_index=True,
        column_config={
            "COB ID": st.column_config.TextColumn(required=True),
            "Speedframe": st.column_config.SelectboxColumn(options=speedframes, required=True),
            "Spindle": st.column_config.SelectboxColumn(options=spindles, required=True),
            "Scan date & time": st.column_config.DatetimeColumn(format="DD-MM-YYYY HH:mm:ss", step=1,
                                                                required=True),
        },
    )

    if st.button("Validate & Save", type="primary"):
        payload = ReceivePayload(
            cy_id=cy_id, autoconer_id=autoconer or "", drum_id=drum or "",
            cone_scan_datetime=datetime.combine(cone_date, cone_time).replace(microsecond=0),
            cobs=grid_to_entries(grid),
        )
        try:
            txn_id = receive_service.save_receive(engine, payload, user.user_id)
        except ReceiveRejected as rejected:
            st.error("Nothing was saved. Please fix the following:\n\n" + format_errors(rejected.errors))
        else:
            st.session_state.receive_success = (
                f"Saved Yarn Cone {normalize_id(cy_id)} with {len(payload.cobs)} COB(s). "
                f"Transaction ID: {txn_id}")
            st.session_state.receive_form_id += 1
            st.rerun()
