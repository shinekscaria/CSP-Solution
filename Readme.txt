# CSP Demo - Customer Segmentation & Offer Generator

Minimal local demo for CSP customer segmentation and personalized offers.

## Features
- SQLite backend (no external DB).
- Flask REST API.
- ML segmentation (KMeans) persisted to DB.
- Offer generator (eligibility + scoring) — chosen offer persisted.
- Frontend: customers, offers, segments pages.
- Unit tests with pytest.

## Run locally
1. Create venv and activate:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
