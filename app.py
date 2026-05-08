from flask import Flask, render_template, request, redirect, url_for, session
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
    return render_template('index.html')

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
    return redirect(url_for('login'))

@app.route('/demo')
def demo():
    session['user'] = 'demo'
    return redirect(url_for('home'))

if __name__ == '__main__':
    app.run(debug=True)
