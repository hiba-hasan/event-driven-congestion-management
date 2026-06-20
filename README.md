# 🏙️ Resilient City OS

### Event-Driven Congestion Intelligence & Response Planning

> **Most traffic systems stop at predicting congestion. Resilient City OS goes one step further—learning from historical disruptions and transforming those insights into operational playbooks for future events.**

Built for the **Flipkart Gridlock Hackathon**, this prototype uses historical traffic disruption data to identify recurring event patterns, detect institutional learning failures, and recommend actionable traffic response strategies.

---

## 🚨 Problem Statement

Political rallies, festivals, sports events, construction activities, and sudden gatherings create localized traffic breakdowns.

### Why It's Hard Today

- Traffic impact is discovered only after congestion occurs.
- Resource deployment is often experience-driven.
- Cities repeatedly make the same operational mistakes.
- There is no institutional memory for managing disruptions.

---

## 💡 Our Solution

**Resilient City OS** converts historical disruption data into a decision-support system for traffic authorities.

Given an upcoming event, the system can:

- Forecast likely traffic impact

- Match the event to historical disruption archetypes

- Recommend manpower deployment

- Suggest barricading requirements

- Propose diversion strategies

- Warn authorities about historical response inconsistencies

---

## 🧠 How It Works

### 1. Event DNA Clustering

Historical events are grouped into recurring disruption archetypes using unsupervised learning.

**Input Features**

- Event type
- Priority
- Zone
- Corridor
- Junction characteristics

**Output**

- 10 Event DNA archetypes representing how disruptions behave.

Example:

> Cluster 8 → High-priority planned disruptions involving processions and public events.

---

### 2. Resilience Scoring

Measures how well junctions recover from disruptions.

```
Resilience Score = 1 / (1 + Average Recovery Time)
```

Higher scores indicate stronger recovery capability.

This helps identify:

- 🟢 Resilient junctions
- 🔴 Fragile junctions

---

### 3. Institutional Learning Failure Detection

Detects situations where similar events produce wildly different recovery outcomes.

This indicates:

> The city is repeating mistakes instead of learning from past responses.

Learning gaps are identified using the **Coefficient of Variation (CV)** of recovery times.

---

### 4. 🚦 Response Planner

The system's operational intelligence layer.

Authorities provide details about an upcoming event.

The planner:

- Finds the closest Event DNA archetype
- Forecasts expected impact
- Estimates affected junctions
- Generates dynamic recommendations for:
  - Police deployment
  - Barricading
  - Diversion planning
- Flags institutional warnings
- Provides recommendation confidence scores

---

## 🖥️ Dashboard Features

### 🗺️ Resilience Map

Visualize vulnerable and resilient junctions across the city.

### 🧬 Event Archetypes

Explore historical disruption patterns and affected areas.

### ⚠️ Learning Failures

Identify where authorities repeatedly fail to respond consistently.

### 🚦 Response Planner

Generate operational response strategies for future events.

---

## 📊 Results from Bengaluru Dataset

| Metric                  | Value       |
| ----------------------- | ----------- |
| Events Processed        | 3,442       |
| Junctions Analyzed      | 280         |
| Event Archetypes        | 10          |
| Fragile Junctions       | 226         |
| Resilient Junctions     | 54          |
| Learning Failure Points | 16          |
| Critical Learning Gaps  | 9 Junctions |

### Key Insight

Two planned-event archetypes revealed that:

- Events often considered **low priority** can require significantly longer recovery times.
- Authorities may systematically underestimate certain disruptions.

---

## 🏗️ System Architecture

```
Historical Events
        │
        ▼
Event DNA Clustering
        │
        ▼
Resilience Scoring
        │
        ▼
Learning Failure Detection
        │
        ▼
🚦 Response Planner
        │
        ▼
Operational Recommendations
```

---

## ⚙️ Technology Stack

| Layer            | Technology             |
| ---------------- | ---------------------- |
| Data Processing  | Pandas, NumPy          |
| Machine Learning | Scikit-Learn (K-Means) |
| Backend          | FastAPI                |
| Dashboard        | Streamlit              |
| Visualization    | Plotly                 |
| Storage          | JSON, Parquet          |
| Language         | Python 3.11+           |

---

## 🚀 Quick Start

### Clone the Repository

```bash
git clone https://github.com/hiba-hasan/event-driven-congestion-management.git
cd gridlock-event-driven-congestion
```

### Install Dependencies

```bash
python3 -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate

pip install -r requirements.txt
```

### Start the API

```bash
uvicorn src.api:app --reload
```

Swagger Documentation:

```
http://localhost:8000/docs
```

### Launch Dashboard

Open a new terminal:

```bash
source venv/bin/activate
streamlit run dashboard/app.py
```

Dashboard:

```
http://localhost:8501
```

---

## 📁 Project Structure

```
gridlock-event-driven-congestion/
├── dashboard/
├── src/
├── results/
├── data/
├── README.md
├── requirements.txt
├── config.yaml
```

---

## 🎯 Why This Matters

Traditional systems are reactive.

They answer:

> "What happened?"

Resilient City OS answers:

> "What is likely to happen, and what should we do about it?"

By combining event intelligence, resilience analysis, and institutional memory, cities can move from reacting to congestion to proactively managing it.

---

## 🏆 Built for Flipkart Gridlock Hackathon

### What We Built

- ✅ Event DNA Clustering
- ✅ Resilience Scoring
- ✅ Learning Failure Detection
- ✅ FastAPI Service Layer
- ✅ Interactive Streamlit Dashboard
- ✅ Dynamic Response Planner
- ✅ Operational Recommendations

---

## 🔮 Future Enhancements

- Real-time event ingestion
- Live traffic integration
- Route optimization engine
- Multi-city deployment
- Citizen alert system

---

> **"Most systems stop at predicting congestion. Resilient City OS transforms historical disruption intelligence into actionable response playbooks for smarter cities."**
