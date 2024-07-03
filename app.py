from datetime import datetime
import pickle
from flask import Flask, json, render_template, request, redirect, url_for, session
from flask_bootstrap import Bootstrap
import pandas as pd
import plotly.graph_objs as go
import plotly.io as pio
from pymongo import MongoClient
from model import predict_model
import bcrypt
import urllib.parse
import secret

app = Flask(__name__)
app.secret_key = secret.FLASK_KEY
Bootstrap(app)

username = urllib.parse.quote_plus(secret.MONGO_USER)
password = urllib.parse.quote_plus(secret.MONGO_PASSWORD)

client = MongoClient(f'mongodb+srv://{username}:{password}@cluster0.1qgr6hv.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0')
db = client.get_database("proyectos_profesionales")
models = db['models']
users = db['users']
stats = db['stats']

# Initialize model
model_path = models.find_one({"fecha_deprecated": ""})
with open(model_path["ruta"], 'rb') as model_file:
    try:
        latest_model = pickle.load(model_file)
    except:
        raise "Error loading the model"

@app.route('/', methods=['GET', 'POST'])
def home():
    if request.method == 'POST':
        session.clear()
        return redirect(url_for('home'))
    
    if 'username' in session:
        is_logged = True
    else:
        is_logged = False

    df = pd.DataFrame(list(stats.find()))
    usage_fig = go.Figure(data=go.Histogram(x=df["timestamp"]))
    usage_fig.update_layout(title_text="Usage over Time")
    graphJSON = pio.to_json(usage_fig)

    return render_template('home.html', is_logged=is_logged, graphJSON=graphJSON)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        user = users.find_one({"username": username})
        
        if user and bcrypt.checkpw(request.form['password'].encode('utf-8'), user['password']):
            session['username'] = username
            return redirect(url_for('home'))
        
        return "Invalid login"

    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = bcrypt.hashpw(request.form['password'].encode('utf-8'), bcrypt.gensalt())

        if users.find_one({"username": username}):
            return "User already exists"
        
        if users.find_one({"email": email}):
            return "Email already exists"
        
        users.insert_one({"username": username, "email": email, "password": password, "user_created": datetime.now()})
        session['username'] = username
        return redirect(url_for('home'))
    else:
        return render_template('register.html')

@app.route('/predict', methods=['GET', 'POST'])
def predict():
    prediction_str = ''
    if 'username' not in session:
        return redirect(url_for('login'))
    
    if request.method == 'POST' and len(request.form) > 0:
        features = request.form.to_dict()
        prediction = predict_model(latest_model, features)

        # Upload stats
        prediction_data = {
            "username": session['username'],
            "features": dict(features),
            "prediction": int(prediction),
            "timestamp": datetime.now()
        }
        stats.insert_one(prediction_data)

        # Display result
        if prediction == 1:
            prediction_str = "Rains are expected for the day"
        else:
            prediction_str = "No rain is expected"

        return render_template('prediction.html', prediction_str=prediction_str)
    
    if model_path:
        fecha_pro = f"Latest model as of {str(model_path['fecha_pro'])}"
        prediction_params = [element["variable"] for element in model_path["variables"]]
        return render_template('prediction.html', params=prediction_params, fecha=fecha_pro)
    else:
        return "No valid model available"

if __name__ == '__main__':
    app.run(debug=True)