import pandas as pd
import streamlit as st

from aion import calc, db, seed, ui

d = ui.data()
chars = d.characters

FIELDS = ["name", "class", "faction", "server", "is_main", "membership", "level", "item_level", "combat_power",
          "pvp_item_level", "pvp_combat_power", "pvp_power_metric", "active", "sort_order", "notes"]


def _opt_int(v):
    return None if v is None or pd.isna(v) else int(v)


def character_form(existing: pd.Series | None) -> None:
    e = existing if existing is not None else pd.Series(dtype=object)
    g = lambda k, default: default if existing is None or pd.isna(e.get(k)) else e.get(k)
    with st.form("character_form", border=False):
        name = st.text_input("Name", value=g("name", ""))
        with st.container(horizontal=True):
            cls = st.selectbox("Class", calc.CLASSES, index=calc.CLASSES.index(g("class", "Gladiator")))
            faction = st.segmented_control("Faction", calc.FACTIONS, default=g("faction", "Asmodian"))
        server = st.text_input("Server", value=g("server", chars["server"].iloc[0] if not chars.empty else "Server 1"))
        with st.container(horizontal=True):
            is_main = st.toggle("Main", value=bool(g("is_main", chars.empty)))
            membership = st.toggle("Membership", value=bool(g("membership", True)))
            active = st.toggle("Active", value=bool(g("active", True)))
        with st.container(horizontal=True):
            level = st.number_input("Level", 1, 60, int(g("level", 1)))
            item_level = st.number_input("PvE GS", 0, value=int(g("item_level", 0)))
            cp = st.number_input("PvE combat power", 0, value=_opt_int(g("combat_power", None)))
        with st.container(horizontal=True):
            pvp_il = st.number_input("PvP GS", 0, value=_opt_int(g("pvp_item_level", None)))
            pvp_cp = st.number_input("PvP displayed CP", 0, value=_opt_int(g("pvp_combat_power", None)),
                                     help="Displayed CP changes with equipped gear; PvP bonuses don't map 1:1.")
            pvp_metric = st.number_input("PvP power metric", value=None if pd.isna(g("pvp_power_metric", None)) else float(g("pvp_power_metric", 0)))
        sort_order = st.number_input("Display order", value=int(g("sort_order", (chars["sort_order"].max() + 1) if not chars.empty else 0)))
        notes = st.text_area("Notes", value=g("notes", ""))
        if st.form_submit_button("Save", type="primary", icon=":material/save:"):
            if not name.strip():
                st.error("Name is required.")
                return
            values = dict(name=name.strip(), **{"class": cls}, faction=faction or "Asmodian", server=server.strip() or "Server 1",
                          is_main=is_main, membership=membership, level=level, item_level=item_level, combat_power=cp,
                          pvp_item_level=pvp_il, pvp_combat_power=pvp_cp, pvp_power_metric=pvp_metric,
                          active=active, sort_order=sort_order, notes=notes)
            if existing is None:
                new_id = db.insert("characters", values)
                with db.connect() as conn:
                    seed.add_character_defaults(conn, new_id, is_main)
            else:
                db.update("characters", {"id": int(existing["id"])}, values)
            st.rerun()


@st.dialog("New character", width="large")
def create_dialog():
    character_form(None)


@st.dialog("Edit character", width="large")
def edit_dialog(row: pd.Series):
    character_form(row)


@st.dialog("Delete character")
def delete_dialog(row: pd.Series):
    st.warning(f"Delete **{row['name']}** ({row['class']})? Its leveling blocks, gear slots, activity settings "
               "and weekly log are deleted too.", icon=":material/warning:")
    if st.button("Delete", type="primary", icon=":material/delete:"):
        db.delete("characters", {"id": int(row["id"])})
        st.rerun()


view = chars.sort_values(["sort_order", "id"]).reset_index(drop=True)
event = ui.show(
    view[["name", "class", "faction", "server", "is_main", "membership", "level", "item_level", "combat_power",
          "pvp_item_level", "pvp_combat_power", "active", "notes"]],
    hide_index=True, on_select="rerun", selection_mode="single-row", key="characters_table",
    column_config={
        "name": ui.cc.TextColumn("Name", pinned=True),
        "class": "Class", "faction": "Faction", "server": "Server",
        "is_main": ui.cc.CheckboxColumn("Main"),
        "membership": ui.cc.CheckboxColumn("Membership"),
        "level": ui.cc.NumberColumn("Level"),
        "item_level": ui.cc.NumberColumn("PvE GS"),
        "combat_power": ui.cc.NumberColumn("PvE CP", format="%,d"),
        "pvp_item_level": ui.cc.NumberColumn("PvP GS"),
        "pvp_combat_power": ui.cc.NumberColumn("PvP CP", format="%,d"),
        "active": ui.cc.CheckboxColumn("Active"),
        "notes": ui.cc.TextColumn("Notes", width="large"),
    },
)
selected = view.iloc[event.selection.rows[0]] if event.selection.rows else None

with st.container(horizontal=True):
    if st.button("New character", type="primary", icon=":material/person_add:"):
        create_dialog()
    if st.button("Edit", icon=":material/edit:", disabled=selected is None):
        edit_dialog(selected)
    if st.button("Delete", icon=":material/delete:", disabled=selected is None):
        delete_dialog(selected)
if selected is None:
    st.caption("Select a row to edit or delete it.")

if not chars.empty and not chars["is_main"].astype(bool).any():
    st.warning("No character is marked as Main.", icon=":material/warning:")
for server, grp in chars.groupby("server"):
    if grp["is_main"].astype(bool).sum() > 1:
        st.info(f"{server} has more than one Main. Server-wide content goes to the Main with the highest GS.",
                icon=":material/info:")
