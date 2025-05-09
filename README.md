# Decision Making Experiment

A web-based experiment studying decision-making with AI advice, using a Quadratic Scoring Rule for bonus payments.

## Setup

1. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Run the application:
```bash
python app.py
```

The experiment will be available at http://localhost:3000

## Features

- Multiple business cases with high and low stakes
- AI advice integration
- Quadratic Scoring Rule for bonus calculation
- Fact-checking option with cost
- Post-experiment questionnaire
- Session management for multiple participants

## Configuration

Key parameters can be adjusted in `config.py`:
- Number of cases per participant
- Bonus amount per case
- Fact-check cost rate
- Case scenarios and AI advice 

