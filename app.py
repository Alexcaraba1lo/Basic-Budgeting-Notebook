from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from supabase import create_client
from dotenv import load_dotenv
import os

load_dotenv()

app = Flask(__name__)
app.secret_key = os.urandom(24)

supabase = create_client(
    os.getenv('SUPABASE_URL'),
    os.getenv('SUPABASE_KEY')
)

@app.route('/')
def home():
    if 'user' not in session:
        return redirect(url_for('login'))
    return render_template('index.html', user=session['user'])

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
            session['user'] = response.user.email
            session['user_id'] = response.user.id
            return redirect(url_for('home'))
        except:
            return render_template('login.html', error='Invalid email or password')
    message = request.args.get('message')
    return render_template('login.html', message=message)

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        try:
            supabase.auth.sign_up({
                "email": email,
                "password": password
            })
            return redirect(url_for('login', message='Account created successfully! Please sign in.'))
        except:
            return render_template('signup.html', error='Could not create account')
    return render_template('signup.html')

@app.route('/logout')
def logout():
    session.pop('user', None)
    session.pop('user_id', None)
    return redirect(url_for('login'))

@app.route('/demo')
def demo():
    session['user'] = 'demo'
    session['user_id'] = 'demo'
    return redirect(url_for('home'))

@app.route('/save_item', methods=['POST'])
def save_item():
    if session.get('user_id') == 'demo':
        return jsonify({'status': 'demo'})
    data = request.json
    from datetime import datetime
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
    from datetime import datetime
    now = datetime.now()
    month = int(request.args.get('month', now.month))
    year = int(request.args.get('year', now.year))
    response = supabase.table('budget_items').select('*').eq('user_id', session['user_id']).eq('month', month).eq('year', year).execute()
    return jsonify(response.data)

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
            except Exception as e:
                error = 'Could not update password'
        
        elif action == 'delete_account':
            try:
                supabase.table('budget_items').delete().eq('user_id', session['user_id']).execute()
                session.clear()
                return redirect(url_for('login', message='Account deleted successfully'))
            except Exception as e:
                error = 'Could not delete account'
    
    return render_template('profile.html', user=session['user'], message=message, error=error)

if __name__ == '__main__':
    app.run(debug=True)
