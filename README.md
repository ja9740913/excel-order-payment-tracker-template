# Free Excel Order and Payment Tracker Template

Payment Risk Check Lite is a free, macro-free Excel order and payment tracker template for reviewing order amounts, paid amounts, due dates, collection status, outstanding balances, and obvious data-quality issues in one local workbook.

[Use the free browser checker](https://payment-flow-studio-tw.masstech.chatgpt.site/en/free?source=github_lite_readme) · [Compare the free and paid 500-row editions](https://payment-flow-studio-tw.masstech.chatgpt.site/en/templates/payment-tracker-excel-template?source=github_lite_paid) · [Open the direct Gumroad checkout](https://toolcraftstudio.gumroad.com/l/order-payment-dashboard-excel)

> Publication status: this package was prepared locally for a future GitHub repository. No remote repository or GitHub release has been created, and nothing in this folder has been uploaded by the preparation process.

## Download the free files

- [Payment-Risk-Check-Lite-v1.0.0.zip](release/Payment-Risk-Check-Lite-v1.0.0.zip) — the complete five-file release.
- [Blank workbook](workbooks/01-payment-risk-check-lite-blank.xlsx) — make a copy before entering your records.
- [Fictional demo workbook](workbooks/02-payment-risk-check-lite-demo.xlsx) — 12 fictional rows with seven valid rows and five deliberate data issues.
- [SHA-256 checksums](SHA256SUMS.txt) — integrity records for every distributed binary asset.

## What the free edition includes

- Up to 100 order rows.
- Five KPIs: valid orders, valid order amount, outstanding amount, overdue outstanding, and data issues.
- Checks for duplicate Order ID, missing Customer Code or Due Date, invalid order or paid amounts, and overdue status.
- Two `.xlsx` workbooks: one blank and one fictional demonstration.
- No VBA, macros, banking connection, platform API, or external data connection.

The free edition does **not** include monthly summaries, charts, item analysis, channel analysis, broader dropdowns, multi-user controls, integrations, or commercial implementation rights. Those are part of the paid edition where applicable. The official paid product is available at [Gumroad](https://toolcraftstudio.gumroad.com/l/order-payment-dashboard-excel).

## Excel is the primary environment

These files are built and verified as Microsoft Excel `.xlsx` workbooks. Google Sheets import is not the primary or verified environment. If you import a workbook into Google Sheets, independently check formulas, cached values, data validation, conditional formatting, date behavior, and layout before relying on the result. Compatibility is not guaranteed.

## Fictional data and privacy boundary

All records in the demo workbook are fictional and deliberately constructed for testing. Do not treat them as customer, transaction, collection, or accounting records.

The workbook does not ask for a phone number, email address, account login, bank connection, or spreadsheet upload. It runs locally in your spreadsheet application. Do not publish a workbook after adding real records, and do not attach real or confidential data to a future GitHub issue.

The adjacent [free browser checker](https://payment-flow-studio-tw.masstech.chatgpt.site/en/free?source=github_lite_readme) is the official Sites tool for checking a de-identified CSV in the browser. Review that page's current scope and privacy notice before use.

## Important boundaries

This operational sample is not accounting, tax, legal, collection, invoicing, banking, or payment software. It does not guarantee revenue, collection, time savings, data accuracy, or suitability for a particular workflow. Keep backups, validate formulas, and assess your own permissions, privacy, security, and legal duties.

## Verify the package

Python 3 is sufficient; the verifier uses only the standard library.

```powershell
python -B .\verify_release.py
```

The default verification checks:

- the exact public-file inventory;
- the release manifest and all SHA-256 records;
- the ZIP's internal file list and internal checksums;
- workbook and PNG container safety boundaries;
- local Markdown links and the two live public URLs;
- absence of paid ZIPs, private-key material, credential-like assignments, local absolute paths, and unexpected binary files;
- the local-only, not-yet-published external-state declaration.

For a hash-only check without network access:

```powershell
python -B .\verify_release.py --offline
```

The verifier can validate this folder and its declared publication state; it cannot prove that no unrelated third party has copied the files elsewhere.

## Project policies

- [License](LICENSE)
- [Security policy](SECURITY.md)
- [Contribution policy](CONTRIBUTING.md)
- [Release manifest](release-manifest.json)
