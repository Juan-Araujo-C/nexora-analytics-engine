# ◈ Nexora | Customer Intelligence Engine

![Python](https://img.shields.io/badge/Python-3.11-blue?style=for-the-badge&logo=python)
![FastAPI](https://img.shields.io/badge/FastAPI-005571?style=for-the-badge&logo=fastapi)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-316192?style=for-the-badge&logo=postgresql)
![Docker](https://img.shields.io/badge/Docker-2496ED?style=for-the-badge&logo=docker)
![Streamlit](https://img.shields.io/badge/Streamlit-FF4B4B?style=for-the-badge&logo=streamlit)

A full-stack, containerized analytics platform designed to bridge the gap between raw database transactions and actionable marketing intelligence. Nexora ingests historical e-commerce data and performs automated **RFM (Recency, Frequency, Monetary) segmentation** to drive targeted marketing strategies.

## 🎯 Business Value (The "Why")
Modern digital marketing relies on data, yet most ad spend is wasted on unsegmented audiences. Nexora solves this by providing:
* **Churn Prevention:** Instantly identifies "At Risk" cohorts before they abandon the brand.
* **Lookalike Optimization:** Isolates "Champions" to export high-LTV (Life Time Value) seed audiences for Meta Ads/Google Ads.
* **Customer 360° View:** A granular drill-down tool for sales and support teams to audit individual transactional histories.

## 🏗️ Technical Architecture
The system is strictly decoupled, ensuring scalability and clean separation of concerns:
1. **Database Layer:** `PostgreSQL` relational database mapping Customers to Transactions and computed Segments via SQLAlchemy ORM.
2. **API Layer:** A `FastAPI` REST backend providing secure, token-gated endpoints and high-performance querying.
3. **Frontend Layer:** A custom-styled `Streamlit` dashboard utilizing `Plotly` and CSS injection for a premium, enterprise-grade UI/UX.
4. **DevOps:** Fully dockerized backend pipeline via `docker-compose`.

## 🚀 Quick Start

### Prerequisites
* Docker & Docker Compose
* Python 3.11+

### 1. Launch the Backend Engine
The backend and database are containerized for zero-config deployment.
```bash
cd analytics-pipeline-saas
docker compose up --build
```

### 2. Launch the Dashboard
In a separate terminal instance, boot the analytics interface:
```bash
cd nexora-dashboard
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

### 3. Authentication
Upon opening `http://localhost:8501`, enter the secure API Key configured in your `.env` to unlock the dashboard.

---
*Built to translate raw engineering into marketing performance.*