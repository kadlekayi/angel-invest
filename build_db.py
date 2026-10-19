#!/usr/bin/env python3
"""Rebuild tracker.db from the CSV sources. Keeps the repo reproducible:
python3 build_db.py  (run from the repo root)"""
import sqlite3, csv, os

db = "tracker.db"
if os.path.exists(db): os.remove(db)
con = sqlite3.connect(db); cur = con.cursor()

cur.executescript("""
CREATE TABLE voids (id INTEGER PRIMARY KEY, name TEXT UNIQUE NOT NULL, description TEXT);
CREATE TABLE sdgs (id INTEGER PRIMARY KEY, number INTEGER UNIQUE NOT NULL, title TEXT NOT NULL);
CREATE TABLE investors (
  id INTEGER PRIMARY KEY, name TEXT UNIQUE NOT NULL, type TEXT, geography TEXT,
  focus_sectors TEXT, stage TEXT, typical_check_usd TEXT, website TEXT,
  notes TEXT, last_verified DATE);
CREATE TABLE startups (
  id INTEGER PRIMARY KEY, name TEXT UNIQUE NOT NULL, sector TEXT, country_region TEXT,
  website TEXT, impact_model TEXT, stage TEXT, last_verified DATE);
CREATE TABLE startup_voids (startup_id INTEGER REFERENCES startups(id), void_id INTEGER REFERENCES voids(id),
  PRIMARY KEY (startup_id, void_id));
CREATE TABLE startup_sdgs (startup_id INTEGER REFERENCES startups(id), sdg_id INTEGER REFERENCES sdgs(id),
  PRIMARY KEY (startup_id, sdg_id));
CREATE TABLE investor_voids (investor_id INTEGER REFERENCES investors(id), void_id INTEGER REFERENCES voids(id),
  PRIMARY KEY (investor_id, void_id));
CREATE TABLE investments (
  id INTEGER PRIMARY KEY, investor_id INTEGER REFERENCES investors(id),
  startup_id REFERENCES startups(id), round TEXT, amount_usd REAL,
  announced_date DATE, source_url TEXT, notes TEXT);
""")
con.commit()

voids = [
 ("Financial exclusion","Banks/credit systems fail to serve low-income or unbanked populations"),
 ("Energy access","Grid electricity absent or unreliable for rural/poor populations"),
 ("Agricultural market & finance void","Smallholders lack inputs, buyers, fair prices, or credit"),
 ("Healthcare access","Primary care, diagnostics, or medicine unaffordable or unavailable"),
 ("Education & childcare void","Quality early education/childcare unavailable to low-income families"),
 ("Capital access gap (pioneer gap / missing middle)","Enterprises too risky for VC, too big for microfinance/philanthropy"),
 ("Payments & infrastructure void","Fragmented or absent payment/commerce rails"),
 ("Supply chain void","Broken formal supply chains between producers and off-takers"),
 ("Philanthropic engagement gap","Charitable giving infrastructure underdeveloped"),
 ("Climate resilience & clean environment void","Climate change effects (water scarcity, floods, heat) undermine vulnerable communities lacking adaptive infrastructure"),
 ("Retail capital market access void","Capital markets shallow; retail investors lack diversified, transparent, low-cost products beyond mutual funds"),
 ("Bond/fixed-income access void","Bond markets opaque and dominated by banks; retail investors excluded"),
 ("Insurance penetration void","Very low health/life insurance penetration leaving families exposed to catastrophic costs"),
 ("Financial literacy void","Complex financial products & news inaccessible to most of the population"),
 ("Urban air pollution void","Severe urban air pollution with no affordable clean-air infrastructure"),
 ("Sanitation & hygiene void","Lack of safe sanitation and menstrual hygiene products & facilities"),
 ("Healthy food access void","Food system dominated by ultra-processed products; honest healthy options scarce"),
]
cur.executemany("INSERT INTO voids(name, description) VALUES (?,?)", voids)

sdgs = [(1,"No Poverty"),(2,"Zero Hunger"),(3,"Good Health and Well-being"),(4,"Quality Education"),
        (5,"Gender Equality"),(7,"Affordable and Clean Energy"),(8,"Decent Work and Economic Growth"),
        (9,"Industry, Innovation and Infrastructure"),(10,"Reduced Inequalities"),(11,"Sustainable Cities and Communities"),(12,"Responsible Consumption and Production"),(13,"Climate Action"),(6,"Clean Water and Sanitation")]
cur.executemany("INSERT INTO sdgs(number,title) VALUES (?,?)", sdgs)

# Startup -> void, SDGs
sv = {
 "MNT-Halan": ("Financial exclusion",[1,8,10]),
 "Wave": ("Payments & infrastructure void",[1,8,10]),
 "Oraan": ("Financial exclusion",[5,8,10]),
 "Kidogo": ("Education & childcare void",[4,5,8]),
 "Yellow": ("Energy access",[7,1,10]),
 "Acceso": ("Agricultural market & finance void",[1,2,8]),
 "SmartMoney": ("Payments & infrastructure void",[1,8]),
 "Winich": ("Supply chain void",[1,2,8]),
 "Complete Farmer": ("Agricultural market & finance void",[1,2,8]),
 "Flutterwave": ("Payments & infrastructure void",[8,9,10]),
 "Lula": ("Financial exclusion",[8,9]),
 "Ilara Health / similar healthtech": ("Healthcare access",[3,10]),
 "Puna Bio": ("Agricultural market & finance void",[2,12]),
 "Aerobotics": ("Agricultural market & finance void",[2,8]),
 "Bboxx / off-grid solar cohort": ("Energy access",[7,1,10]),
 "Do Good Points": ("Philanthropic engagement gap",[3,12]),
 "smallcase": ("Retail capital market access void",[8,9,10]),
 "Wint Wealth": ("Bond/fixed-income access void",[8,10]),
 "GoldenPi": ("Bond/fixed-income access void",[8,10]),
 "Ditto Insurance": ("Insurance penetration void",[3,8,10]),
 "Finshots": ("Financial literacy void",[4,8,10]),
 "Praan": ("Urban air pollution void",[3,11,13]),
 "PeeSafe": ("Sanitation & hygiene void",[3,5,6]),
 "The Whole Truth": ("Healthy food access void",[2,3,12]),
}
with open("startups.csv") as f:
    for r in csv.DictReader(f):
        cur.execute("INSERT INTO startups(name,sector,country_region,website,impact_model,stage) VALUES (?,?,?,?,?,?)",
          (r["Name"],r["Sector"],r["Country/Region"],r["Website"],r["Social Impact / Model"],r["Stage"]))
        sid = cur.lastrowid
        vname, sdglist = sv[r["Name"]]
        cur.execute("INSERT INTO startup_voids SELECT ?, id FROM voids WHERE name=?", (sid, vname))
        for n in sdglist:
            cur.execute("INSERT OR IGNORE INTO startup_sdgs SELECT ?, id FROM sdgs WHERE number=?", (sid, n))

iv = {r["Name"]: None for r in csv.DictReader(open("investors.csv"))}
ivmap = {
 "Acumen (incl. Acumen Angel Network)":"Capital access gap (pioneer gap / missing middle)",
 "Toniic":"Capital access gap (pioneer gap / missing middle)",
 "Social Venture Circle (formerly Investors' Circle)":"Capital access gap (pioneer gap / missing middle)",
 "E8 Angels":"Energy access",
 "Angels of Impact":"Capital access gap (pioneer gap / missing middle)",
 "Intellecap / Impact Investment Network (I3N)":"Capital access gap (pioneer gap / missing middle)",
 "Katapult (Katapult VC / Katapult Foundation)":"Capital access gap (pioneer gap / missing middle)",
 "SheEO":"Capital access gap (pioneer gap / missing middle)",
 "Angels for Angels":"Capital access gap (pioneer gap / missing middle)",
 "LeapFrog Investments":"Financial exclusion",
 "Root Capital":"Agricultural market & finance void",
 "NESsT":"Capital access gap (pioneer gap / missing middle)",
 "Accion Venture Lab":"Financial exclusion",
 "Bamboo Capital Partners":"Capital access gap (pioneer gap / missing middle)",
 "Commonwealth":"Capital access gap (pioneer gap / missing middle)",
 "Samir Sathe-type individual angels (India)":"Capital access gap (pioneer gap / missing middle)",
 "Raintree Foundation / Raintree Family Office":"Climate resilience & clean environment void",
 "Rainmatter Capital (Zerodha)":"Capital access gap (pioneer gap / missing middle)",
 "Rainmatter Foundation (Zerodha)":"Climate resilience & clean environment void",
 "Climate Angels":"Climate resilience & clean environment void",
}
with open("investors.csv") as f:
    for r in csv.DictReader(f):
        cur.execute("INSERT INTO investors(name,type,geography,focus_sectors,stage,typical_check_usd,website,notes) VALUES (?,?,?,?,?,?,?,?)",
          (r["Name"],r["Type"],r["Geography"],r["Focus Areas / Sectors"],r["Stage"],
           r["Typical Check Size (USD)"],r["Website"],r["Impact Thesis / Notes"]))
        cur.execute("INSERT INTO investor_voids SELECT ?, id FROM voids WHERE name=?",
          (cur.lastrowid, ivmap[r["Name"]]))

seed = [
 ("Acumen (incl. Acumen Angel Network)","Kidogo","grant/equity",None,None,"Acumen portfolio; Pivotal Ventures follow-on"),
 ("Acumen (incl. Acumen Angel Network)","Yellow","equity",2000000,"2024","Hardest-to-Reach initiative"),
 ("Acumen (incl. Acumen Angel Network)","Acceso","equity",None,None,"Acumen portfolio"),
 ("Root Capital","Acceso","debt",None,None,"illustrative agri-finance edge"),
 ("Rainmatter Capital (Zerodha)","smallcase","equity",None,"2015","Rainmatter portfolio; Wikipedia + rainmatter.org"),
 ("Rainmatter Capital (Zerodha)","Wint Wealth","equity",None,None,"Rainmatter portfolio; Wikipedia Zerodha"),
 ("Rainmatter Capital (Zerodha)","GoldenPi","equity",None,None,"Rainmatter portfolio; Wikipedia Zerodha"),
 ("Rainmatter Capital (Zerodha)","Ditto Insurance","equity",None,None,"Rainmatter portfolio; moneycontrol"),
 ("Rainmatter Capital (Zerodha)","Finshots","equity",None,None,"Rainmatter portfolio; rainmatter.org blog"),
 ("Rainmatter Capital (Zerodha)","PeeSafe","equity",None,None,"Rainmatter portfolio; Entrepreneur India"),
 ("Rainmatter Capital (Zerodha)","The Whole Truth","equity",None,None,"Rainmatter portfolio; Entrepreneur India"),
 ("Climate Angels","Praan","seed",None,"2022-07","Climate Angels portfolio page: seed round July 2022"),
]
for i,s,rd,amt,dt,note in seed:
    cur.execute("""INSERT INTO investments(investor_id,startup_id,round,amount_usd,announced_date,notes)
      SELECT (SELECT id FROM investors WHERE name=?),(SELECT id FROM startups WHERE name=?),?,?,?,?""",(i,s,rd,amt,dt,note))
con.commit()
for t in ["voids","sdgs","investors","startups","startup_voids","startup_sdgs","investor_voids","investments"]:
    print(t, cur.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0])
con.close()
print("OK: tracker.db rebuilt from CSVs")
