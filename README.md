# Simples Nacional SaaS & AI CFO 🚀

The ultimate intelligent financial platform for Brazilian PMEs (Small & Medium Enterprises) under the Simples Nacional tax regime. This platform goes far beyond basic accounting—it acts as an automated "Virtual CFO" (BPO Financeiro) to prevent bankruptcy, optimize taxes, and predict cash runways.

## 🌟 Key Features

### 1. 🧠 AI CFO & Runway Prediction
Built to combat the fact that "3 out of 4 businesses fail," our AI continuously monitors the company's financial graph:
- **Cash Runway Analysis:** Predicts exactly how many months the business can survive at its current burn rate.
- **Account Mixing Alert:** Automatically flags if the founders are mixing PF (Personal) and PJ (Business) finances (the #1 predictor of bankruptcy).
- **Insolvency Risk Score:** Powered by an embedded ML model (RandomForest) predicting failure probabilities based on working capital and volatility.

### 2. ⚖️ Advanced Tax Engineering (Planejamento Tributário)
- **Fator R Optimizer:** A dashboard that calculates the exact amount of Pró-labore needed this month to legally drop the tax bracket from Anexo V (15.5%) to Anexo III (6%).
- **Reforma Tributária (EC 132/2023) Simulator:** Prepares businesses for the 2026/2027 transition by analyzing their B2B vs B2C ratio and recommending whether they should stay unified inside the DAS or segregate IBS/CBS collection to stay competitive.
- **Sociedade Uniprofissional (SUP) Scanner:** Scans if a clinic/law firm is eligible to stop paying variable ISS and switch to a fixed municipal fee, projecting annual savings.

### 3. 💰 Smart Pricing Calculator
- Automatically calculates the company's exact *Aliquota Efetiva* (effective tax rate) inside the Simples Nacional based on their RBT12.
- A beautiful UI where users input the cost of a product and their desired profit margin, and the engine automatically adds the exact tax markup to ensure they actually take home their target profit.

### 4. 🛡️ Spec-Driven Gatekeeper
A rigorous CI/CD pipeline built directly into `git push`:
- **SAST:** Runs `bandit` to scan for security vulnerabilities (injection, insecure hashes, etc.).
- **Unit Tests:** Executes the Django test suite to mathematically verify all tax and AI formulas.
- Pushes to main are physically blocked unless security and math checks pass 100%.

### 5. 🏢 SaaS Admin & Multi-Tenancy
- **Row-Level Tenant Isolation:** Complete segregation of data between clients using `CompanyUser` foreign keys.
- **Onboarding Flow:** Seamless CNPJ and Company registration flow.
- **Superadmin Dashboard:** A high-security control panel for the SaaS owner to monitor system error logs and total registered clients.

## 🛠️ Tech Stack
- **Backend:** Python / Django
- **Frontend:** Vanilla JS / Glassmorphism UI / Custom CSS
- **Machine Learning:** Scikit-Learn / NetworkX (Knowledge Graphs)
- **Database:** SQLite (dev) / PostgreSQL (prod)

## 🚀 Getting Started

```bash
# 1. Clone the repository
git clone https://github.com/FilipeAphrody/SimplesNacional.git
cd SimplesNacional

# 2. Create and activate a Virtual Environment
python -m venv venv
.\venv\Scripts\activate

# 3. Install Dependencies
pip install -r requirements.txt

# 4. Run Migrations & Train ML Model
python manage.py migrate
# (The AI Model trains itself on the first dashboard load if the .pkl is missing)

# 5. Start the Server
python manage.py runserver
```

## 🔒 Security

We employ **Spec-Driven Development**. Any pull request or push is intercepted by our `.git/hooks/pre-push` script which audits the code using `bandit` and runs the full test suite. No broken or insecure code can enter the `main` branch.
