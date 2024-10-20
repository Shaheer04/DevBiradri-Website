from flask import Flask, render_template, request,redirect, url_for
from pymongo import MongoClient
from bson.objectid import ObjectId
from dotenv import load_dotenv,find_dotenv
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

load_dotenv(find_dotenv())
mongo_url = os.getenv('MONGO_URL')
username = os.getenv('SMTP_USERNAME')
password = os.getenv('SMTP_PASSWORD')
smtp_server = os.getenv('SMTP_SERVER')
smtp_port = os.getenv('SMTP_PORT')


app = Flask(__name__)

# Connect to MongoDB
client = MongoClient(mongo_url)
db = client['Cluster0']
collection = db['registration_form_submissions']

def send_confirmation_email(recipient, name):
    sender_email = username
    message = MIMEMultipart("alternative")
    message["Subject"] = "Registration Confirmation"
    message["From"] = sender_email
    message["To"] = recipient

    # Create the HTML version of your message
    html = render_template('email_template.html', name=name)
    
    # Turn these into plain/html MIMEText objects
    part = MIMEText(html, "html")
    
    # Add HTML part to MIMEMultipart message
    message.attach(part)
    
    # Send the email
    with smtplib.SMTP(smtp_server, smtp_port) as server:
        server.starttls()  # Secure the connection
        server.login(username, password)
        server.sendmail(sender_email, recipient, message.as_string())

@app.route('/')
def index():
    return render_template('index.html')


@app.route('/register', methods=['GET', 'POST'])
def evnet_register():
    if request.method == 'POST':
            # Extract form data
            form_data = {
                'fullname': request.form.get('fullname'),
                'email': request.form.get('email'),
                'phone': request.form.get('phone'),
                'gender': request.form.get('gender'),
                'profession': request.form.get('profession'),
                'institute_name': request.form.get('institute-name'),
                'linkedin_link': request.form.get('linkedin-link'),
                'heard_about_us': request.form.get('heared-us'),
                'expectations': request.form.get('message'),
                'joined_whatsapp': request.form.get('ws-group')
            }
            
            #Check if email is already registered
            if collection.find_one({'email': form_data['email']}):
                return "Email already registered!"
            
            # Save data to MongoDB
            result = collection.insert_one(form_data)

            try:
                send_confirmation_email(form_data['email'], form_data['fullname'])
            except Exception as e:
                print(f"Failed to send email: {e}")
            
            # Redirect to a success page or back to the form
            return redirect(url_for('success'))
    
    return render_template('register.html')

@app.route('/success')
def success():
    return "Form submitted successfully! Please check your email for confirmation."

if __name__ == '__main__':
    app.run(debug=True)