"""
Build and run notebooks/worked_example.ipynb: three shop questions answered from the data, then checked against the
truth columns.

Usage (from the repository root, with requirements-dev.txt installed):
    python scripts/make_notebook.py

The cells live in this file, so the notebook is reviewed as code. The script writes the notebook, runs it top to
bottom with a fresh kernel and saves it with outputs. Cell ids and metadata are fixed and timings are not recorded,
so two runs give the same file.
"""
import sys
from pathlib import Path

import nbformat
from nbclient import NotebookClient

PROJECT_DIR = Path(__file__).resolve().parents[1]
NOTEBOOK = PROJECT_DIR / "notebooks" / "worked_example.ipynb"

CELLS = [
    ("md", """# Worked example: three questions, answered and checked

Data Generator writes the answer next to the data: truth columns such as `true_effect`, `customer_segment` and
`is_fraud` hold what an analysis should find. This notebook answers three questions a shop would ask, from the raw
tables, and only then opens the truth to see how close it got.

1. [Did the checkout redesign raise conversion?](#1.-Did-the-checkout-redesign-raise-conversion?) A/B test with a
   sample ratio check.
2. [Which customers come back?](#2.-Which-customers-come-back?) Cohort retention and RFM against the hidden segments.
3. [Which orders are fraud?](#3.-Which-orders-are-fraud?) Rules built from red flags, scored with precision and recall.

The data is the default run (seed 42, 40,000 customers, 80,000 order lines) with English values, generated in memory
in about 5 seconds. `python scripts/make_notebook.py` rebuilds this notebook with its outputs."""),
    ("code", """import math
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.colors import LinearSegmentedColormap
from matplotlib.ticker import MultipleLocator

%matplotlib inline

ROOT = next(path for path in [Path.cwd(), *Path.cwd().parents] if (path / "func").is_dir())
sys.path.insert(0, str(ROOT))

from func import service  # noqa: E402
from ui import theme  # noqa: E402

pd.set_option("display.precision", 3)
plt.rcParams.update({
    "figure.dpi": 100, "savefig.dpi": 100, "font.size": 10, "axes.spines.top": False, "axes.spines.right": False,
    "axes.edgecolor": "#c9d1d3", "axes.labelcolor": theme.MUTED, "xtick.color": theme.MUTED,
    "ytick.color": theme.MUTED, "axes.titleweight": "bold", "axes.titlesize": 12, "axes.titlelocation": "left",
})"""),
    ("code", """params = service.GenerationParams(customers=40_000, products=50_000, order_lines=80_000, seed=42,
                                  language="en")
data = service.generate(params)
{name: len(table) for name, table in data.items()}"""),
    ("md", """## 1. Did the checkout redesign raise conversion?

`checkout_redesign` split web sessions between the old checkout (A) and the new one (B) for nine weeks. Before
reading the result, check that the split itself worked: a sample ratio mismatch (SRM) means the assignment is broken
and the result cannot be trusted, whatever it says."""),
    ("code", """experiments = data["experiment_data"].set_index("experiment_name")
assignments = data["experiment_assignment_data"]
sessions = data["session_data"].set_index("session_id")


def units_of(name):
    return assignments[assignments["experiment_id"] == experiments.loc[name, "experiment_id"]]


def srm_p_value(variants, planned_b):
    \"\"\"Chi-square goodness of fit of the A/B counts against the planned split (1 degree of freedom).\"\"\"
    observed = np.array([(variants == "A").sum(), (variants == "B").sum()])
    expected = np.array([1 - planned_b, planned_b]) * observed.sum()
    chi2 = ((observed - expected) ** 2 / expected).sum()
    return math.erfc(math.sqrt(chi2 / 2))


units = units_of("checkout_redesign")
print(f"B share {(units['variant'] == 'B').mean():.2%} of {len(units):,} sessions, "
      f"SRM p-value {srm_p_value(units['variant'], experiments.loc['checkout_redesign', 'planned_split_b']):.2f}")"""),
    ("md", """The split is 50/50 and the SRM test sees nothing wrong. A random split should also balance what users
bring with them, so the channel and device mix of A and B should match:"""),
    ("code", """visits = sessions.loc[units["unit_id"]].assign(variant=units["variant"].to_numpy())
mix = pd.concat({
    "channel": pd.crosstab(visits["channel"], visits["variant"], normalize="columns"),
    "device": pd.crosstab(visits["device"], visits["variant"], normalize="columns"),
})
mix.assign(gap_pp=(mix["B"] - mix["A"]) * 100).round(3)"""),
    ("md", """The groups look alike, so a difference in conversion can be put down to the checkout. Conversion is
the share of sessions with an order. The lift is B / A - 1 with a 95% confidence interval from the log of the
ratio, and the p-value comes from a two-proportion z-test."""),
    ("code", """def conversion_test(visits):
    converted = visits["order_id"].notna()
    a, b = converted[visits["variant"] == "A"], converted[visits["variant"] == "B"]
    pa, pb = a.mean(), b.mean()
    se_log = math.sqrt((1 - pa) / (pa * len(a)) + (1 - pb) / (pb * len(b)))
    low, high = (math.exp(math.log(pb / pa) + z * se_log) - 1 for z in (-1.96, 1.96))
    pooled = converted.mean()
    z = (pb - pa) / math.sqrt(pooled * (1 - pooled) * (1 / len(a) + 1 / len(b)))
    return {"conversion_A": pa, "conversion_B": pb, "lift": pb / pa - 1, "ci_low": low, "ci_high": high,
            "p_value": math.erfc(abs(z) / math.sqrt(2))}


pd.Series(conversion_test(visits)).map("{:.4f}".format).to_frame("checkout_redesign")"""),
    ("md", """B converts better and the 95% interval stays above zero, so the redesign raised conversion. The interval
is wide, though: the data fits a gain from a few percent to well over ten, which is what nine weeks of traffic can
tell. The same steps on every experiment, with the truth next to them:"""),
    ("code", """rows = []
for name, row in experiments.iterrows():
    units = units_of(name)
    p_srm = srm_p_value(units["variant"], row["planned_split_b"])
    if row["metric"] == "conversion_rate":
        visits = sessions.loc[units["unit_id"]].assign(variant=units["variant"].to_numpy())
        result = conversion_test(visits)
        measured, low, high = result["lift"], result["ci_low"], result["ci_high"]
    else:  # units per order line for customers in the window
        lines = data["order_data"]
        window = sessions[sessions["session_start"].dt.normalize().between(row["start_date"], row["end_date"])]
        variant = units.set_index("unit_id")["variant"]
        in_test = lines[lines["order_id"].isin(window["order_id"].dropna().astype(int))
                        & lines["customer_id"].isin(variant.index)]
        group = in_test["customer_id"].map(variant)
        qa, qb = in_test.loc[group == "A", "quantity"], in_test.loc[group == "B", "quantity"]
        measured = qb.mean() - qa.mean()
        half = 1.96 * math.sqrt(qa.var() / len(qa) + qb.var() / len(qb))
        low, high = measured - half, measured + half
    rows.append({"experiment": name, "metric": row["metric"], "srm_p_value": p_srm, "measured": measured,
                 "ci_low": low, "ci_high": high, "true_effect": row["true_effect"],
                 "srm_planted": row["has_sample_ratio_mismatch"]})
results = pd.DataFrame(rows).set_index("experiment")
results["truth_in_ci"] = results["true_effect"].between(results["ci_low"], results["ci_high"])
results.round(4)"""),
    ("code", """conversion = results[results["metric"] == "conversion_rate"].iloc[::-1]
fig, ax = plt.subplots(figsize=(8, 2.8))
y = np.arange(len(conversion))
ax.hlines(y, conversion["ci_low"], conversion["ci_high"], color=theme.PRIMARY, linewidth=2)
ax.plot(conversion["measured"], y, "o", color=theme.PRIMARY, markersize=8, label="measured lift, 95% CI")
ax.plot(conversion["true_effect"], y, "D", color=theme.ACCENT, markersize=8, label="true effect")
ax.axvline(0, color="#c9d1d3", linewidth=1)
ax.set_yticks(y, [f"{name}{' (SRM)' if srm else ''}" for name, srm in conversion["srm_planted"].items()])
ax.xaxis.set_major_locator(MultipleLocator(0.04))
ax.xaxis.set_major_formatter(lambda value, _: f"{value:+.0%}")
held = conversion["truth_in_ci"].sum()
ax.set_title(f"{held} of {len(conversion)} intervals hold the true conversion lift")
ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.15), ncol=2, frameon=False, fontsize=9)
ax.grid(axis="x", color="#eef1f2")
fig.tight_layout()"""),
    ("md", """**Against the truth.** Every confidence interval contains `true_effect`, as about 95 in 100 of them
should. Three lessons sit in the table:

- `free_shipping_banner` fails the SRM check (B got about 46% of the sessions instead of 50%) and
  `has_sample_ratio_mismatch` confirms it was planted. Its lift looks like a win, and it must not be reported: once
  the split is broken, nothing guarantees that A and B differ only by the banner.
- `search_ranking_aa` is an A/A test with no effect. Its estimate lands several percent from zero and the interval
  still holds zero: that is the size of the noise in a four-week test.
- `recommendation_widget` measures units per order line for customers rather than conversion per session, and
  the true +0.12 units sits inside its interval too."""),
    ("md", """## 2. Which customers come back?

A cohort is the month of a customer's first order. Retention in month *k* is the share of a cohort that orders again
*k* months later. One trap first: the shop is older than the data. `signup_date` in `customer_data` goes back to
2019, so for some customers the first order in the data is not their first order ever, and counting them would
inflate the early cohorts. The cohorts below keep only customers who signed up within the period."""),
    ("code", """orders = (data["sales_data"].groupby("order_id")
          .agg(customer_id=("customer_id", "first"), order_date=("order_date", "first"),
               value=("revenue_gross", "sum")))
month = orders["order_date"].dt.to_period("M")
first_month = month.groupby(orders["customer_id"]).transform("min")
orders["cohort"], orders["age_months"] = first_month, (month - first_month).apply(lambda offset: offset.n)
signup = data["customer_data"].set_index("customer_id")["signup_date"]
new_customers = orders["customer_id"].map(signup) >= orders["order_date"].min()
print(f"{new_customers.groupby(orders['customer_id']).first().mean():.0%} of the customers who ordered signed up "
      "within the period")

active = (orders[new_customers].groupby(["cohort", "age_months"])["customer_id"].nunique()
          .unstack(fill_value=0))
retention = active.div(active[0], axis=0).loc[:, 1:12]
retention = retention[retention.index <= retention.index.max() - 12]  # cohorts with 12 full months
retention.mean().rename("mean retention").to_frame().T.round(3)"""),
    ("code", """fig, ax = plt.subplots(figsize=(8, 4.2))
teal = LinearSegmentedColormap.from_list("teal", theme.TEAL[:9])  # one hue, light to dark
image = ax.imshow(retention.to_numpy(), cmap=teal, vmin=0, aspect="auto")
ax.set_xticks(range(12), range(1, 13))
ax.set_yticks(range(len(retention)), [str(period) for period in retention.index])
ax.set_xlabel("months after the first order")
ax.set_title(f"{retention[1].mean():.0%} of new customers order again the next month, "
             f"{retention[12].mean():.0%} a year later")
fig.colorbar(image, ax=ax, format=lambda value, _: f"{value:.0%}", shrink=0.8)
fig.tight_layout()"""),
    ("md", """Retention drops after the first month and then flattens. The dark diagonal is November 2023: every cohort
orders more in the Black Friday month, whatever its age, so seasonality shows up inside a cohort table too.
Retention flattens because a core of customers keeps buying while most never return. RFM puts a score on that:
recency (days since the last order), frequency (orders) and monetary value (revenue), each split into quintiles from
1 to 5 over the customers who ordered."""),
    ("code", """end = orders["order_date"].max()
rfm = orders.groupby("customer_id").agg(last_order=("order_date", "max"), frequency=("value", "size"),
                                        monetary=("value", "sum"))
rfm["recency_days"] = (end - rfm.pop("last_order")).dt.days
rfm["R"] = pd.qcut(rfm["recency_days"].rank(method="first"), 5, labels=[5, 4, 3, 2, 1]).astype(int)
rfm["F"] = pd.qcut(rfm["frequency"].rank(method="first"), 5, labels=[1, 2, 3, 4, 5]).astype(int)
rfm["M"] = pd.qcut(rfm["monetary"].rank(method="first"), 5, labels=[1, 2, 3, 4, 5]).astype(int)
rfm["rfm_group"] = pd.cut(rfm[["R", "F", "M"]].sum(axis=1), [2, 6, 9, 12, 15],
                          labels=["at risk", "occasional", "steady", "best"])
rfm["rfm_group"].value_counts().sort_index()"""),
    ("md", """**Against the truth.** `customer_segment` in `customer_data` is the behaviour each customer was given
when the data was generated. How do the RFM groups line up with it?"""),
    ("code", """segments = data["customer_data"].set_index("customer_id")["customer_segment"]
order = ["one_time", "occasional", "regular", "deal_hunter", "loyal"]
truth = pd.crosstab(rfm["rfm_group"], segments.reindex(rfm.index), normalize="index")[order]
truth.round(2)"""),
    ("code", """revenue_by_segment = orders.groupby(orders["customer_id"].map(segments))["value"].sum()
revenue_share = revenue_by_segment / orders["value"].sum()
customers_share = segments.reindex(rfm.index).value_counts(normalize=True)
pd.DataFrame({"share_of_customers": customers_share, "share_of_revenue": revenue_share}).loc[order].round(3)"""),
    ("md", """Three numbers per customer recover much of the hidden behaviour: the best RFM group is mostly loyal and
regular customers, and the at-risk group mostly one-time and occasional buyers. Deal hunters also land among the
best, because they buy often. RFM sees how much they buy, not that they wait for a discount; the share of discounted
lines per customer (`discount_rate` in `sales_data`) would set them apart. Loyal customers are a small part of the
base and bring an outsized share of revenue."""),
    ("md", """## 3. Which orders are fraud?

The shop wants a short list of orders to hold for review. Four red flags come from the order itself, without the
truth:

- shipped to a postal code other than the customer's own,
- paid by card,
- worth more than 95% of all orders,
- the customer placed two or more orders within three days."""),
    ("code", """sales = data["sales_data"]
order_view = (sales.groupby("order_id")
              .agg(customer_id=("customer_id", "first"), ordered_at=("order_datetime", "first"),
                   value=("revenue_gross", "sum"), payment=("payment_method", "first"),
                   ship_to=("shipping_postal_code", "first"), home=("postal_code", "first"))
              .sort_values("ordered_at"))
burst = (order_view.reset_index().set_index("ordered_at").groupby("customer_id")["order_id"]
         .rolling("3D").count().rename("orders_in_3_days").reset_index())
order_view = order_view.reset_index().merge(burst, on=["customer_id", "ordered_at"]) \\
    .drop_duplicates("order_id").set_index("order_id")

flags = pd.DataFrame({
    "other_address": order_view["ship_to"] != order_view["home"],
    "card": order_view["payment"] == "Card",
    "high_value": order_view["value"] > order_view["value"].quantile(0.95),
    "burst": order_view["orders_in_3_days"] >= 2,
})
flags.mean().rename("share of orders").round(3)"""),
    ("md", """Each flag alone catches far too many honest orders: people send gifts to other addresses and pay by card
every day. Together they narrow the list. **Against the truth**, `is_fraud` in `order_data` scores each rule:"""),
    ("code", """is_fraud = data["order_data"].groupby("order_id")["is_fraud"].first().reindex(flags.index)
rules = {
    "other address": flags["other_address"],
    "other address + card": flags["other_address"] & flags["card"],
    "other address + card + high value": flags["other_address"] & flags["card"] & flags["high_value"],
    "all four flags": flags.all(axis=1),
    "at least three flags": flags.sum(axis=1) >= 3,
}
scores = pd.DataFrame({
    name: {"flagged": rule.sum(), "fraud caught": (rule & is_fraud).sum(),
           "precision": (rule & is_fraud).sum() / max(rule.sum(), 1),
           "recall": (rule & is_fraud).sum() / is_fraud.sum()}
    for name, rule in rules.items()}).T
scores.round(3)"""),
    ("md", """No rule catches every ring, because no sign is always there. Rings also send parcels to a locker in the
customer's own postal code, pay with BLIK or a deferred payment and often start with a cheap test order, while
honest customers keep shipping to a second address of their own. The rules trade one error for the other: all four
flags give an almost clean list that misses about half of the fraud, and three of four flags catch most of it at
the cost of reviewing honest orders too. `anomaly_data` lists every ring with its dates and addresses, which helps
to see which orders a rule missed and why."""),
]


def build() -> nbformat.NotebookNode:
    notebook = nbformat.v4.new_notebook()
    notebook.metadata = {"kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
                         "language_info": {"name": "python"}}
    for number, (kind, source) in enumerate(CELLS, start=1):
        cell = (nbformat.v4.new_markdown_cell if kind == "md" else nbformat.v4.new_code_cell)(source)
        cell.id = f"cell-{number:02d}"
        notebook.cells.append(cell)
    return notebook


def main() -> None:
    notebook = build()
    client = NotebookClient(notebook, timeout=600, kernel_name="python3", record_timing=False,
                            resources={"metadata": {"path": str(NOTEBOOK.parent)}})
    client.execute()
    for cell in notebook.cells:
        cell.metadata = {}
    notebook.metadata = {"kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
                         "language_info": {"name": "python"}}
    NOTEBOOK.write_text(nbformat.writes(notebook) + "\n", encoding="utf-8", newline="\n")
    print(f"{NOTEBOOK.relative_to(PROJECT_DIR)}: {NOTEBOOK.stat().st_size / 1024:.0f} KB")


if __name__ == "__main__":
    if sys.platform == "win32":  # pyzmq needs a selector event loop on Windows
        import asyncio

        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    sys.exit(main())
