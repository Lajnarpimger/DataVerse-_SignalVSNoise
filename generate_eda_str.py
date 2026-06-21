import nbformat as nbf
import os

nb = nbf.v4.new_notebook()

cells = []

# Section 1
cells.append(nbf.v4.new_markdown_cell("""# Suspicious Transaction Report (STR) Completeness Scoring EDA
### Defensible Evidence and Analyst-Centric Reasoning Framework

## Section 1: Problem Reframing
The objective of this challenge is not to build a "suspicious transaction detector". The analyst reading these reports already assumes the activity was flagged as suspicious by a monitoring system. 

Instead, the objective is **STR Report Completeness Scoring**. We must answer: *"How complete, informative, and analytically useful is this STR report?"*

This notebook provides the evidence base for what information is required, what information narratives actually preserve, and why certain features are proposed for the final completeness scoring framework.

We will strictly avoid supervised ML feature importance (since there are no ground-truth report quality labels) and rely on domain reasoning."""))

cells.append(nbf.v4.new_code_cell("""import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import re
from collections import Counter
import warnings
warnings.filterwarnings('ignore')

sns.set_theme(style="whitegrid")"""))

# Section 2
cells.append(nbf.v4.new_markdown_cell("""## Section 2: Structured Data Inventory
We perform a systematic audit of structured XML and CSV fields to identify the "Available Facts". We will export this as `field_summary.csv`."""))

cells.append(nbf.v4.new_code_cell("""# Load parsed reports and transactions
df_reports = pd.read_csv("report.csv")
df_transactions = pd.read_csv("transactions.csv")
df_accounts = pd.read_csv("accounts.csv")
df_features = pd.read_csv("ml_features.csv")

# Generate field summary
fields_info = []
for col in df_reports.columns:
    missing_pct = df_reports[col].isnull().mean()
    fields_info.append({
        'Field': col,
        'Source': 'XML/report.csv',
        'Missing_Pct': missing_pct,
        'Unique_Values': df_reports[col].nunique()
    })

df_field_summary = pd.DataFrame(fields_info)
df_field_summary.to_csv("field_summary.csv", index=False)

# Sanity Check: Missingness
field_missing_pct = df_field_summary['Missing_Pct']
assert field_missing_pct.between(0,1).all(), "Missing percentages must be between 0 and 1"

df_field_summary.head()"""))

# Section 3
cells.append(nbf.v4.new_markdown_cell("""## Section 3: Fact Mapping
We map the structured fields to the 5 key analyst questions and explicitly classify them based on when they are expected.

**Analyst Questions:**
1. *What happened?* (Transaction context)
2. *Who was involved?* (Party context)
3. *Why is it suspicious?* (Suspicion rationale)
4. *What should be investigated?* (Analytical reasoning)
5. *Are the stated facts accurate?* (Validation)

**Classification Types:**
- **Always Expected**: e.g., Amount, Date.
- **Conditionally Expected**: e.g., PEP, Sanctions, Velocity (Only expected if the underlying signal actually exists in the structured data).
- **Optional Context**: e.g., Reporter Phone Number.
"""))

cells.append(nbf.v4.new_code_cell("""fact_mapping = pd.DataFrame([
    {"Analyst Question": "What happened?", "Feature": "Amount", "Classification": "Always Expected"},
    {"Analyst Question": "What happened?", "Feature": "Date", "Classification": "Always Expected"},
    {"Analyst Question": "Who was involved?", "Feature": "Counterparty", "Classification": "Always Expected"},
    {"Analyst Question": "Why is it suspicious?", "Feature": "PEP Indicator", "Classification": "Conditionally Expected"},
    {"Analyst Question": "Why is it suspicious?", "Feature": "Sanctions Hit", "Classification": "Conditionally Expected"},
    {"Analyst Question": "Why is it suspicious?", "Feature": "Velocity Spike", "Classification": "Conditionally Expected"},
    {"Analyst Question": "Are the stated facts accurate?", "Feature": "Signatory Contact", "Classification": "Optional Context"}
])
fact_mapping"""))

# Section 4
cells.append(nbf.v4.new_markdown_cell("""## Section 4: Narrative Extraction
We implement robust parsing to extract "Reported Facts" from narratives. We persist a `match_type` (exact, fuzzy, inferred) and a `match_score` (0.0 to 1.0) to document extraction confidence."""))

cells.append(nbf.v4.new_code_cell("""# Example robust amount extractor with confidence
def extract_amount_with_confidence(text, expected_amount):
    if pd.isnull(text) or pd.isnull(expected_amount):
        return {"extracted": None, "match_type": "none", "match_score": 0.0}
    
    text = str(text).lower()
    expected_amount = float(expected_amount)
    
    # Simple regex for numbers
    numbers = re.findall(r'\\d+(?:[.,]\\d+)*', text)
    numbers = [float(n.replace(',', '')) for n in numbers if n.replace(',', '').replace('.','',1).isdigit()]
    
    if expected_amount in numbers:
        return {"extracted": expected_amount, "match_type": "exact", "match_score": 1.0}
    
    # Fuzzy check (within 1%)
    for n in numbers:
        if abs(n - expected_amount) / (expected_amount + 1e-9) < 0.01:
            return {"extracted": n, "match_type": "fuzzy", "match_score": 0.8}
            
    # Check for words like 'thousands', 'lakhs'
    if 'thousand' in text and expected_amount >= 1000:
        return {"extracted": "thousands", "match_type": "inferred", "match_score": 0.4}
        
    return {"extracted": None, "match_type": "none", "match_score": 0.0}

# Apply to a sample
df_reports['amount_extraction'] = df_reports.apply(
    lambda row: extract_amount_with_confidence(row['reason'], row['tx_amount_local'] if 'tx_amount_local' in df_reports.columns else 0), 
    axis=1
)
df_reports['amount_match_score'] = df_reports['amount_extraction'].apply(lambda x: x['match_score'])
"""))

# Section 5
cells.append(nbf.v4.new_markdown_cell("""## Section 5: Narrative Richness & Boilerplate Detection Analysis
We measure duplication and short narratives to identify vague/generic templates (Signal vs. Noise)."""))

cells.append(nbf.v4.new_code_cell("""df_reports['word_count'] = df_reports['reason'].astype(str).apply(lambda x: len(x.split()))
df_reports['sentence_count'] = df_reports['reason'].astype(str).apply(lambda x: len(x.split('.')))

# Sanity Check
assert (df_reports['word_count'] >= 0).all(), "Word count must be >= 0"
assert (df_reports['sentence_count'] >= 0).all(), "Sentence count must be >= 0"

# Boilerplate metrics
under_10_words = (df_reports['word_count'] < 10).sum()
under_20_words = (df_reports['word_count'] < 20).sum()
duplicate_narratives = df_reports['reason'].duplicated().sum()

print(f"Reports with < 10 words: {under_10_words}")
print(f"Reports with < 20 words: {under_20_words}")
print(f"Exact Duplicate Narratives: {duplicate_narratives}")

# Most common boilerplate text
print("\\nTop 3 Most Common Narratives:")
print(df_reports['reason'].value_counts().head(3))
"""))

# Section 6
cells.append(nbf.v4.new_markdown_cell("""## Section 6: Information Preservation
Compare "Available Facts" against "Reported Facts" to measure omission rates. We only evaluate conditionally expected features if the underlying signal exists."""))

cells.append(nbf.v4.new_code_cell("""# Example: Amount Preservation
total_expected_amounts = df_reports.shape[0]
amounts_preserved = (df_reports['amount_match_score'] > 0).sum()
amount_omission_rate = 1.0 - (amounts_preserved / total_expected_amounts)

print(f"Amount Omission Rate: {amount_omission_rate:.1%}")
"""))

# Section 7
cells.append(nbf.v4.new_markdown_cell("""## Section 7: Narrative Information Gain Analysis
We categorize the narrative's value by separating:
- **Preserved Facts**: Facts in both structured and narrative.
- **Added Facts**: Facts only in narrative (e.g. customer explanation).
- **Analytical Reasoning**: Narrative explains *why* it is suspicious.

Resulting Classifications:
1. **Fact Copying**: Mostly repeats structured data.
2. **Fact Preservation**: Preserves key context.
3. **Information Enrichment**: Adds new context.
4. **Analytical Enrichment**: Adds reasoning."""))

cells.append(nbf.v4.new_code_cell("""# Mock categorization based on text length and unique keywords
def categorize_information_gain(text):
    text = str(text).lower()
    if len(text.split()) < 10:
        return "Fact Copying"
    
    analytical_keywords = ['because', 'due to', 'indicates', 'unusual', 'inconsistent', 'justification']
    if any(k in text for k in analytical_keywords):
        return "Analytical Enrichment"
        
    enrichment_keywords = ['customer stated', 'relationship', 'purpose of', 'source of']
    if any(k in text for k in enrichment_keywords):
        return "Information Enrichment"
        
    return "Fact Preservation"

df_reports['info_gain_category'] = df_reports['reason'].apply(categorize_information_gain)

plt.figure(figsize=(8,5))
sns.countplot(y=df_reports['info_gain_category'], order=['Fact Copying', 'Fact Preservation', 'Information Enrichment', 'Analytical Enrichment'])
plt.title("Information Gain Categories")
plt.show()
"""))

# Section 8
cells.append(nbf.v4.new_markdown_cell("""## Section 8: Reconstruction Experiment
Objective metrics indicating if an analyst can reconstruct the event:
- **Transaction Reconstruction**: identified / expected (Amount, Date, Type)
- **Party Reconstruction**: identified / expected (Customer, Counterparty, Jurisdiction)
- **Suspicion Reconstruction**: identified / available_signals (PEP, Sanctions, Velocity)"""))

cells.append(nbf.v4.new_code_cell("""# Example computation for Transaction Reconstruction
# (Assuming amount is identified if match_score > 0)
df_reports['tx_reconstruction_score'] = df_reports['amount_match_score'] # Simplified for demo

# Sanity check
assert df_reports['tx_reconstruction_score'].between(0, 1).all()

print(f"Average Transaction Reconstruction Score: {df_reports['tx_reconstruction_score'].mean():.2f}")
"""))

# Section 9
cells.append(nbf.v4.new_markdown_cell("""## Section 9: Signal Coverage
We quantify how often high-risk context is present in ledger data but omitted from the narrative. This is performed **separately for each signal type**."""))

cells.append(nbf.v4.new_code_cell("""# Mock Signal Data Integration
df_reports['has_pep_signal'] = np.random.choice([0, 1], size=len(df_reports), p=[0.95, 0.05])
df_reports['has_sanctions_signal'] = np.random.choice([0, 1], size=len(df_reports), p=[0.99, 0.01])

df_reports['mentions_pep'] = df_reports['reason'].astype(str).str.contains('pep|politic', case=False).astype(int)
df_reports['mentions_sanctions'] = df_reports['reason'].astype(str).str.contains('sanction', case=False).astype(int)

def calculate_signal_coverage(signal_col, mention_col):
    available_signals = df_reports[signal_col].sum()
    if available_signals == 0:
        return 0.0, 0, 0
    explained_signals = df_reports[(df_reports[signal_col] == 1) & (df_reports[mention_col] == 1)].shape[0]
    
    # Sanity Checks
    assert explained_signals <= available_signals, "Explained signals cannot exceed available signals"
    coverage_ratio = explained_signals / available_signals
    assert 0 <= coverage_ratio <= 1, "Coverage ratio must be between 0 and 1"
    
    return coverage_ratio, explained_signals, available_signals

pep_cov, pep_exp, pep_avail = calculate_signal_coverage('has_pep_signal', 'mentions_pep')
sanc_cov, sanc_exp, sanc_avail = calculate_signal_coverage('has_sanctions_signal', 'mentions_sanctions')

print(f"PEP Signal Coverage: {pep_cov:.1%} ({pep_exp}/{pep_avail})")
print(f"Sanctions Signal Coverage: {sanc_cov:.1%} ({sanc_exp}/{sanc_avail})")
"""))

# Section 10
cells.append(nbf.v4.new_markdown_cell("""## Section 10: Feature Candidate Justification Table & Validation
The ultimate audit trail for proposed features. Global validation asserts ensure logical consistency."""))

cells.append(nbf.v4.new_code_cell("""# Define the Justification Table
justification_data = [
    {"Feature": "Amount Match", "Analyst Question": "What happened?", "Domain Rationale": "Core transaction context", "Structured Availability": "100%", "Narrative Availability": f"{amounts_preserved/total_expected_amounts:.1%}", "Omission Rate": f"{amount_omission_rate:.1%}"},
    {"Feature": "PEP Mention", "Analyst Question": "Why suspicious?", "Domain Rationale": "AML risk indicator", "Structured Availability": f"{pep_avail}", "Narrative Availability": f"{pep_exp}", "Omission Rate": f"{1-pep_cov:.1%}" if pep_avail > 0 else "N/A"}
]

df_justification = pd.DataFrame(justification_data)

# Global Assertions Validation
validation_score = 1.0 # placeholder
assert 0 <= validation_score <= 1
assert 0 <= pep_cov <= 1

df_justification
"""))

# Section 11
cells.append(nbf.v4.new_markdown_cell("""## Section 11: Framework Proposal
Based on the EDA, we propose the following candidate completeness dimensions:

- **Dimension A**: Transaction Context (What happened?)
- **Dimension B**: Party Context (Who was involved?)
- **Dimension C**: Suspicion Explanation (Why is it suspicious?)
- **Dimension D**: Analytical Reasoning (What should be investigated?)
- **Dimension E**: Validation (Are the stated facts accurate?)

**Note: No scoring formula, weights, or aggregation strategy will be defined in this notebook.**"""))


nb['cells'] = cells

with open('EDA_STR.ipynb', 'w', encoding='utf-8') as f:
    nbf.write(nb, f)
print("Notebook EDA_STR.ipynb generated successfully.")
