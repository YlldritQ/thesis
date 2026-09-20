"""Generate notebooks/01_eda.ipynb programmatically (reliable JSON via nbformat)."""

from pathlib import Path

import nbformat as nbf

nb = nbf.v4.new_notebook()
cells = []


def md(text: str) -> None:
    cells.append(nbf.v4.new_markdown_cell(text))


def code(text: str) -> None:
    cells.append(nbf.v4.new_code_cell(text))


md(
    "# Kosovo Public Procurement — Exploratory Data Analysis\n"
    "\n"
    "**Source:** [Open Contracting Partnership — Publication 115]"
    "(https://data.open-contracting.org/en/publication/115) "
    "(publisher: Kosovo Public Procurement Regulatory Commission, OCDS format).\n"
    "\n"
    "**Purpose of this notebook:** understand the shape, coverage and quality of "
    "the data before any modelling. Decisions about features and anomaly-detection "
    "strategy should flow from what we learn here.\n"
    "\n"
    "**Unit:** each row below is a compiled-release/tender record, not evidence "
    "of a signed, executed or paid contract."
)

code(
    "import json\n"
    "from pathlib import Path\n"
    "\n"
    "import matplotlib.pyplot as plt\n"
    "import numpy as np\n"
    "import pandas as pd\n"
    "import seaborn as sns\n"
    "from thesis.domain.procedures import classify_procedure\n"
    "\n"
    "sns.set_theme(style='whitegrid', context='notebook')\n"
    "plt.rcParams['figure.figsize'] = (10, 5)\n"
    "pd.set_option('display.max_columns', 50)\n"
    "pd.set_option('display.width', 160)\n"
    "\n"
    "RAW_PATH = Path('..') / 'data' / 'raw' / 'kosovo_ocds.jsonl'\n"
    "print('Raw file exists:', RAW_PATH.exists(), '| size (MB):', round(RAW_PATH.stat().st_size / 1e6, 1))"
)

md(
    "## 1. Load and flatten the OCDS records\n"
    "\n"
    "Each line in the JSONL is one *compiled release* — a contracting process "
    "containing a `tender` object, a `parties` array, and metadata. We pull the "
    "fields that matter for EDA into a flat DataFrame; nested raw JSON stays "
    "available on disk for later deep-dives."
)

code(
    "def extract_row(rec: dict) -> dict:\n"
    "    tender = rec.get('tender') or {}\n"
    "    value = tender.get('value') or {}\n"
    "    period = tender.get('tenderPeriod') or {}\n"
    "    procuring = (tender.get('procuringEntity') or {}).get('party') or {}\n"
    "    parties = rec.get('parties') or []\n"
    "    roles = [set(p.get('roles') or []) for p in parties]\n"
    "    tenderers = tender.get('tenderers')\n"
    "    role_count = sum('tenderer' in role for role in roles)\n"
    "    if isinstance(tenderers, list):\n"
    "        num_bidders, bidder_data_observed = len(tenderers), True\n"
    "    elif role_count > 0:\n"
    "        num_bidders, bidder_data_observed = role_count, True\n"
    "    else:\n"
    "        num_bidders, bidder_data_observed = None, False\n"
    "    return {\n"
    "        'ocid': rec.get('ocid'),\n"
    "        'release_date': rec.get('date'),\n"
    "        'tender_id': tender.get('id'),\n"
    "        'title': tender.get('title'),\n"
    "        'status': tender.get('status'),\n"
    "        'category': tender.get('mainProcurementCategory'),\n"
    "        'method': tender.get('procurementMethod'),\n"
    "        'method_details': tender.get('procurementMethodDetails'),\n"
    "        'procedure_subtype': classify_procedure(\n"
    "            tender.get('procurementMethod'), tender.get('procurementMethodDetails'),\n"
    "            tender.get('id')),\n"
    "        'award_criteria': tender.get('awardCriteria'),\n"
    "        'estimated_value_eur': value.get('amount'),\n"
    "        'currency': value.get('currency'),\n"
    "        'start_date': period.get('startDate'),\n"
    "        'end_date': period.get('endDate'),\n"
    "        'duration_days': period.get('durationInDays'),\n"
    "        'procuring_entity_id': procuring.get('id'),\n"
    "        'procuring_entity_name': procuring.get('name'),\n"
    "        'num_bidders': num_bidders,\n"
    "        'bidder_data_observed': bidder_data_observed,\n"
    "        'num_suppliers': sum('supplier' in r for r in roles),\n"
    "        'num_parties': len(parties),\n"
    "    }\n"
    "\n"
    "\n"
    "rows = []\n"
    "with open(RAW_PATH) as f:\n"
    "    for line in f:\n"
    "        rows.append(extract_row(json.loads(line)))\n"
    "\n"
    "df = pd.DataFrame(rows)\n"
    "df['release_date'] = pd.to_datetime(df['release_date'], errors='coerce', utc=True)\n"
    "df['start_date'] = pd.to_datetime(df['start_date'], errors='coerce', utc=True)\n"
    "df['end_date'] = pd.to_datetime(df['end_date'], errors='coerce', utc=True)\n"
    "df['year'] = df['release_date'].dt.year\n"
    "print(df.shape)\n"
    "df.head(3)"
)

md("## 2. Schema and missingness")

code(
    "print('Dtypes:')\n"
    "print(df.dtypes)\n"
    "print('\\nMissing values (% of rows):')\n"
    "(df.isna().mean() * 100).round(2).sort_values(ascending=False)"
)

md(
    "## 3. Temporal coverage\n"
    "\n"
    "How many tender records are published per year? Are recent years complete? "
    "A sharp drop in the tail usually means the latest year is partial."
)

code(
    "yearly = df.groupby('year').size().rename('tenders').to_frame()\n"
    "yearly['estimated_eur_mn'] = df.groupby('year')['estimated_value_eur'].sum().div(1e6).round(1)\n"
    "display(yearly)\n"
    "\n"
    "fig, axes = plt.subplots(1, 2, figsize=(14, 4.5))\n"
    "yearly['tenders'].plot(kind='bar', ax=axes[0], color='steelblue')\n"
    "axes[0].set_title('Number of tender records per year')\n"
    "axes[0].set_ylabel('count')\n"
    "yearly['estimated_eur_mn'].plot(kind='bar', ax=axes[1], color='darkorange')\n"
    "axes[1].set_title('Total estimated tender value per year (EUR, millions)')\n"
    "axes[1].set_ylabel('EUR (mn)')\n"
    "plt.tight_layout();"
)

md("## 4. Procurement categories and methods")

code(
    "fig, axes = plt.subplots(1, 2, figsize=(14, 4.5))\n"
    "df['category'].value_counts().plot(kind='barh', ax=axes[0], color='teal')\n"
    "axes[0].set_title('Main procurement category')\n"
    "df['method'].value_counts().plot(kind='barh', ax=axes[1], color='indianred')\n"
    "axes[1].set_title('Procurement method')\n"
    "plt.tight_layout();"
)

code("df['method_details'].value_counts().head(15).to_frame('count')")

md(
    "## 5. Estimated tender-value distribution\n"
    "\n"
    "Published tender estimates are extremely skewed (most small, a few massive). "
    "A log-scale view is the only sensible one."
)

code(
    "vals = df['estimated_value_eur'].dropna()\n"
    "vals = vals[vals > 0]\n"
    "print(vals.describe(percentiles=[0.25, 0.5, 0.75, 0.9, 0.95, 0.99]).round(2))\n"
    "\n"
    "fig, axes = plt.subplots(1, 2, figsize=(14, 4.5))\n"
    "axes[0].hist(np.log10(vals), bins=60, color='steelblue')\n"
    "axes[0].set_title('Distribution of log10(estimated tender value EUR)')\n"
    "axes[0].set_xlabel('log10(EUR)')\n"
    "\n"
    "sns.boxplot(data=df.assign(log_value=np.log10(df['estimated_value_eur'].where(df['estimated_value_eur'] > 0))),\n"
    "            x='category', y='log_value', ax=axes[1])\n"
    "axes[1].set_title('log10(value) by category')\n"
    "plt.tight_layout();"
)

md(
    "## 6. Top procuring entities\n"
    "\n"
    "Which institutions publish the most tenders and the largest total estimated "
    "value? This is descriptive publication context, not observed spending."
)

code(
    "top_entities = (\n"
    "    df.groupby('procuring_entity_name')\n"
    "      .agg(tenders=('ocid', 'count'),\n"
    "           total_estimated_eur=('estimated_value_eur', 'sum'),\n"
    "           median_estimated_eur=('estimated_value_eur', 'median'))\n"
    "      .sort_values('total_estimated_eur', ascending=False)\n"
    "      .head(20)\n"
    ")\n"
    "top_entities"
)

code(
    "ax = top_entities['total_estimated_eur'].div(1e6).sort_values().plot(\n"
    "    kind='barh', figsize=(10, 8), color='indigo'\n"
    ")\n"
    "ax.set_title('Top 20 entities by total estimated tender value (EUR mn)')\n"
    "ax.set_xlabel('EUR (mn)')\n"
    "plt.tight_layout();"
)

md(
    "## 7. Competition: bidders per tender\n"
    "\n"
    "A single observed bidder is a competition descriptor, not proof of "
    "wrongdoing. The coarse method='open' value mixes source procedure "
    "subtypes. Rates below use only records with published bidder data and "
    "keep design contests, price quotations and standard-open procedures separate."
)

code(
    "observed = df[df['bidder_data_observed']].copy()\n"
    "bidder_dist = observed['num_bidders'].value_counts().sort_index()\n"
    "print('Distribution of bidders per tender (top 15):')\n"
    "print(bidder_dist.head(15))\n"
    "print(f\"\\nBidder-data coverage: {df['bidder_data_observed'].mean():.1%}\")\n"
    "print(f\"Single-bidder share (observed): {(observed['num_bidders'] == 1).mean():.1%}\")\n"
    "print(f\"Zero-bidder share (observed):   {(observed['num_bidders'] == 0).mean():.1%}\")\n"
    "print('\\nSingle-bidder share by source procedure subtype:')\n"
    "print(observed.assign(single=observed.num_bidders.eq(1)).groupby('procedure_subtype', "
    "dropna=False).agg(records=('ocid', 'size'), single_bidder_pct=('single', "
    "lambda s: round(100 * s.mean(), 2))).sort_values('records', ascending=False))\n"
    "\n"
    "ax = observed['num_bidders'].clip(upper=15).value_counts().sort_index().plot(\n"
    "    kind='bar', figsize=(10, 4), color='seagreen'\n"
    ")\n"
    "ax.set_title('Number of bidders per tender (clipped at 15)')\n"
    "ax.set_xlabel('bidders')\n"
    "ax.set_ylabel('tenders');"
)

md(
    "## 8. Initial descriptive screens (pre-modelling)\n"
    "\n"
    "Before training any ML model, it's worth sanity-checking what pure rule-based "
    "screens would surface. These are exploratory counts only: the current "
    "rule registry adds procedure taxonomy, award-state guards, materiality "
    "tolerances and explicit zero-weight diagnostics."
)

code(
    "signals = pd.DataFrame({\n"
    "    'single_bidder': df['num_bidders'] == 1,\n"
    "    'estimated_value_top_1pct': (df['estimated_value_eur'] >= \n"
    "                                  df['estimated_value_eur'].quantile(0.99)),\n"
    "    'short_tender_period': df['duration_days'].between(1, 10, inclusive='both'),\n"
    "})\n"
    "signals['flagged_any'] = signals.any(axis=1)\n"
    "print('Share of tender records flagged by each heuristic:')\n"
    "print((signals.mean() * 100).round(2))\n"
    "print(f\"\\nTotal flagged by any: {signals['flagged_any'].sum():,} ({signals['flagged_any'].mean():.1%})\")"
)

md(
    "## 9. Canonical handoff\n"
    "\n"
    "This notebook does not publish pipeline artifacts. The canonical silver, "
    "gold-feature, benchmark, and ML-scored outputs are built by the project CLI."
)

code("print('Run from the repository root: python -m thesis pipeline run')")

md(
    "## 10. Takeaways for the next step\n"
    "\n"
    "*(Fill in after running the cells — short bullets for the thesis.)*\n"
    "\n"
    "- Temporal coverage: ...\n"
    "- Value distribution: ...\n"
    "- Competition concerns: ...\n"
    "- Data quality gaps: ...\n"
    "\n"
    "> Do not cite stored notebook outputs as authoritative. Use the generated "
    "docs/findings.md, which records current artifact hashes."
)

nb["cells"] = cells
nb["metadata"] = {
    "kernelspec": {"display_name": "Python 3 (thesis)", "language": "python", "name": "thesis"},
    "language_info": {"name": "python", "version": "3.9.6"},
}

out = Path(__file__).resolve().parents[1] / "notebooks" / "01_eda.ipynb"
out.parent.mkdir(parents=True, exist_ok=True)
nbf.write(nb, out)
print(f"Wrote {out} ({out.stat().st_size / 1024:.1f} KB, {len(cells)} cells)")
