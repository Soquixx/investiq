# InvestIQ – AI Powered Financial Intelligence Platform

![Python](https://img.shields.io/badge/Python-3.10-blue)
![Framework](https://img.shields.io/badge/Framework-Flask-black)
![Machine Learning](https://img.shields.io/badge/AI-Machine%20Learning-green)
![Status](https://img.shields.io/badge/Status-Active-success)

InvestIQ is an AI-powered financial intelligence platform that helps users understand investment decisions through data-driven analysis, risk profiling, and explainable insights.

The system combines machine learning models, user financial profiles, and live market data to generate personalized portfolio insights and investment guidance.

---

## Problem

Many retail investors make financial decisions without structured analysis, often relying on social media trends or incomplete information. This results in poor diversification and unmanaged financial risk.

InvestIQ addresses this gap by providing a system that analyzes user financial data and generates explainable portfolio insights.

---

## Core Features

**Risk Profiling**  
Analyzes user financial inputs to determine investment risk tolerance.

**Portfolio Allocation**  
Generates diversified portfolio allocations aligned with user risk capacity.

**Machine Learning Predictions**  
Uses trained ML models to estimate potential investment outcomes.

**Explainable Insights**  
Provides understandable explanations for recommendations.

**Live Market Data Integration**  
Uses real-time market information to support financial insights.

**AI Chatbot Assistant**  
Allows users to interact with the system, ask financial questions, and understand recommendations based on their profile and market data.

---

## Project Structure

```
investiq
│
├── database        # Database models
├── models          # Machine learning models
├── routes          # API and application routes
├── services        # Financial analysis and ML logic
├── templates       # HTML frontend
│
├── app.py          # Flask application configuration
├── run.py          # Application entry point
└── models_list.txt # ML model references
```

---

# Technology Stack

### Backend  
- Python
- Flask

### Machine Learning  
- Scikit-learn
- Pandas
- NumPy

### Frontend  
- HTML 
- Jinja 
- Templates

### Database  
- SQLite

### Market Data  
- Live market data integration
- yfinace

### APIs 
- Alpha Vantage API - Real time market data
- Google Gemini APi - AI chatbot and financial explanations
 
---


## Installation

Clone the repository

```bash
git clone https://github.com/Soquixx/investiq.git
cd investiq
```

Create virtual environment

```bash
python -m venv venv
```

Activate environment

Windows

```bash
venv\Scripts\activate
```

Linux / Mac

```bash
source venv/bin/activate
```

Install dependencies

```bash
pip install -r requirements.txt
```

---

## Run Application

```bash
python run.py
```

The application will start locally and can be accessed through the browser.

---


## License

MIT License
