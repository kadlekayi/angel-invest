#!/usr/bin/env python3
"""
THE PATIENT CAPITAL GAME - ESG investor simulator (prototype)

An angel/family-office simulation played in the terminal. All companies,
voids, and outcomes are drawn from the real-world tracker database
(../tracker.db built by ../build_db.py).

Quick play:   python3 esg_game.py
Auto-play:     python3 esg_game.py --auto [elevar|rainmatter|raintree|balanced]

Design notes (mapping ESG frameworks to mechanics):
  - IRIS+/GIIN style KPIs -> each deal carries impact KPIs aggregated into an Impact Score
  - SDG coverage constraint -> LP mandate requires breadth (min distinct SDGs)
  - Pioneer gap -> high-impact deals are illiquid & risky; commercial deals dilute impact
  - Five Dimensions of Impact (Impact Frontiers) -> WHAT/WHO/HOW MUCH/CONTRIBUTION/RISK scoring
  - Real narratives: Elevar (thesis patience + exits), Rainmatter (permanent capital,
    ecosystem drip), Raintree (blended catalytic capital) are playable strategies with
    historically-shaped payoff curves.
"""
import sqlite3, random, sys, os

DB = os.path.join(os.path.dirname(__file__), "..", "tracker.db")

# ----------------------------------------------------------------------------
# Load the world from the real tracker
# ----------------------------------------------------------------------------
def load_world():
    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    cur = con.cursor()

    startups = {}
    for r in cur.execute("""
        SELECT s.id, s.name, s.sector, s.country_region, s.impact_model, s.stage,
               v.name AS void_name,
               (SELECT GROUP_CONCAT(g.number) FROM startup_sdgs ss JOIN sdgs g ON g.id=ss.sdg_id
                 WHERE ss.startup_id = s.id) AS sdgs
        FROM startups s JOIN startup_voids sv ON sv.startup_id=s.id JOIN voids v ON v.id=sv.void_id"""):
        startups[r["name"]] = dict(r)

    # Hand-tuned game parameters per company (drawn from real-world narratives)
    # risk = P(serious trouble/yr), impact = IRIS-style depth (0-10),
    # growth = expected value multiple over 10 yrs, liquidity = can exit early?
    TUNING = {
        # Elevar portfolio: patient, crisis-exposed, huge payoffs
        "Ujjivan Financial Services": dict(cost=2.0, risk=0.25, impact=9, growth=6.0, liquidity=2,
            kpi="3.7M+ customers", crisis="2010 AP microfinance crisis: sector collapse risk"),
        "Shubham Housing Finance": dict(cost=1.5, risk=0.15, impact=8, growth=4.5, liquidity=2,
            kpi="100k households financed in 13 states"),
        "Varthana": dict(cost=1.0, risk=0.35, impact=7, growth=3.0, liquidity=1,
            kpi="97.5% collection efficiency post-COVID"),
        "SarvaGram": dict(cost=1.0, risk=0.25, impact=7, growth=3.0, liquidity=1,
            kpi="rural households reached via last-mile network"),
        "Indifi Technologies": dict(cost=1.0, risk=0.30, impact=6, growth=3.5, liquidity=1,
            kpi="MSMEs underwritten without collateral"),
        "Vistaar Financial Services": dict(cost=1.5, risk=0.20, impact=6, growth=4.0, liquidity=2,
            kpi="semi-urban MSME loan book"),
        "Afluenta": dict(cost=0.8, risk=0.40, impact=6, growth=2.5, liquidity=1,
            kpi="thin-file LatAm borrowers funded"),
        "Nia.one": dict(cost=0.5, risk=0.50, impact=7, growth=2.0, liquidity=0,
            kpi="migrant workers housed near factories"),
        # Rainmatter portfolio: ecosystem, drip-funded, low liquidity forever
        "smallcase": dict(cost=0.8, risk=0.20, impact=5, growth=4.0, liquidity=0,
            kpi="retail portfolios diversified"),
        "Ditto Insurance": dict(cost=0.6, risk=0.25, impact=7, growth=3.0, liquidity=0,
            kpi="underinsured families covered"),
        "Finshots": dict(cost=0.4, risk=0.15, impact=6, growth=2.5, liquidity=0,
            kpi="millions financially literate via newsletter"),
        "The Whole Truth": dict(cost=0.5, risk=0.30, impact=4, growth=2.0, liquidity=0,
            kpi="honest-label food products sold"),
        # Global South fintech/energy: high growth, commercial-ish
        "Flutterwave": dict(cost=2.5, risk=0.30, impact=4, growth=8.0, liquidity=3,
            kpi="Africa payment rails"),
        "MNT-Halan": dict(cost=2.0, risk=0.35, impact=6, growth=6.0, liquidity=2,
            kpi="unbanked Egyptians served"),
        "Wave": dict(cost=2.0, risk=0.35, impact=7, growth=5.0, liquidity=2,
            kpi="low-fee mobile money users"),
        "Yellow": dict(cost=0.8, risk=0.30, impact=7, growth=3.0, liquidity=1,
            kpi="off-grid solar homes, hardest-to-reach"),
        # Philanthropic / catalytic bucket (Raintree style)
        "Kidogo": dict(cost=0.5, risk=0.30, impact=8, growth=0.5, liquidity=0, catalytic=True,
            kpi="children in affordable quality childcare"),
        "Acceso": dict(cost=1.0, risk=0.25, impact=7, growth=2.0, liquidity=1,
            kpi="smallholders linked to premium markets"),
        "Praan": dict(cost=0.5, risk=0.45, impact=6, growth=2.0, liquidity=0,
            kpi="PM2.5 reduced in public spaces"),
        "PeeSafe": dict(cost=0.4, risk=0.25, impact=5, growth=2.0, liquidity=0,
            kpi="menstrual hygiene access"),
    }
    for name, t in TUNING.items():
        if name in startups:
            startups[name].update(t)
    con.close()
    # only keep fully-tuned playable companies
    return {n: s for n, s in startups.items() if "cost" in s}

# ----------------------------------------------------------------------------
# Event deck - materiality made mechanical
# ----------------------------------------------------------------------------
EVENTS = [
    ("Monsoon failure", "Agricultural & rural portfolios hit: any agri/rural holding loses 20% value and impact delivery drops this year.", "agri"),
    ("Andhra-Pradesh-style regulatory shock", "Microfinance-type holdings face a crisis year: 50% value drawdown, but survivors that hold get a 2x recovery kicker later (the Elevar story).", "microfinance"),
    ("Climate event: floods + heatwave", "Climate-resilience holdings (energy access, climate tech) gain +1 impact; unadapted rural holdings lose impact delivery.", "climate"),
    ("New air-quality regulation", "Clean-air ventures (e.g., Praan) see demand surge: value +30%.", "air"),
    ("LP ESG audit", "Your LPs audit the portfolio: if SDG coverage < 4 distinct goals, mandate breached (financial floor rises 2pp).", "audit"),
    ("Macroeconomic downturn", "All holdings -15% value this year; catalytic/grant bucket impact counts double this year (safety nets matter in downturns).", "macro"),
    ("Impact measurement scandal", "One random holding is caught inflating KPIs: its impact contribution is zeroed. Lesson: verify IRIS reporting.", "scandal"),
    ("Bull market for fintech", "Fintech holdings +25% value. IPO window opens: liquid holdings (liquidity>=2) may exit at bonus valuations.", "bull"),
]

# ----------------------------------------------------------------------------
# Five Dimensions of Impact scoring (simplified to numeric contributions)
#   WHAT, WHO, HOW MUCH, CONTRIBUTION, RISK — each 0..2 per deal
# ----------------------------------------------------------------------------
def five_dimensions(deal, catalytic_capital_deployed):
    s = deal["world"]
    what = 2 if s["impact"] >= 7 else (1 if s["impact"] >= 5 else 0)
    who = 2 if "India" in (s["country_region"] or "") or "Africa" in (s["country_region"] or "") or "Latin" in (s["country_region"] or "") else 1
    how_much = 2 if s["impact"] >= 8 else 1
    contribution = 2 if (s.get("catalytic") or s["risk"] >= 0.35) else 1   # pioneer-gap capital counts more
    risk = 0 if s["risk"] >= 0.4 else (1 if s["risk"] >= 0.25 else 2)      # lower residual risk = better score
    return what + who + how_much + contribution + risk

# ----------------------------------------------------------------------------
# Game state
# ----------------------------------------------------------------------------
class Game:
    def __init__(self, strategy=None, auto=False):
        self.world = load_world()
        self.strategy = strategy          # None = manual play
        self.auto = auto
        self.cash = 10.0                  # $10M
        self.year = 0
        self.portfolio = []               # list of dicts
        self.grants = []                  # catalytic bucket
        self.exit_proceeds = 0.0
        self.drip = 0.4                   # Rainmatter-style: drip income per year (bootstrapped profit share)
        self.mandate_min_sdgs = 4
        self.financial_floor_irr = 0.08
        self.audit_flag = False
        self.log = []

    def available_deals(self):
        return [s for s in self.world.values()
                if s["name"] not in [p["world"]["name"] for p in self.portfolio + self.grants]]

    # ---- player actions ----
    def invest(self, name):
        s = self.world[name]
        cost = s["cost"]
        if cost > self.cash:
            return f"Not enough cash: {s['name']} costs ${cost:.1f}M."
        self.cash -= cost
        deal = dict(world=s, entry_year=self.year, entry_cost=cost, in_crisis=False, crisis_kicker=False)
        (self.grants if s.get("catalytic") else self.portfolio).append(deal)
        return f"Invested ${cost:.1f}M in {s['name']} ({s['void_name']})."

    def exit(self, idx):
        deal = self.portfolio[idx]
        held = self.year - deal["entry_year"]
        mult = 1.0 + (deal["world"]["growth"] - 1.0) * (held / 10.0)
        if deal.get("crisis_kicker"):
            mult *= 2.0   # recovery kicker (Elevar pattern)
        if deal["in_crisis"]:
            mult *= 0.5
        proceeds = deal["entry_cost"] * mult
        self.exit_proceeds += proceeds
        del self.portfolio[idx]
        return f"Exited {deal['world']['name']}: ${proceeds:.2f}M returned ({held}yr hold)."

    # ---- yearly tick ----
    def apply_event(self):
        ev = random.choice(EVENTS)
        tag = ev[2]
        for d in self.portfolio:
            w = d["world"]
            sector = (w["sector"] or "").lower()
            if tag == "agri" and ("agri" in sector or "rural" in sector):
                d["value_shock"] = d.get("value_shock", 1.0) * 0.8
            elif tag == "microfinance" and ("microfinance" in sector or "housing" in sector or "msme" in sector):
                d["in_crisis"] = True; d["crisis_kicker"] = True
            elif tag == "bull" and "fintech" in sector:
                d["value_shock"] = d.get("value_shock", 1.0) * 1.25
            elif tag == "air" and "air" in sector:
                d["value_shock"] = d.get("value_shock", 1.0) * 1.3
        if tag == "audit":
            if len(self.sdg_coverage()) < self.mandate_min_sdgs:
                self.audit_flag = True
        if tag == "scandal" and self.portfolio:
            victim = random.choice(self.portfolio); victim["impact_zeroed"] = True
        return ev[0], ev[1]

    def sdg_coverage(self):
        sdgs = set()
        for d in self.portfolio + self.grants:
            if d["world"].get("sdgs"):
                sdgs.update(int(x) for x in d["world"]["sdgs"].split(","))
        return sorted(sdgs)

    def portfolio_value(self):
        total = self.cash + self.exit_proceeds
        for d in self.portfolio:
            held = self.year - d["entry_year"]
            mult = 1.0 + (d["world"]["growth"] - 1.0) * (held / 10.0)
            if d.get("crisis_kicker"): mult *= 2.0
            if d.get("in_crisis") and held >= 8: mult *= 1.0  # recovered by year 8 of hold
            elif d.get("in_crisis"): mult *= 0.5
            mult *= d.get("value_shock", 1.0)
            total += d["entry_cost"] * mult
        return total

    def impact_score(self):
        score = 0.0
        for d in self.portfolio + self.grants:
            if d.get("impact_zeroed"): continue
            base = five_dimensions(d, self.grants)  # 0-10
            score += base * (2.0 if d["world"].get("catalytic") and self.year >= 7 else 1.0)
        return score

    # ---- AI strategies (auto-play) ----
    def auto_move(self):
        deals = self.available_deals()
        if self.strategy == "elevar":
            # thesis: highest five-dimension impact deals first, hold forever
            deals.sort(key=lambda s: -(s["impact"] + (1 if s["risk"] >= 0.3 else 0)))
        elif self.strategy == "rainmatter":
            # ecosystem drip: reinvest drip, prefer fintech/low-liquidity ecosystem plays
            deals.sort(key=lambda s: (0 if "fintech" in (s["sector"] or "").lower() else 1, -s["impact"]))
        elif self.strategy == "raintree":
            # blended: catalytic bucket first, then climate
            deals.sort(key=lambda s: (0 if s.get("catalytic") else (1 if "climate" in (s["sector"] or "").lower() else 2), -s["impact"]))
        else:  # balanced
            deals.sort(key=lambda s: -(s["growth"] * 0.5 + s["impact"]))
        for s in deals:
            if s["cost"] <= self.cash:
                return s["name"]
        return None

    def play(self):
        print("=" * 70)
        print("THE PATIENT CAPITAL GAME — you manage $10M with an ESG mandate")
        print(f"Strategy: {self.strategy or 'MANUAL'} | 10 rounds | "
              f"IRP floor 8% | SDG coverage >= {self.mandate_min_sdgs}")
        print("=" * 70)
        for year in range(1, 11):
            self.year = year
            self.cash += self.drip          # Rainmatter-style annual capital drip
            ev_name, ev_desc = self.apply_event()
            self.log.append((year, ev_name))
            print(f"\n--- YEAR {year} | cash ${self.cash:.1f}M | event: {ev_name}")
            print(f"    {ev_desc}")

            for _ in range(2):              # up to 2 actions per year
                if self.auto:
                    name = self.auto_move()
                    if name:
                        print("   " + self.invest(name))
                    break
                # manual UI
                print(f"\n   Portfolio: {[d['world']['name'] for d in self.portfolio]}"
                      f"{' | grants: ' + str([d['world']['name'] for d in self.grants]) if self.grants else ''}")
                deals = self.available_deals()
                for i, s in enumerate(deals[:8]):
                    print(f"   [{i}] {s['name']:<32} ${s['cost']:.1f}M  risk={s['risk']:.2f} "
                          f"impact={s['impact']}/10  growth=x{s['growth']:.1f}  "
                          f"{'CATALYTIC ' if s.get('catalytic') else ''}{s['void_name'][:30]}")
                for j, d in enumerate(self.portfolio):
                    print(f"   [e{j}] EXIT {d['world']['name']}")
                cmd = input("   invest number / eN to exit / [enter]=skip / q=quit: ").strip()
                if cmd == "q": return self.report()
                if cmd.startswith("e") and cmd[1:].isdigit():
                    print("   " + self.exit(int(cmd[1:])))
                elif cmd.isdigit() and int(cmd) < len(deals):
                    print("   " + self.invest(deals[int(cmd)]["name"]))
                elif cmd == "":
                    break
        return self.report()

    def report(self):
        pv = self.portfolio_value()
        irr_proxy = (pv / 10.0) ** (1 / 10) - 1
        impact = self.impact_score()
        sdgs = self.sdg_coverage()
        print("\n" + "=" * 70)
        print("FINAL OUTCOME REPORT — three axes")
        print("=" * 70)
        print(f"FINANCIAL   : portfolio ${pv:.1f}M  |  ~IRR proxy {irr_proxy*100:.1f}% "
              f"{'(met 8% floor)' if irr_proxy >= 0.08 else '(BREACHED floor)'}"
              f"{'  [audit note: SDG mandate breached in a prior year -> floor was raised 2pp]' if self.financial_floor_irr > 0.08 else ''}")
        print(f"IMPACT      : five-dimensions score {impact:.0f}/100  "
              f"({len(self.portfolio)} investments, {len(self.grants)} catalytic grants)")
        print(f"SDG COVERAGE: {sdgs if sdgs else 'none'}  "
              f"{'OK' if len(sdgs) >= self.mandate_min_sdgs else 'MANDATE BREACHED'}")
        systemic = "voids handed to commercial capital at exit (Elevar 'commercialize then hand over' pattern)" if self.exit_proceeds > 5 else "permanent-capital ecosystem held (Rainmatter pattern: no exits, compounding service)" if len(self.portfolio) >= 6 else "still frontier capital - voids not yet institutionalized"
        print(f"SYSTEMIC    : {systemic}")
        print("\nEvents survived:", "; ".join(f"Y{y}: {n}" for y, n in self.log))
        floor = self.financial_floor_irr
        if irr_proxy >= floor and impact >= 40 and self.exit_proceeds > 5:
            verdict = "WIN (Elevar pattern): trade-off beaten AND voids institutionalized via commercial exits"
        elif irr_proxy >= floor and impact >= 40 and len(self.portfolio) >= 6:
            verdict = "WIN (Rainmatter pattern): sustainable returns via permanent-capital ecosystem, exits unnecessary"
        elif irr_proxy >= floor and impact >= 40:
            verdict = "WIN (Raintree pattern): blended capital delivered both axes; some voids needed philanthropy"
        elif impact >= 40:
            verdict = "LOSS: impact strong but capital not sustainable (IRR below floor)"
        elif irr_proxy >= floor:
            verdict = "LOSS: financially fine but ESG mandate failed on impact"
        else:
            verdict = "DOUBLE FAILURE: neither axis met"
        print("\nVERDICT:", verdict)
        return dict(pv=pv, irr=irr_proxy, impact=impact, sdgs=sdgs)


if __name__ == "__main__":
    strategy = None; auto = False
    if "--auto" in sys.argv:
        auto = True
        i = sys.argv.index("--auto")
        if len(sys.argv) > i + 1 and sys.argv[i + 1] in ("elevar", "rainmatter", "raintree", "balanced"):
            strategy = sys.argv[i + 1]
        else:
            strategy = "balanced"
    Game(strategy=strategy, auto=auto).play()
