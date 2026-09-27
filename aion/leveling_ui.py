"""Leveling defaults UI (Main / Alt tabs on the Leveling page)."""
from __future__ import annotations

import json

import streamlit as st

from aion import db, ui


def _save_option(template_id: int, opt: str, widget_key: str) -> None:
    row = db.read_table("leveling_templates", where="id = ?", params=[template_id]).iloc[0]
    opts = json.loads(row["options"] or "{}")
    opts[opt] = st.session_state[widget_key]
    db.update("leveling_templates", {"id": template_id}, {"options": json.dumps(opts)})


def _save_checklist(template_id: int, widget_key: str) -> None:
    db.update("leveling_templates", {"id": template_id}, {"checklist": st.session_state[widget_key]})


def leveling_defaults(role: str) -> None:
    tmpl = db.read_table("leveling_templates", where="role = ?", params=[role], order="priority")

    def upd(rk: dict, changes: dict) -> None:
        db.update("leveling_templates", rk, {k: v for k, v in changes.items() if k in ("hours", "critical")})

    with st.container(border=True):
        st.subheader("Blocks")
        st.caption("Hours are planning values and apply to every "
                   + ("Main" if role == "main" else "Alt") + " character and feed the **Leveling schedule**.")
        ui.editor(
            tmpl[["label", "start_level", "end_level", "hours", "critical"]], f"tmpl_{role}",
            [{"id": int(i)} for i in tmpl["id"]], on_update=upd,
            disabled=["label", "start_level", "end_level"],
            column_config={
                "label": ui.cc.TextColumn("Block"),
                "start_level": ui.cc.NumberColumn("Start level"),
                "end_level": ui.cc.NumberColumn("End level"),
                "hours": ui.cc.NumberColumn("Estimated hours", min_value=0.0, step=0.25, format="%.2f"),
                "critical": ui.cc.CheckboxColumn("Critical"),
            },
        )
        total = tmpl["hours"].sum()
        crit = tmpl.loc[tmpl["critical"].astype(bool), "hours"].sum()
        st.caption(f"Total **{total:.1f} h** per character, **{crit:.1f} h** critical. "
                   "Cleanup is one-time progression and never counts toward the weekly loop.")

    for col, (_, t) in zip(st.columns(len(tmpl)), tmpl.iterrows()):
        with col, st.container(border=True):
            st.markdown(f"**{t['label']}** · {t['hours']:.1f} h")
            if t["block_type"] == "mid":
                st.caption(":material/lock: Mandatory: rush the MSQ to 45; Nightmare unlocks through the MSQ chain.")
            for opt, val in json.loads(t["options"] or "{}").items():
                wk = f"opt_{t['id']}_{opt}"
                label = opt.replace("_", " ").capitalize()
                if isinstance(val, bool):
                    st.toggle(label, value=val, key=wk, on_change=_save_option, args=(int(t["id"]), opt, wk))
                else:
                    st.segmented_control(label, ["none", "minimal", "selective", "all"], default=val, key=wk,
                                         on_change=_save_option, args=(int(t["id"]), opt, wk))
            wk = f"check_{t['id']}"
            st.text_area("Route checklist (one item per line)", value=t["checklist"] or "", key=wk, height=180,
                         on_change=_save_checklist, args=(int(t["id"]), wk))
