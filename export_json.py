#!/usr/bin/env python3
"""Export tracker.db to web/data.json for the static dashboard (index.html).
Run after build_db.py. Zero dependencies."""
import sqlite3, json, os

HERE = os.path.dirname(os.path.abspath(__file__))
con = sqlite3.connect(os.path.join(HERE, "..", "tracker.db"))
con.row_factory = sqlite3.Row

startups = []
for r in con.execute("SELECT * FROM startups ORDER BY name"):
    void = con.execute("""SELECT v.name FROM startup_voids sv JOIN voids v ON v.id=sv.void_id
                          WHERE sv.startup_id=?""", (r["id"],)).fetchone()
    sdgs = [x["number"] for x in con.execute(
        """SELECT g.number FROM startup_sdgs ss JOIN sdgs g ON g.id=ss.sdg_id
           WHERE ss.startup_id=? ORDER BY g.number""", (r["id"],))]
    edges = con.execute("""SELECT i.name AS investor, inv.round, inv.announced_date
        FROM investments inv JOIN investors i ON i.id=inv.investor_id
        WHERE inv.startup_id=? ORDER BY inv.announced_date""", (r["id"],)).fetchall()
    startups.append(dict(
        name=r["name"], sector=r["sector"], region=r["country_region"],
        website=r["website"], model=r["impact_model"], stage=r["stage"],
        void=void["name"] if void else "Uncategorized",
        sdgs=sdgs,
        investors=[dict(e) for e in edges]))

investors = []
for r in con.execute("SELECT * FROM investors ORDER BY name"):
    void = con.execute("""SELECT v.name FROM investor_voids iv JOIN voids v ON v.id=iv.void_id
                          WHERE iv.investor_id=?""", (r["id"],)).fetchone()
    edges = con.execute("""SELECT s.name AS startup, inv.round
        FROM investments inv JOIN startups s ON s.id=inv.startup_id
        WHERE inv.investor_id=?""", (r["id"],)).fetchall()
    investors.append(dict(
        name=r["name"], type=r["type"], geography=r["geography"],
        focus=r["focus_sectors"], stage=r["stage"], check=r["typical_check_usd"],
        website=r["website"], thesis=r["notes"],
        void=void["name"] if void else "Uncategorized",
        portfolio=[dict(e) for e in edges]))

sdgs = {r["number"]: r["title"] for r in con.execute("SELECT * FROM sdgs")}
voids = [dict(r) for r in con.execute("SELECT * FROM voids ORDER BY name")]
con.close()

data = dict(startups=startups, investors=investors, sdgs=sdgs, voids=voids)
out = os.path.join(HERE, "data.json")
with open(out, "w") as f:
    json.dump(data, f, indent=1)
print(f"wrote {out}: {len(startups)} startups, {len(investors)} investors, {len(voids)} voids")
