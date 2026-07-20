# 🥗 MizanSa7a AR

<div align="center">

### AI-Powered Arabic Nutritional Analysis System

Speech Recognition • NLP • spaCy • LLM • PostgreSQL • OpenFoodFacts

![Python](https://img.shields.io/badge/Python-3.11-blue)
![Flask](https://img.shields.io/badge/Flask-3.x-green)
![spaCy](https://img.shields.io/badge/spaCy-NLP-orange)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-Database-blue)
![License](https://img.shields.io/badge/License-MIT-yellow)

</div>

---

# 📖 Overview

NutriVoice-AR is an AI-powered web application that analyzes meals described in **Arabic text or speech** and automatically computes their nutritional values.

The system combines **Speech Recognition**, **Natural Language Processing (NLP)**, **spaCy**, **Large Language Models (LLMs)**, a **local PostgreSQL nutritional database**, and the **OpenFoodFacts API** to accurately recognize foods, estimate quantities, and calculate calories and macronutrients.

It also stores users' meal history and provides personalized nutrition statistics through an interactive dashboard.

---

# ✨ Features

- 🎤 Arabic Speech Recognition
- 📝 Arabic Text Analysis
- 🧠 Hybrid Food Recognition (spaCy + LLM)
- 🇲🇦 Moroccan Food Database
- 🌍 OpenFoodFacts API Integration
- 🍽 Food Quantity Extraction
- 🔄 Food Name Normalization
- 🔥 Calories Calculation
- 🥩 Macronutrients Calculation
- 👤 User Authentication
- 📅 Meal History
- 📊 Nutrition Dashboard
- 🗄 PostgreSQL Database
- 🌐 REST API

---

# 🏗 System Architecture

```
Speech / Text
      │
      ▼
Speech Recognition
(Web Speech API)
      │
      ▼
Arabic NLP Processing
      │
      ├───────────────┐
      ▼               ▼
 spaCy NER         LLM NER
      │               │
      └──────┬────────┘
             ▼
Food Normalization
             │
             ▼
PostgreSQL Database
             │
      Food Found?
       │          │
      Yes         No
       │          │
       │          ▼
       │   OpenFoodFacts API
       │          │
       └──────┬───┘
              ▼
Nutrition Calculator
              │
              ▼
Meal History
              │
              ▼
Dashboard & Statistics
```

---

# 🛠 Technologies

## Backend

- Python
- Flask
- Flask-CORS
- spaCy
- PostgreSQL
- JWT Authentication
- Requests

## Frontend

- HTML5
- CSS3
- JavaScript
- Web Speech API
- Chart.js

## AI & NLP

- spaCy
- Gemini LLM
- Rule-Based NLP
- Named Entity Recognition (NER)

## Database

- PostgreSQL
- JSON

## External APIs

- OpenFoodFacts API

---

# 📂 Project Structure

```
NutriVoice-AR/

│
├── backend/
│   ├── api_server.py
│   ├── meal_analyzer.py
│   ├── ner_spacy_food.py
│   ├── ner_llm_food.py
│   ├── postgres_client.py
│   ├── history_db.py
│   ├── user_manager.py
│   ├── config.py
│   ├── test_db.py
│   └── data/
│       ├── meal_history.json
│       └── users_fallback.json
│
├── frontend/
│   ├── index.html
│   ├── login.html
│   ├── profile.html
│   ├── stats.html
│   ├── style.css
│   └── script.js
│

│
├── screenshots/
│
├── README.md
├── requirements.txt
└── .gitignore
```

---

# 🚀 Installation

## Clone Repository

```bash
git clone https://github.com/YOUR_USERNAME/NutriVoice-AR.git

cd NutriVoice-AR
```

---

## Create Virtual Environment

Windows

```bash
python -m venv venv

venv\Scripts\activate
```

Linux

```bash
python3 -m venv venv

source venv/bin/activate
```

---

## Install Dependencies

```bash
pip install -r requirements.txt
```

---

## Configure Environment Variables

Create a file named `.env`

```env
GEMINI_API_KEY=YOUR_API_KEY

JWT_SECRET=YOUR_SECRET

DB_HOST=localhost

DB_PORT=5432

DB_NAME=nutrition

DB_USER=postgres

DB_PASSWORD=password
```

---

## Create PostgreSQL Database

```sql
CREATE DATABASE nutrition;
```

Then import

```
database/schema.sql

database/foods.sql
```

---

## Run Backend

```bash
cd backend

python api_server.py
```

Backend URL

```
http://localhost:5000
```

---

## Open Frontend

Open

```
frontend/index.html
```

or

```bash
python -m http.server
```

---

# 🌐 REST API

## Analyze Meal

```
POST /analyze
```

Example Request

```json
{
    "text":"كليت جوج بيضات وطاجين الدجاج"
}
```

Example Response

```json
{
    "foods":[
        {
            "name":"بيض",
            "quantity":2,
            "calories":156
        },
        {
            "name":"طاجين الدجاج",
            "quantity":1,
            "calories":350
        }
    ],
    "total_calories":506
}
```

---

## User Login

```
POST /login
```

---

## Profile

```
GET /profile
```

---

## Statistics

```
GET /stats
```

---

# 🧠 NLP Pipeline

```
Arabic Speech
      │
      ▼
Speech Recognition
      │
      ▼
Text Cleaning
      │
      ▼
Food Detection
      │
      ├── Rule-Based
      ├── spaCy NER
      └── LLM
      │
      ▼
Food Normalization
      │
      ▼
Local Database Search
      │
      ▼
OpenFoodFacts API
      │
      ▼
Nutrition Calculation
      │
      ▼
JSON Response
```

---

# 📊 Evaluation

The project compares two different Named Entity Recognition approaches:

- spaCy
- Large Language Model (LLM)

Evaluation is performed using more than **20 complex Arabic meal descriptions**, including:

- Moroccan traditional dishes
- Compound meals
- Multiple food entities
- Ambiguous quantities
- Spoken Arabic
- Moroccan Darija

Evaluation metrics:

- Precision
- Recall
- F1-Score
- Accuracy

---

# 📸 Screenshots

## Home

```
screenshots/home.png
```

## Login

```
screenshots/login.png
```

## Dashboard

```
screenshots/dashboard.png
```

## Statistics

```
screenshots/statistics.png
```

---

# 🔮 Future Improvements

- Mobile Application
- Barcode Scanner
- OCR Food Recognition
- Image-Based Food Detection
- Personalized Diet Recommendation
- AI Meal Recommendation
- Multi-language Support
- Wearable Device Integration

---

# 👨‍💻 Author

**Atimad BEL CAID**

Master's Student in Artificial Intelligence

Faculty of Sciences Semlalia (FSSM)

Marrakech, Morocco

---

# 📄 License

This project is licensed under the MIT License.

---

# ⭐ Support

If you found this project useful, please consider giving it a ⭐ on GitHub.
