# The Patient Capital Game

An ESG investor simulation built directly on the tracker database (`../tracker.db`).
You manage $10M over 10 years under an ESG mandate: beat an 8% return floor *and*
deliver measurable social/environmental outcomes, or your LPs walk.

## Play

```bash
cd game/
python3 esg_game.py                 # manual play (invest / exit / pass each year)
python3 esg_game.py --auto elevar   # watch the AI play a strategy
python3 esg_game.py --auto rainmatter
python3 esg_game.py --auto raintree
python3 esg_game.py --auto balanced
```

## How ESG frameworks become mechanics

| Framework (class) | Game mechanic |
|---|---|
| IRIS+ / GIIN impact metrics | Every deal carries a real-world KPI (e.g., Varthana's 97.5% collection efficiency, Shubham's 100k households); the "Impact measurement scandal" event zeroes a holding's impact if you didn't verify reporting |
| SDG alignment | LP mandate requires coverage of ≥4 distinct SDGs; breach raises your return floor (audit event) |
| Five Dimensions of Impact (Impact Frontiers) | Each deal scored on WHAT / WHO / HOW MUCH / CONTRIBUTION / RISK; pioneer-gap deals score higher on contribution |
| Materiality / event risk | Yearly event cards keyed to the institutional void each sector fills (monsoon failure hits agri; regulatory shock hits microfinance — the real 2010 AP crisis pattern Elevar survived) |
| Pioneer gap / missing middle | High-impact deals are illiquid and risky; commercial deals dilute impact. Both extremes lose |
| Impact-weighted deal terms | Governance axis: permanent capital (no-exit, Rainmatter) vs exit-mandate structures changes what you can hold through |

## The three real-world strategies

- **Elevar** (thesis-driven patience): buy the highest-impact deals, survive the regulatory crisis card, exit to commercial buyers. Win condition: "beyond trade-offs" + voids institutionalized via exits (Ujjivan IPO, Shubham→LeapFrog, Vistaar→Warburg).
- **Rainmatter** (permanent capital ecosystem): annual capital drip (10% of profits), never exit, compound ecosystem value. Win condition: sustainable returns with a large held portfolio.
- **Raintree** (blended catalytic): catalytic grants score zero financial return but double impact in downturns and unlock otherwise-unfundable voids. Win condition: both axes met with philanthropy in the mix.

All companies, voids, SDGs, and historical outcomes in the deck are drawn from the
real tracker: if it's in the game, it's a real venture filling a real institutional void.
