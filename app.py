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
import csv
import os
from datetime import datetime

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-here'  # Change this in production
app.config['SESSION_TYPE'] = 'filesystem'
Session(app)

# Add this after the Session(app) line
@app.before_request
def prevent_back():
    """Prevent going back to previous pages"""
    if request.method == 'GET':
        # List of paths that should be accessible
        allowed_paths = ['/', '/instructions', '/static']
        # Get the current path
        current_path = request.path
        
        # If the path is not in allowed paths and not a static file
        if not any(current_path.startswith(path) for path in allowed_paths):
            # Check if we have a session
            if 'participant_id' in session:
                # Get the current step
                current_step = None
                if current_path == '/case':
                    current_step = 'case'
                elif current_path == '/advice':
                    current_step = 'advice'
                elif current_path == '/opponent':
                    current_step = 'opponent'
                elif current_path == '/truth':
                    current_step = 'truth'
                elif current_path == '/questionnaire':
                    current_step = 'questionnaire'
                elif current_path == '/inbetween':
                    current_step = 'inbetween'
                
                # If we're trying to access a step that's not the current one
                if current_step and current_step != session.get('current_step'):
                    # Redirect to the current step
                    if session.get('current_step') == 'case':
                        return redirect(url_for('show_case'))
                    elif session.get('current_step') == 'advice':
                        return redirect(url_for('show_advice'))
                    elif session.get('current_step') == 'opponent':
                        return redirect(url_for('show_opponent'))
                    elif session.get('current_step') == 'truth':
                        return redirect(url_for('show_truth'))
                    elif session.get('current_step') == 'questionnaire':
                        return redirect(url_for('questionnaire'))
                    elif session.get('current_step') == 'inbetween':
                        return redirect(url_for('inbetween'))
                # If we're trying to access a page without a current step set
                elif not session.get('current_step') and current_step:
                    return redirect(url_for('index'))

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
    if 'current_step' not in session:
        session['current_step'] = None

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
    
    # Update current step
    session['current_step'] = 'case'
    
    return render_template('case.html', 
                         case=case,
                         text=text,
                         stakes=stakes)

@app.route('/submit_initial_decision', methods=['POST'])
def submit_initial_decision():
    decision = request.form['decision']
    confidence = float(request.form['confidence']) / 100.0
    case = session['shuffled_cases'][session['current_case']]
    stakes = 'high' if session['participant_id'] % 2 == 0 else 'low'
    
    # Store in session
    session['responses'].append({
        'case_id': case['id'],
        'initial_decision': decision,
        'initial_confidence': confidence
    })
    
    # Log to CSV with all available data
    log_data = {
        'timestamp': datetime.now().isoformat(),
        'participant_id': session['participant_id'],
        'step': 'initial_decision',
        'case_id': case['id'],
        'stakes': stakes,
        'initial_decision': decision,
        'initial_confidence': confidence,
        'revised_decision': '',
        'revised_confidence': '',
        'attention_check': '',
        'opponent_confidence': '',
        'stay_with_decision': '',
        'trust_choice': '',
        'fact_check': '',
        'fact_check_cost': '',
        'is_correct': '',
        'case_reward': '',
        'case_bonus': session['case_bonuses'][case['id']]
    }
    log_to_csv(log_data)
    
    # Select AI advice for the right case, randomize true/false
    case_advice = [a for a in AI_ADVICE_POOL if a['caseId'] == case['id']]
    advice = random.choice(case_advice)
    session['current_advice'] = advice
    
    return redirect(url_for('show_advice'))

@app.route('/advice')
def show_advice():
    # Update current step
    session['current_step'] = 'advice'
    return render_template('advice.html', 
                         advice=session['current_advice'])

@app.route('/submit_revised_decision', methods=['POST'])
def submit_revised_decision():
    decision = request.form['decision']
    confidence = float(request.form['confidence']) / 100.0
    attention_check = request.form.get('attention_check', '')
    case = session['shuffled_cases'][session['current_case']]
    stakes = 'high' if session['participant_id'] % 2 == 0 else 'low'
    
    # Get current response to preserve initial decision data
    current_response = session['responses'][-1]
    
    # Update session data
    current_response.update({
        'revised_decision': decision,
        'revised_confidence': confidence,
        'attention_check': attention_check
    })
    
    # Log to CSV with all available data
    log_data = {
        'timestamp': datetime.now().isoformat(),
        'participant_id': session['participant_id'],
        'step': 'revised_decision',
        'case_id': case['id'],
        'stakes': stakes,
        'initial_decision': current_response['initial_decision'],
        'initial_confidence': current_response['initial_confidence'],
        'revised_decision': decision,
        'revised_confidence': confidence,
        'attention_check': attention_check,
        'opponent_confidence': '',
        'stay_with_decision': '',
        'trust_choice': '',
        'fact_check': '',
        'fact_check_cost': '',
        'is_correct': '',
        'case_reward': '',
        'case_bonus': session['case_bonuses'][case['id']]
    }
    log_to_csv(log_data)
    
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
    
    # Update current step
    session['current_step'] = 'opponent'
    
    return render_template('opponent.html',
        variant_text=variant_text,
        ai_advice=ai_advice)

@app.route('/inbetween')
def inbetween():
    session['current_step'] = 'inbetween'
    return render_template('inbetween.html')

@app.route('/trust_decision', methods=['POST'])
def trust_decision():
    confidence = float(request.form['confidence']) / 100.0
    trust_choice = request.form['trust_choice']
    fact_check = request.form['fact_check']
    stay_with_decision = request.form.get('stay_with_decision', '')
    case = session['shuffled_cases'][session['current_case']]
    stakes = 'high' if session['participant_id'] % 2 == 0 else 'low'

    # Get the current response to preserve all previous data
    current_response = session['responses'][-1]

    # Log responses
    current_response['opponent_confidence'] = confidence
    current_response['trust_choice'] = trust_choice
    current_response['fact_check'] = fact_check
    current_response['stay_with_decision'] = stay_with_decision
    
    # Calculate if decision was correct
    is_correct = current_response['revised_decision'] == case['correctAction']
    qsr_score = calculate_qsr(current_response['revised_confidence'], is_correct)
    case_reward = qsr_score * TOTAL_BONUS_PER_CASE
    
    # Log to CSV with all previous data preserved
    log_data = {
        'timestamp': datetime.now().isoformat(),
        'participant_id': session['participant_id'],
        'step': 'trust_decision',
        'case_id': case['id'],
        'stakes': stakes,
        'initial_decision': current_response['initial_decision'],
        'initial_confidence': current_response['initial_confidence'],
        'revised_decision': current_response['revised_decision'],
        'revised_confidence': current_response['revised_confidence'],
        'attention_check': current_response.get('attention_check', ''),
        'opponent_confidence': confidence,
        'trust_choice': trust_choice,
        'fact_check': fact_check,
        'stay_with_decision': stay_with_decision,
        'is_correct': str(is_correct),
        'case_reward': case_reward
    }
    
    if fact_check == 'yes':
        cost = session['case_bonuses'][case['id']] * FACT_CHECK_COST_RATE
        session['case_bonuses'][case['id']] -= cost
        current_response['fact_checked'] = True
        current_response['fact_check_cost'] = cost
        log_data['fact_check_cost'] = cost
        log_data['case_bonus'] = session['case_bonuses'][case['id']]
        # Log to CSV
        log_to_csv(log_data)
        # Show the true answer (do not increment current_case yet)
        return redirect(url_for('show_truth'))
    else:
        log_data['case_bonus'] = session['case_bonuses'][case['id']]
        # Log to CSV
        log_to_csv(log_data)
        session['current_case'] += 1
        # If there are more cases, go to inbetween page
        if session['current_case'] < NUM_CASES_PER_PARTICIPANT:
            # Ensure the next case is different but with the same stakes
            current_case = session['shuffled_cases'][session['current_case'] - 1]
            remaining_cases = [c for c in CASES if c['id'] != current_case['id']]
            # Stakes logic: even participant_id = high, odd = low
            stakes = 'high' if session['participant_id'] % 2 == 0 else 'low'
            # Shuffle and pick one
            random.shuffle(remaining_cases)
            session['shuffled_cases'] = [current_case, remaining_cases[0]]
            return redirect(url_for('inbetween'))
        return redirect(url_for('questionnaire'))

@app.route('/inbetween_next')
def inbetween_next():
    session['current_step'] = 'case'
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
    
    # Update current step
    session['current_step'] = 'truth'
    
    return render_template('truth.html', correct_action=case['correctAction'], next_url=next_url)

@app.route('/questionnaire')
def questionnaire():
    # Update current step
    session['current_step'] = 'questionnaire'
    return render_template('questionnaire.html')

@app.route('/submit_questionnaire', methods=['POST'])
def submit_questionnaire():
    # Get the last case data
    last_case = session['shuffled_cases'][-1]
    last_response = session['responses'][-1]
    stakes = 'high' if session['participant_id'] % 2 == 0 else 'low'
    
    # Collect all questionnaire responses
    responses = {
        'timestamp': datetime.now().isoformat(),
        'participant_id': session['participant_id'],
        'step': 'questionnaire',
        'case_id': last_case['id'],
        'stakes': stakes,
        'initial_decision': last_response['initial_decision'],
        'initial_confidence': last_response['initial_confidence'],
        'revised_decision': last_response['revised_decision'],
        'revised_confidence': last_response['revised_confidence'],
        'attention_check': last_response.get('attention_check', ''),
        'opponent_confidence': last_response.get('opponent_confidence', ''),
        'stay_with_decision': last_response.get('stay_with_decision', ''),
        'trust_choice': last_response.get('trust_choice', ''),
        'fact_check': last_response.get('fact_check', ''),
        'fact_check_cost': last_response.get('fact_check_cost', ''),
        'is_correct': str(last_response['revised_decision'] == last_case['correctAction']),
        'case_reward': last_response.get('case_reward', ''),
        'case_bonus': session['case_bonuses'][last_case['id']],
        'age': request.form['age'],
        'gender': request.form['gender'],
        'study_level': request.form['study_level'],
        'study_other': request.form.get('study_other', ''),
    }
    
    # Task expertise (4 items)
    for i in range(4):
        responses[f'task_expertise_{i}'] = request.form.get(f'task_expertise_{i}')
    
    # PTT (6 items)
    for i in range(6):
        responses[f'ptt_{i}'] = request.form.get(f'ptt_{i}')
    
    # ATAI (5 items)
    for i in range(5):
        responses[f'atai_{i}'] = request.form.get(f'atai_{i}')
    
    # Calculate final bonus
    total_bonus = 0
    for response in session['responses']:
        case = next(c for c in CASES if c['id'] == response['case_id'])
        is_correct = response['revised_decision'] == case['correctAction']
        qsr_score = calculate_qsr(response['revised_confidence'], is_correct)
        case_bonus = qsr_score * session['case_bonuses'][case['id']]
        total_bonus += case_bonus
    
    responses['total_bonus'] = total_bonus
    
    # Log to CSV
    log_to_csv(responses)
    
    return render_template('completion.html', 
                         total_bonus=total_bonus,
                         responses=responses)

# Define fixed column ordering for CSV file to create a nice table structure
CSV_FILE = 'experiment_data.csv'
CSV_COLUMNS = [
    'timestamp', 'participant_id', 'step', 'case_id', 'stakes',
    'initial_decision', 'initial_confidence',
    'revised_decision', 'revised_confidence', 'attention_check',
    'opponent_confidence', 'stay_with_decision', 'trust_choice', 'fact_check', 'fact_check_cost',
    'is_correct', 'case_reward', 'case_bonus',
    'age', 'gender', 'study_level', 'study_other',
    # Task expertise (4 items)
    'task_expertise_0', 'task_expertise_1', 'task_expertise_2', 'task_expertise_3',
    # PTT (6 items)
    'ptt_0', 'ptt_1', 'ptt_2', 'ptt_3', 'ptt_4', 'ptt_5',
    # ATAI (5 items)
    'atai_0', 'atai_1', 'atai_2', 'atai_3', 'atai_4',
    'total_bonus'
]

def log_to_csv(data_dict):
    """
    Log data to CSV file with consistent column ordering for a clean table structure.
    """
    file_exists = os.path.isfile(CSV_FILE)
    
    # Fill in missing columns with empty strings to ensure table structure
    row = {col: data_dict.get(col, '') for col in CSV_COLUMNS}
    
    with open(CSV_FILE, 'a', newline='', encoding='utf-8') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=CSV_COLUMNS)
        if not file_exists:
            writer.writeheader()
        writer.writerow(row)

if __name__ == '__main__':
    app.run(debug=True, port=3000)

