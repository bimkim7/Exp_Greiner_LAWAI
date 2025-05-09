from flask import Flask, render_template, request, session, redirect, url_for
from flask_session import Session
import random
import json
from config import (
    NUM_CASES_PER_PARTICIPANT,
    TOTAL_BONUS_PER_CASE,
    FACT_CHECK_COST_RATE,
    CASES,
    AI_ADVICE_POOL,
    calculate_qsr
)

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-here'  # Change this in production
app.config['SESSION_TYPE'] = 'filesystem'
Session(app)

# Add context processor to make config variables available to all templates
@app.context_processor
def inject_config():
    return {
        'NUM_CASES_PER_PARTICIPANT': NUM_CASES_PER_PARTICIPANT,
        'TOTAL_BONUS_PER_CASE': TOTAL_BONUS_PER_CASE,
        'FACT_CHECK_COST_RATE': FACT_CHECK_COST_RATE
    }

def init_session():
    """Initialize session variables for a new participant"""
    if 'participant_id' not in session:
        session['participant_id'] = random.randint(1000, 9999)
    if 'current_case' not in session:
        session['current_case'] = 0
    if 'case_bonuses' not in session:
        session['case_bonuses'] = {case['id']: TOTAL_BONUS_PER_CASE for case in CASES}
    if 'shuffled_cases' not in session:
        session['shuffled_cases'] = random.sample(CASES, NUM_CASES_PER_PARTICIPANT)
    if 'responses' not in session:
        session['responses'] = []

@app.route('/')
def index():
    init_session()
    return render_template('index.html')

@app.route('/instructions')
def instructions():
    # Reset session state for a new experiment
    session['current_case'] = 0
    session['responses'] = []
    session['case_bonuses'] = {case['id']: TOTAL_BONUS_PER_CASE for case in CASES}
    session['shuffled_cases'] = random.sample(CASES, NUM_CASES_PER_PARTICIPANT)
    return render_template('instructions.html')

@app.route('/case')
def show_case():
    if session['current_case'] >= NUM_CASES_PER_PARTICIPANT:
        return redirect(url_for('questionnaire'))
    
    case = session['shuffled_cases'][session['current_case']]
    stakes = 'high' if session['participant_id'] % 2 == 0 else 'low'
    text = case[f'text_{stakes}']
    
    return render_template('case.html', 
                         case=case,
                         text=text,
                         stakes=stakes)

@app.route('/submit_initial_decision', methods=['POST'])
def submit_initial_decision():
    decision = request.form['decision']
    confidence = float(request.form['confidence']) / 100.0
    case = session['shuffled_cases'][session['current_case']]
    session['responses'].append({
        'case_id': case['id'],
        'initial_decision': decision,
        'initial_confidence': confidence
    })
    # Select AI advice for the right case, randomize true/false
    case_advice = [a for a in AI_ADVICE_POOL if a['caseId'] == case['id']]
    advice = random.choice(case_advice)
    session['current_advice'] = advice
    return redirect(url_for('show_advice'))

@app.route('/advice')
def show_advice():
    return render_template('advice.html', 
                         advice=session['current_advice'])

@app.route('/submit_revised_decision', methods=['POST'])
def submit_revised_decision():
    decision = request.form['decision']
    confidence = float(request.form['confidence']) / 100.0
    
    case = session['shuffled_cases'][session['current_case']]
    session['responses'][-1].update({
        'revised_decision': decision,
        'revised_confidence': confidence
    })
    
    return redirect(url_for('show_opponent'))

@app.route('/opponent')
def show_opponent():
    case = session['shuffled_cases'][session['current_case']]
    # Randomly select one of the two variants for this case
    variant_text = random.choice(case['opponent_variants'])
    # Store for later use if needed
    session['current_variant'] = variant_text
    # Pass previous AI advice
    ai_advice = session['current_advice']['advice_text'] if 'current_advice' in session else ''
    return render_template('opponent.html',
        variant_text=variant_text,
        ai_advice=ai_advice)

@app.route('/inbetween')
def inbetween():
    return render_template('inbetween.html')

@app.route('/trust_decision', methods=['POST'])
def trust_decision():
    confidence = float(request.form['confidence']) / 100.0
    trust_choice = request.form['trust_choice']
    fact_check = request.form['fact_check']
    stay_with_decision = request.form.get('stay_with_decision')
    attention_check = request.form.get('attention_check')
    case = session['shuffled_cases'][session['current_case']]

    # Log responses
    session['responses'][-1]['opponent_confidence'] = confidence
    session['responses'][-1]['trust_choice'] = trust_choice
    session['responses'][-1]['fact_check'] = fact_check
    session['responses'][-1]['stay_with_decision'] = stay_with_decision
    session['responses'][-1]['attention_check'] = attention_check

    if fact_check == 'yes':
        cost = session['case_bonuses'][case['id']] * FACT_CHECK_COST_RATE
        session['case_bonuses'][case['id']] -= cost
        session['responses'][-1]['fact_checked'] = True
        session['responses'][-1]['fact_check_cost'] = cost
        # Show the true answer (do not increment current_case yet)
        return redirect(url_for('show_truth'))
    else:
        session['current_case'] += 1
        # If this was the first case and there is a second, go to inbetween page
        if session['current_case'] == 1 and NUM_CASES_PER_PARTICIPANT > 1:
            # Ensure the second case is different but with the same stakes
            first_case = session['shuffled_cases'][0]
            remaining_cases = [c for c in CASES if c['id'] != first_case['id']]
            # Stakes logic: even participant_id = high, odd = low
            stakes = 'high' if session['participant_id'] % 2 == 0 else 'low'
            # Shuffle and pick one
            random.shuffle(remaining_cases)
            session['shuffled_cases'] = [first_case, remaining_cases[0]]
            return redirect(url_for('inbetween'))
        if session['current_case'] >= NUM_CASES_PER_PARTICIPANT:
            return redirect(url_for('questionnaire'))
        return redirect(url_for('show_case'))

@app.route('/inbetween_next')
def inbetween_next():
    return redirect(url_for('show_case'))

@app.route('/truth')
def show_truth():
    case = session['shuffled_cases'][session['current_case']]
    # After showing the truth, increment current_case and go to next or questionnaire
    if session['current_case'] + 1 >= NUM_CASES_PER_PARTICIPANT:
        next_url = url_for('questionnaire')
    else:
        next_url = url_for('show_case')
    session['current_case'] += 1
    return render_template('truth.html', correct_action=case['correctAction'], next_url=next_url)

@app.route('/questionnaire')
def questionnaire():
    return render_template('questionnaire.html')

@app.route('/submit_questionnaire', methods=['POST'])
def submit_questionnaire():
    # Collect all questionnaire responses
    responses = {
        'age': request.form['age'],
        'gender': request.form['gender'],
        'study_level': request.form['study_level'],
        'study_other': request.form.get('study_other', ''),
    }
    # Task expertise
    for i in range(4):
        responses[f'task_expertise_{i+1}'] = request.form.get(f'task_expertise_{i}')
    # PTT
    for i in range(6):
        responses[f'ptt_{i+1}'] = request.form.get(f'ptt_{i}')
    # ATAI
    for i in range(5):
        responses[f'atai_{i+1}'] = request.form.get(f'atai_{i}')

    # Calculate final bonus
    total_bonus = 0
    for response in session['responses']:
        case = next(c for c in CASES if c['id'] == response['case_id'])
        is_correct = response['revised_decision'] == case['correctAction']
        qsr_score = calculate_qsr(response['revised_confidence'], is_correct)
        case_bonus = qsr_score * session['case_bonuses'][case['id']]
        total_bonus += case_bonus

    return render_template('completion.html', 
                         total_bonus=total_bonus,
                         responses=responses)

if __name__ == '__main__':
    app.run(debug=True, port=3000)

