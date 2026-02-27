#!flask/bin/python
from flask import Flask, jsonify, abort, request, make_response, url_for
from flask import render_template, redirect, session
from werkzeug.security import generate_password_hash, check_password_hash
from dotenv import load_dotenv
from pymongo import MongoClient
import os
import boto3    
import time
import datetime
import exifread
import json
import certifi

# Load environment variables
load_dotenv()

app = Flask(__name__, static_url_path="/assets", static_folder="assets")
app.secret_key = os.getenv("FLASK_SECRET_KEY", "fallback-secret-for-dev")

# Directory and File Settings
UPLOAD_FOLDER = os.path.join(app.root_path, 'media')
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

ALLOWED_EXTENSIONS = set(['png', 'jpg', 'jpeg'])

# AWS Settings (Still used for S3)
AWS_ACCESS_KEY = os.getenv("AWS_ACCESS_KEY")
AWS_SECRET_KEY = os.getenv("AWS_SECRET_KEY")
REGION = os.getenv("AWS_REGION", "us-east-2")
BUCKET_NAME = os.getenv("BUCKET_NAME", "my-cloud-gallery-2026")

# MongoDB Settings
MONGO_URI = os.getenv("MONGO_URI")
client = MongoClient(MONGO_URI, tlsCAFile=certifi.where())
db = client['CloudGalleryDB']
users_collection = db['Users']
photos_collection = db['PhotoGallery']

# --- Helper Functions ---

def get_current_user():
    return session.get('user_id')

def login_required(f):
    def decorated_function(*args, **kwargs):
        if not get_current_user():
            return redirect('/login')
        return f(*args, **kwargs)
    decorated_function.__name__ = f.__name__
    return decorated_function

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def getExifData(path_name):
    with open(path_name, 'rb') as f:
        tags = exifread.process_file(f)
    ExifData = {}
    for tag in tags.keys():
        if tag not in ('JPEGThumbnail', 'TIFFThumbnail', 'Filename', 'EXIF MakerNote'):
            ExifData[str(tag)] = str(tags[tag])
    return ExifData

def s3uploading(filename, filenameWithPath, username):
    s3 = boto3.client('s3', aws_access_key_id=AWS_ACCESS_KEY,
                      aws_secret_access_key=AWS_SECRET_KEY)
    bucket = BUCKET_NAME
    path_filename = "photos/" + username + "/" + filename
    s3.upload_file(filenameWithPath, bucket, path_filename)
    s3.put_object_acl(ACL='public-read', Bucket=bucket, Key=path_filename)
    return f"https://{BUCKET_NAME}.s3.{REGION}.amazonaws.com/{path_filename}"

# --- Routes ---

@app.route('/', methods=['GET', 'POST'])
def home_page():
    user_id = get_current_user()
    if not user_id:
        return redirect('/login')
    
    # MongoDB find instead of DynamoDB scan
    items = list(photos_collection.find({'UserID': user_id}))
    return render_template('index.html', photos=items, username=session.get('username'))

@app.route('/add', methods=['GET', 'POST'])
@login_required
def add_photo():
    if request.method == 'POST':
        user_id = get_current_user()
        username = session.get('username')
        file = request.files['imagefile']
        title = request.form['title']
        tags = request.form['tags']
        description = request.form['description']

        if file and allowed_file(file.filename):
            filename = file.filename
            filenameWithPath = os.path.join(UPLOAD_FOLDER, filename)
            file.save(filenameWithPath)
            
            uploadedFileURL = s3uploading(filename, filenameWithPath, username)
            ExifData = getExifData(filenameWithPath)
            ts = time.time()
            timestamp = datetime.datetime.fromtimestamp(ts).strftime('%Y-%m-%d %H:%M:%S')

            # MongoDB insert_one
            photos_collection.insert_one({
                "PhotoID": str(int(ts * 1000)),
                "UserID": user_id,
                "CreationTime": timestamp,
                "Title": title,
                "Description": description,
                "Tags": tags,
                "URL": uploadedFileURL,
                "ExifData": json.dumps(ExifData)
            })

        return redirect('/')
    return render_template('form.html')

@app.route('/<photoID>', methods=['GET'])
@login_required
def view_photo(photoID):
    user_id = get_current_user()
    photo = photos_collection.find_one({'PhotoID': str(photoID), 'UserID': user_id})
    
    if not photo:
        abort(404)
        
    tags = photo['Tags'].split(',')
    exifdata = json.loads(photo['ExifData'])
    return render_template('photodetail.html', photo=photo, tags=tags, exifdata=exifdata)

@app.route('/search', methods=['GET'])
@login_required
def search_page():
    user_id = get_current_user()
    query = request.args.get('query', "")

    # MongoDB flexible search with Case-Insensitive Regex
    search_filter = {
        'UserID': user_id,
        '$or': [
            {'Title': {'$regex': query, '$options': 'i'}},
            {'Description': {'$regex': query, '$options': 'i'}},
            {'Tags': {'$regex': query, '$options': 'i'}}
        ]
    }
    items = list(photos_collection.find(search_filter))
    return render_template('search.html', photos=items, searchquery=query)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        user = users_collection.find_one({'Username': username})
        
        if user and check_password_hash(user['Password'], password):
            session['user_id'] = user['UserID']
            session['username'] = user['Username']
            return redirect('/')
        
        return render_template('login.html', error='Invalid username or password')
    return render_template('login.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        confirm_password = request.form['confirm_password']

        if not username or not password:
            return render_template('signup.html', error='Username and password required')
        if password != confirm_password:
            return render_template('signup.html', error='Passwords do not match')

        if users_collection.find_one({'Username': username}):
            return render_template('signup.html', error='Username already exists')

        user_id = str(int(time.time() * 1000))
        hashed_password = generate_password_hash(password)
        
        users_collection.insert_one({
            'UserID': user_id,
            'Username': username,
            'Password': hashed_password,
            'CreatedAt': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        })

        session['user_id'] = user_id
        session['username'] = username
        return redirect('/')
    return render_template('signup.html')

@app.route('/logout', methods=['GET'])
def logout():
    session.clear()
    return redirect('/login')

if __name__ == '__main__':
    app.run(debug=True, host="0.0.0.0", port=5001)