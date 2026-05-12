from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from supabase import create_client
from dotenv import load_dotenv
from datetime import timedelta, datetime
import os

load_dotenv()

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', os.urandom(24).hex())
app.permanent_session_lifetime = timedelta(days=30)

supabase = create_client(
    os.getenv('SUPABASE_URL'),
    os.getenv('SUPABASE_KEY')
)

# ----- AUTH ROUTES -----

@app.route('/')
def home():
    if 'user' not in session:
        return redirect(url_for('login'))
    return redirect(url_for('dashboard'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        try:
            response = supabase.auth.sign_in_with_password({
                "email": email,
                "password": password
            })
            session.permanent = True
            session['user'] = response.user.email
            session['user_id'] = response.user.id
            session['name'] = response.user.user_metadata.get('name', email.split('@')[0])
            return redirect(url_for('home'))
        except:
            return render_template('login.html', error='Invalid email or password')
    message = request.args.get('message')
    return render_template('login.html', message=message)

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        password = request.form['password']
        confirm_password = request.form.get('confirm_password', '')
        
        if password != confirm_password:
            return render_template('signup.html', error='Passwords do not match')
        
        try:
            supabase.auth.sign_up({
                "email": email,
                "password": password,
                "options": {"data": {"name": name}}
            })
            return redirect(url_for('login', message='Account created successfully! Please sign in.'))
        except:
            return render_template('signup.html', error='Could not create account')
    return render_template('signup.html')

@app.route('/forgot_password', methods=['GET', 'POST'])
def forgot_password():
    message = None
    error = None
    if request.method == 'POST':
        email = request.form['email']
        try:
            supabase.auth.reset_password_for_email(email)
            message = 'If that email exists, a password reset link has been sent. Check your inbox.'
        except:
            error = 'Could not send reset email'
    return render_template('forgot_password.html', message=message, error=error)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/demo')
def demo():
    session['user'] = 'demo'
    session['user_id'] = 'demo'
    session['name'] = 'Demo User'
    return redirect(url_for('home'))

@app.route('/profile', methods=['GET', 'POST'])
def profile():
    if 'user' not in session or session.get('user') == 'demo':
        return redirect(url_for('login'))
    message = None
    error = None
    if request.method == 'POST':
        action = request.form.get('action')
        if action == 'change_password':
            new_password = request.form.get('new_password')
            try:
                supabase.auth.update_user({"password": new_password})
                message = 'Password updated successfully'
            except:
                error = 'Could not update password'
        elif action == 'delete_account':
            try:
                supabase.table('budget_items').delete().eq('user_id', session['user_id']).execute()
                supabase.table('savings_goals').delete().eq('user_id', session['user_id']).execute()
                supabase.table('goal_contributions').delete().eq('user_id', session['user_id']).execute()
                supabase.table('net_worth_items').delete().eq('user_id', session['user_id']).execute()
                session.clear()
                return redirect(url_for('login', message='Account deleted successfully'))
            except:
                error = 'Could not delete account'
    return render_template('profile.html', user=session['user'], message=message, error=error)

# ----- DASHBOARD ROUTE -----

@app.route('/dashboard')
def dashboard():
    if 'user' not in session:
        return redirect(url_for('login'))
    
    if session.get('user_id') == 'demo':
        return render_template('dashboard.html', user=session['user'], stats={
            'income': 0, 'bills': 0, 'savings': 0, 'debt': 0, 'leftover': 0, 'item_count': 0
        }, last_stats={'income': 0, 'bills': 0, 'savings': 0, 'debt': 0, 'leftover': 0}, goals=[], net_worth=0, total_assets=0, total_liabilities=0)
    
    now = datetime.now()
    response = supabase.table('budget_items').select('*').eq('user_id', session['user_id']).eq('month', now.month).eq('year', now.year).execute()
    items = response.data
    stats = {'income': 0, 'bills': 0, 'savings': 0, 'debt': 0, 'item_count': len(items)}
    for item in items:
        if item['section'] in stats:
            stats[item['section']] += item['amount']
    stats['leftover'] = stats['income'] - stats['bills'] - stats['savings'] - stats['debt']
    
    last_month = now.month - 1 if now.month > 1 else 12
    last_year = now.year if now.month > 1 else now.year - 1
    last_response = supabase.table('budget_items').select('*').eq('user_id', session['user_id']).eq('month', last_month).eq('year', last_year).execute()
    last_items = last_response.data
    last_stats = {'income': 0, 'bills': 0, 'savings': 0, 'debt': 0}
    for item in last_items:
        if item['section'] in last_stats:
            last_stats[item['section']] += item['amount']
    last_stats['leftover'] = last_stats['income'] - last_stats['bills'] - last_stats['savings'] - last_stats['debt']
    
    goals_response = supabase.table('savings_goals').select('*').eq('user_id', session['user_id']).execute()
    
    networth_response = supabase.table('net_worth_items').select('*').eq('user_id', session['user_id']).execute()
    networth_items = networth_response.data
    total_assets = sum(i['amount'] for i in networth_items if i['type'] == 'asset')
    total_liabilities = sum(i['amount'] for i in networth_items if i['type'] == 'liability')
    net_worth = total_assets - total_liabilities
    
    return render_template('dashboard.html', user=session['user'], stats=stats, last_stats=last_stats, goals=goals_response.data, net_worth=net_worth, total_assets=total_assets, total_liabilities=total_liabilities)

# ----- BUDGET ROUTES -----

@app.route('/budget')
def budget():
    if 'user' not in session:
        return redirect(url_for('login'))
    return render_template('index.html', user=session['user'])

@app.route('/save_item', methods=['POST'])
def save_item():
    if session.get('user_id') == 'demo':
        return jsonify({'status': 'demo'})
    data = request.json
    now = datetime.now()
    month = int(data.get('month', now.month))
    year = int(data.get('year', now.year))
    response = supabase.table('budget_items').insert({
        'user_id': session['user_id'],
        'section': data['section'],
        'name': data['name'],
        'amount': data['amount'],
        'month': month,
        'year': year
    }).execute()
    return jsonify({'status': 'saved', 'id': response.data[0]['id']})

@app.route('/update_item', methods=['POST'])
def update_item():
    if session.get('user_id') == 'demo':
        return jsonify({'status': 'demo'})
    data = request.json
    supabase.table('budget_items').update({
        'name': data['name'],
        'amount': data['amount']
    }).eq('id', data['id']).execute()
    return jsonify({'status': 'updated'})

@app.route('/delete_item', methods=['POST'])
def delete_item():
    if session.get('user_id') == 'demo':
        return jsonify({'status': 'demo'})
    data = request.json
    supabase.table('budget_items').delete().eq('id', data['id']).execute()
    return jsonify({'status': 'deleted'})

@app.route('/get_items')
def get_items():
    if session.get('user_id') == 'demo':
        return jsonify([])
    now = datetime.now()
    month = int(request.args.get('month', now.month))
    year = int(request.args.get('year', now.year))
    response = supabase.table('budget_items').select('*').eq('user_id', session['user_id']).eq('month', month).eq('year', year).execute()
    return jsonify(response.data)

# ----- GOALS ROUTES -----

@app.route('/goals')
def goals():
    if 'user' not in session:
        return redirect(url_for('login'))
    if session.get('user_id') == 'demo':
        return render_template('goals.html', goals=[])
    response = supabase.table('savings_goals').select('*').eq('user_id', session['user_id']).execute()
    return render_template('goals.html', goals=response.data)

@app.route('/save_goal', methods=['POST'])
def save_goal():
    if session.get('user_id') == 'demo':
        return jsonify({'status': 'demo'})
    data = request.json
    response = supabase.table('savings_goals').insert({
        'user_id': session['user_id'],
        'name': data['name'],
        'target_amount': data['target_amount'],
        'current_amount': data.get('current_amount', 0),
        'target_date': data.get('target_date')
    }).execute()
    return jsonify({'status': 'saved', 'id': response.data[0]['id']})

@app.route('/update_goal', methods=['POST'])
def update_goal():
    if session.get('user_id') == 'demo':
        return jsonify({'status': 'demo'})
    data = request.json
    contribution_amount = float(data['contribution'])
    goal_id = data['id']
    supabase.table('goal_contributions').insert({
        'user_id': session['user_id'],
        'goal_id': goal_id,
        'amount': contribution_amount
    }).execute()
    contributions = supabase.table('goal_contributions').select('amount').eq('goal_id', goal_id).execute()
    new_total = sum(c['amount'] for c in contributions.data)
    supabase.table('savings_goals').update({
        'current_amount': new_total
    }).eq('id', goal_id).execute()
    return jsonify({'status': 'updated', 'new_total': new_total})

@app.route('/get_contributions/<goal_id>')
def get_contributions(goal_id):
    if session.get('user_id') == 'demo':
        return jsonify([])
    response = supabase.table('goal_contributions').select('*').eq('goal_id', goal_id).order('created_at', desc=True).execute()
    return jsonify(response.data)

@app.route('/delete_goal', methods=['POST'])
def delete_goal():
    if session.get('user_id') == 'demo':
        return jsonify({'status': 'demo'})
    data = request.json
    supabase.table('savings_goals').delete().eq('id', data['id']).execute()
    return jsonify({'status': 'deleted'})

# ----- NET WORTH ROUTES -----

@app.route('/networth')
def networth():
    if 'user' not in session:
        return redirect(url_for('login'))
    if session.get('user_id') == 'demo':
        return render_template('networth.html', items=[], total_assets=0, total_liabilities=0, net_worth=0)
    response = supabase.table('net_worth_items').select('*').eq('user_id', session['user_id']).execute()
    items = response.data
    total_assets = sum(i['amount'] for i in items if i['type'] == 'asset')
    total_liabilities = sum(i['amount'] for i in items if i['type'] == 'liability')
    net_worth = total_assets - total_liabilities
    return render_template('networth.html', items=items, total_assets=total_assets, total_liabilities=total_liabilities, net_worth=net_worth)

@app.route('/save_networth', methods=['POST'])
def save_networth():
    if session.get('user_id') == 'demo':
        return jsonify({'status': 'demo'})
    data = request.json
    response = supabase.table('net_worth_items').insert({
        'user_id': session['user_id'],
        'type': data['type'],
        'name': data['name'],
        'amount': data['amount']
    }).execute()
    return jsonify({'status': 'saved', 'id': response.data[0]['id']})

@app.route('/delete_networth', methods=['POST'])
def delete_networth():
    if session.get('user_id') == 'demo':
        return jsonify({'status': 'demo'})
    data = request.json
    supabase.table('net_worth_items').delete().eq('id', data['id']).execute()
    return jsonify({'status': 'deleted'})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)