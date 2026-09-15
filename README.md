# TinyPod-RMS
```markdown
# 🏨 Automated Revenue Management System (RMS) for Cloudbeds

An automated, data-driven Revenue Management System (RMS) designed to be a highly adaptable, plug-and-play solution for **any hotel, resort, or accommodation provider using Cloudbeds**. 

By seamlessly integrating with the **Cloudbeds API v1.3**, this system allows properties of any size—from intimate boutique hotels to large-scale resorts—to transition from static pricing to intelligent, dynamic rate optimization without expensive third-party enterprise software.

---

## 🌍 Universal Applicability for Cloudbeds Properties

This system is built with a **property-agnostic architecture**, meaning it scales and adapts to your specific hotel data dynamically:
- **Drop-In Integration:** Connects instantly via standard Cloudbeds v1.3 API keys. No complex database migrations, middleware, or system overhauls required.
- **Dynamic Capacity Scaling:** Whether you have 5 rooms or 500, the algorithms automatically scale based on the property capacity and historical reservation data fetched directly from your Cloudbeds account.
- **Market Adaptability:** The internal pricing modifiers (e.g., weekend premiums, holiday spikes, competitor rate parsing) can be easily tweaked to fit diverse market profiles, whether you operate a seasonal beach resort, an urban business hotel, or a rural bed-and-breakfast.

---

## ✨ Key Features

- **Cloudbeds API v1.3 Integration**: Automatically fetches real-time dashboard metrics (Occupancy, In-House Guests, Room Blocks) and reservation pace data. Includes a built-in mock engine fallback if API credentials or network connections are temporarily unavailable.
- **Multi-Factor Dynamic Pricing Engine**:
  - **Base Adjustments**: Room type differentials, day-of-week demand, competitor rates (CompSet), and local holiday/event factors.
  - **Yield & Availability Management**: Net availability yielding based on effective occupancy (accounting for blocked rooms out of service) and booking pace ratios relative to historical lead-time checkpoints.
  - **Same-Day Time Decay**: Automatically discounts remaining inventory after 18:00, 20:00, and 22:00 local time to capture last-minute same-day bookings if occupancy thresholds are not met.
  - **Guest Density Factor**: Triggers premium rate adjustments during periods of high guest-per-room ratios to account for increased operational wear-and-tear.
- **Dual-Perspective Reporting Engine**:
  - **Technical / Analyst View**: Exports detailed metric calculations including RevPAR, confidence scores, and raw pricing factors for revenue managers.
  - **Manager / Executive View**: Converts metrics into high-level demand statuses, explicit operational commands (*Raise Aggressively*, *Discount*, *Hold Rate*), and automated business reasoning narratives for front-desk and general managers.
- **Unattended Background Scheduler**: Executes daily pricing runs automatically at your preferred local time with robust file-conflict handling and system logging.

---

## 📁 Repository Structure

```text
.
├── hotel rms.py                  # Core RMS engine: API ingestion, pricing logic, CSV generator
├── scheduler.py                  # Background scheduler script with logging and CLI options
├── Public holidays.csv           # Local holiday and event database for date-based multipliers
└── rms_scheduler.log             # Auto-generated runtime log (created upon execution)

```

---

## ⚙️ Prerequisites & Setup

### 1. Requirements

Ensure you have **Python 3.8+** installed. Install the required Python packages:

```bash
pip install pandas numpy requests schedule

```

### 2. Cloudbeds API Configuration

Open `hotel rms.py` and set your Cloudbeds API Key at the top of the file:

```python
# ==========================================
# 0. CLOUDBEDS API CONFIGURATION
# ==========================================
API_KEY = "YOUR_CLOUDBEDS_API_KEY_HERE"

```

---

## 🚀 Getting Started

### Option 1: Run the Pricing Engine Manually

To run the revenue management algorithm directly and generate immediate rate recommendations for the next 90 days:

```bash
python "hotel rms.py"

```

#### Generated Outputs:

Upon execution, the script evaluates your Cloudbeds data and exports two date-stamped CSV files:

1. `[Property_Name]_Live_Dashboard_YYYY-MM-DD.csv` *(Technical Scientist View)*
2. `[Property_Name]_Manager_View_YYYY-MM-DD.csv` *(Executive Management View)*

*(Note: If a CSV file is currently open in Excel or locked by another process, the script gracefully falls back to saving with a timestamp suffix to prevent data loss.)*

---

### Option 2: Run the Unattended Automated Scheduler

To run the scheduler continuously in the background (by default configured for daily execution at **06:00 AM**):

```bash
python scheduler.py

```

#### CLI Options:

If you want to trigger an initial pricing run immediately before starting the daily schedule loop, use the `--run-now` flag:

```bash
python scheduler.py --run-now

```

All execution events, standard outputs, and errors will be logged to both the console terminal and appended to `rms_scheduler.log` for easy auditing.

---

## 📊 Business Logic Overview

| Parameter | Default Logic / Rule |
| --- | --- |
| **Room Types** | Supports dynamic tiering (e.g., Premium/Suite inventory carries a baseline multiplier over Standard rooms). |
| **Booking Pace** | Pace ratios comparing current OTB (On-The-Books) to historical OTB at the exact same lead time dynamically increase or decrease rates by up to ±25%. |
| **Lead Time Adjustment** | Close-in dates (within 3 days) with low occupancy trigger emergency discounts; advance dates (>30 days) apply early-bird stability pricing. |
| **Time Decay** | On same-day check-ins (`Days_to_Checkin == 0`), rates decay progressively into the evening to capture last-minute bookings. |
| **Rate Boundaries** | Recommended rates are algorithmically capped between a **Floor Rate (e.g., 0.7x)** and a **Ceiling Rate (e.g., 2.0x)** to prevent extreme pricing anomalies. |

---

```
