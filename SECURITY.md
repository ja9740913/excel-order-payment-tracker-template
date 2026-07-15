# Security Policy

## Supported release

Security and integrity checks currently cover Payment Risk Check Lite 1.0.0 and the exact hashes recorded in `SHA256SUMS.txt`.

## Local-data boundary

The Excel workbooks are macro-free and contain no banking connection, platform API, external data connection, or upload feature. They do not ask for a phone number, email address, password, or account login. The demonstration data is fictional.

Keep real operational data out of public repositories and issues. Work on a copy, retain a clean backup, limit access to exported files, and follow the privacy and retention rules that apply to your organization.

## Reporting an issue

Once a repository exists, use a GitHub issue only when the report can be fully reproduced with fictional data and contains no confidential information. Include the affected version, operating system, spreadsheet application and version, expected result, actual result, and minimal fictional steps.

Do not attach a workbook containing real orders, customer identifiers, payment details, credentials, tokens, receipts, or internal documents. If a report cannot be safely described without sensitive information, do not open a public issue; wait until the maintainer publishes a private reporting channel.

## Integrity check

Run `python -B verify_release.py` before use. A hash mismatch means the file is not the verified 1.0.0 public asset and should not be trusted as this release.

