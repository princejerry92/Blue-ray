# --- Core Python Libraries ---
import os
import sys
import logging
import json
import secrets
import sqlite3
import atexit
import signal
import datetime
from functools import wraps
from multiprocessing import Process, freeze_support
from io import BytesIO
import re
import dns
from dns import (
    asyncbackend,
    asyncquery,
    asyncresolver,
    e164,
    namedict,
    tsigkeyring,
    versioned,
    dnssec,
    name,
    message,
    resolver,
    exception,
    rdatatype,
    rdataclass,
    rdata,
    flags,
    rrset,
    renderer,
    rdtypes,
    tokenizer,
    wire,
    zone,
    ipv4,
    ipv6,
    query,
    update,
    reversename
)


# --- Werkzeug & Flask ---
from flask import (
    Flask, send_from_directory, render_template, request, session,
    flash, jsonify, Response, send_file, abort
)
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.exceptions import HTTPException

# --- Flask Extensions ---
from flask_socketio import SocketIO, emit
from flask_cors import CORS

# --- File Processing Libraries ---
from PIL import Image
from PyPDF2 import PdfReader
from docx import Document
import extractdocx  

# --- Server & Multiprocessing ---
from pyQtwin import FuturisticBrowser, QApplication  # For the GUI launcher

# ==============================================================================
# 1. APPLICATION CONFIGURATION & INITIALIZATION
# ==============================================================================

# --- Configure Logging ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - [%(funcName)s] - %(message)s')
logger = logging.getLogger('exam_app')

# --- Directory Constants ---
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
MAIN_DIR = os.path.join(BASE_DIR, 'ExamTester')
UPLOAD_FOLDER = os.path.join(MAIN_DIR, 'Uploads')
RESULTS_FOLDER = os.path.join(MAIN_DIR, 'Results')
QUESTIONS_FOLDER = os.path.join(MAIN_DIR, 'Questions')

SUBDIRECTORIES = ["Class", "Results", "Questions", "Passwords", "Logger", "Uploads"]
CLASS_SUBFOLDERS = ["Jss1", "Jss2", "Jss3", "SS1", "SS2", "SS3"]

# Ensure core directories exist
for folder in [UPLOAD_FOLDER, RESULTS_FOLDER, QUESTIONS_FOLDER]:
    os.makedirs(folder, exist_ok=True)
    
# --- Flask App Initialization ---
app = Flask(__name__, template_folder='templates', static_folder='static')

# --- Security Best Practice: Use a strong, secret key loaded from environment ---
# This key is crucial for signing the session cookie.
# For development, you can set it in your terminal: export FLASK_SECRET_KEY='your-long-random-string'
app.secret_key = os.environ.get('FLASK_SECRET_KEY', 'dev-secret-key-is-not-secure-use-env-var')

# --- App Configuration ---
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['RESULTS_FOLDER'] = RESULTS_FOLDER
app.config['QUESTIONS_FOLDER'] = QUESTIONS_FOLDER
app.config['ALLOWED_EXTENSIONS'] = {'txt', 'pdf', 'doc', 'docx', 'jpeg', 'jpg', 'png', 'json'}
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB file size limit

# --- Socket.IO Initialization ---
# Using the simpler and stable 'threading' mode.
socketio = SocketIO(app, async_mode='threading', logger=True, engineio_logger=True)

# --- Global In-Memory State (for non-persistent data) ---
# Used to track currently connected clients and their roles.
connected_clients = {}

# ==============================================================================
# 2. DATABASE SETUP & HELPERS
# ==============================================================================

DATABASE_NAME = 'users.db'

def get_db_connection():
    """Establishes a connection to the SQLite database."""
    conn = sqlite3.connect(DATABASE_NAME)
    conn.row_factory = sqlite3.Row  # Makes accessing columns by name easy
    return conn

def init_db():
    """Initializes the database and creates all necessary tables if they don't exist."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Admins table with hashed passwords
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS admins (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL
        )
        ''')

        # Create a default admin if none exist
        cursor.execute("SELECT id FROM admins LIMIT 1")
        if cursor.fetchone() is None:
            default_username = 'admin1'
            default_password = '@RoyalRangers'
            hashed_password = generate_password_hash(default_password)
            cursor.execute(
                "INSERT INTO admins (username, password_hash) VALUES (?, ?)",
                (default_username, hashed_password)
            )
            logger.info(f"Created default admin '{default_username}' with password '{default_password}'.")

        # Table for files managed by the CRUD system
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS files (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            filename TEXT NOT NULL,
            subdirectory TEXT NOT NULL,
            filetype TEXT NOT NULL,
            filepath TEXT NOT NULL  -- Store the path to the file on the filesystem
        )
        ''')

        # Table for CORS origins
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS cors_origins (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            origin TEXT UNIQUE NOT NULL
        )
        ''')
        
        # The main table to replace the old `data_store` dictionary.
        # This table persists all data related to a single exam session.
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS exam_sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT UNIQUE NOT NULL,
            admin_username TEXT NOT NULL,
            
            --  NEW COLUMN --
            exam_code TEXT UNIQUE, 

            exam_time TEXT,
            subject_name TEXT,
            question_length INTEGER,
            question_template_filename TEXT,
            answer_template_filename TEXT,
            contains_images INTEGER DEFAULT 0,
            extracted_questions_json TEXT,
            extracted_answers_json TEXT,
            student_details_json TEXT,
            student_answers_json TEXT,
            student_score INTEGER,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
        ''')
        # Trigger to auto-update the 'updated_at' timestamp
        cursor.execute('''
        CREATE TRIGGER IF NOT EXISTS update_exam_sessions_updated_at
        AFTER UPDATE ON exam_sessions
        FOR EACH ROW
        BEGIN
            UPDATE exam_sessions SET updated_at = CURRENT_TIMESTAMP WHERE id = OLD.id;
        END;
        ''')

        conn.commit()
        logger.info("Database initialized successfully.")
    except sqlite3.Error as e:
        logger.error(f"Database initialization error: {e}")
    finally:
        if conn:
            conn.close()

# Initialize the database on startup
init_db()

def get_or_create_exam_session(flask_session_id, admin_username):
    """
    Retrieves an existing exam session from the DB or creates a new one.
    This is the central function for managing exam state.
    """
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM exam_sessions WHERE session_id = ?", (flask_session_id,))
        exam_session = cursor.fetchone()
        if exam_session:
            return dict(exam_session)
        else:
            cursor.execute(
                "INSERT INTO exam_sessions (session_id, admin_username) VALUES (?, ?)",
                (flask_session_id, admin_username)
            )
            conn.commit()
            cursor.execute("SELECT * FROM exam_sessions WHERE session_id = ?", (flask_session_id,))
            return dict(cursor.fetchone())
        
def create_directory(path):
    """Helper function to create a directory if it doesn't exist."""
    if not os.path.exists(path):
        os.makedirs(path)
        return f"Created directory: {path}"
    else:
        return f"Directory already exists: {path}"
    


# ==============================================================================
# 3. CORS CONFIGURATION
# ==============================================================================

def get_allowed_origins():
    """Fetches allowed CORS origins from the database."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT origin FROM cors_origins')
        origins = [row['origin'] for row in cursor.fetchall()]
    return origins

def update_cors_config():
    """Dynamically updates the CORS configuration for the Flask app."""
    allowed_origins = get_allowed_origins() or "*"  # Default to wildcard if DB is empty
    CORS(app,
         resources={r"/*": {"origins": allowed_origins}},
         methods=["GET", "HEAD", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
         allow_headers=["Content-Type", "Authorization"],
         supports_credentials=True)

# Apply CORS config on startup
update_cors_config()

@app.route('/admin/add_origin', methods=['POST'])
def add_origin():
    # Note: This endpoint should be protected to be callable only by an admin
    new_origin = request.json.get('origin')
    if not new_origin:
        return jsonify({"error": "Origin is required"}), 400
    try:
        with get_db_connection() as conn:
            conn.execute('INSERT INTO cors_origins (origin) VALUES (?)', (new_origin,))
            conn.commit()
        update_cors_config()
        return jsonify({"message": "Origin added successfully"}), 201
    except sqlite3.IntegrityError:
        return jsonify({"error": "Origin already exists"}), 409


@app.route('/admin/delete_origin', methods=['DELETE'])
def delete_origin():
    # Note: This endpoint should be protected
    origin_to_delete = request.json.get('origin')
    if not origin_to_delete:
        return jsonify({"error": "Origin is required"}), 400
    with get_db_connection() as conn:
        conn.execute('DELETE FROM cors_origins WHERE origin = ?', (origin_to_delete,))
        conn.commit()
    update_cors_config()
    return jsonify({"message": "Origin deleted successfully"}), 200

# ==============================================================================
# 4. HELPER FUNCTIONS
# ==============================================================================

def allowed_file(filename):
    """Checks if the uploaded file has an allowed extension."""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

def find_file_in_directory(directory, filename):
    """Recursively finds a file in a directory."""
    for root, _, files in os.walk(directory):
        if filename in files:
            return os.path.join(root, filename)
    return None

def validate_subdirectory(subdirectory):
    """Validates that a subdirectory is allowed and exists."""
    SUBDIRECTORIES = ["Class", "Results", "Questions", "Passwords", "Logger", "Uploads"]
    if subdirectory not in SUBDIRECTORIES:
        return False, f"Invalid subdirectory. Must be one of {SUBDIRECTORIES}."
    
    path = os.path.join(MAIN_DIR, subdirectory)
    # No need to check for existence, as we can create it.
    return True, path

def search_file_in_database(filename, subdirectory):
    """
    Searches the database for a file and returns its stored filepath.
    This is now a helper and not directly used by the /get_file endpoint.
    """
    with get_db_connection() as conn:
        # Correctly query the 'filepath' column.
        cursor = conn.execute(
            'SELECT filepath FROM files WHERE filename = ? AND subdirectory = ?',
            (filename, subdirectory)
        )
        result = cursor.fetchone()
    return result['filepath'] if result else None

# create exam code for admin2
def _generate_unique_code(conn):
    """
    Helper function to generate a unique 6-character alphanumeric code.
    It checks the database to ensure the code is not already in use.
    """
    while True:
        # Generate a simple, readable code (e.g., A9B2C1)
        code = ''.join(secrets.choice('ABCDEFGHJKLMNPQRSTUVWXYZ23456789') for _ in range(6))
        
        # Check if this code already exists in the database
        cursor = conn.execute("SELECT id FROM exam_sessions WHERE exam_code = ?", (code,))
        if cursor.fetchone() is None:
            # If it doesn't exist, we can use it.
            return code
        
def result_format(file_content):
    """
    Parses and formats a raw result file content into a more structured format.
    This function remains as you provided it.
    """
    lines = file_content.splitlines()
    header_lines = []
    student_answers = {}
    correct_answers = {}
    
    # Separate header from answer lines
    answer_section_started = False
    for line in lines:
        if line.strip().lower().startswith("student answers:"):
            answer_section_started = True
            student_answers_str = line.split(":", 1)[1].strip()
            # Handle both "q1:A q2:B" and "1A 2B" formats
            answers = re.findall(r'(\d+):?([A-Z])', student_answers_str)
            for q_num, ans in answers:
                student_answers[int(q_num)] = ans
        elif line.strip().lower().startswith("correct answers:"):
            answer_section_started = True
            correct_answers_str = line.split(":", 1)[1].strip()
            answers = re.findall(r'(\d+):?([A-Z])', correct_answers_str)
            for q_num, ans in answers:
                correct_answers[int(q_num)] = ans
        elif not answer_section_started:
            header_lines.append(line)

    # Rebuild the formatted content
    formatted_content = "\n".join(header_lines) + "\n\n"
    
    student_answers_formatted = "\n".join([f"  Question {q}: {a}" for q, a in sorted(student_answers.items())])
    correct_answers_formatted = "\n".join([f"  Question {q}: {a}" for q, a in sorted(correct_answers.items())])

    formatted_content += f"Student Answers:\n{student_answers_formatted}\n\n"
    formatted_content += f"Correct Answers:\n{correct_answers_formatted}\n"
    
    return formatted_content

# ==============================================================================
# 5. AUTHENTICATION DECORATOR
# ==============================================================================
from functools import wraps # Make sure this import is at the top of your file

def require_login(f):
    """
    A decorator to protect routes that require an admin to be logged in.
    If the user is not logged in, it aborts the request with a 401 Unauthorized error.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Check the Flask session for the 'logged_in' flag we set during login
        if not session.get('logged_in'):
            logger.warning(f"Unauthorized access attempt to '{f.__name__}' route.")
            # For API-like endpoints, returning JSON is better than redirecting
            return jsonify({"error": "Authentication required to access this resource."}), 401
        
        # If logged in, proceed with the original route function
        return f(*args, **kwargs)
    return decorated_function

# ==============================================================================
# 6. CORE FLASK ROUTES AND ADMIN CONTROL (File Management, Pages, etc.)
# ==============================================================================

@app.route('/')
def loader():
    return render_template('loader.html')

@app.route('/home')
def home():
    return render_template('Home.html')

#the dirgod that brings to birth the main directories
@app.route('/init', methods=['GET'])
def initialize_directories():
    """Initialize the directory structure and return the status messages."""
    messages = []
    
    # Create the main directory
    messages.append(create_directory(MAIN_DIR))
    
    # Create the subdirectories
    for subdirectory in SUBDIRECTORIES:
        path = os.path.join(MAIN_DIR, subdirectory)
        messages.append(create_directory(path))
    
    # Create the class subfolders
    class_directory = os.path.join(MAIN_DIR, "Class")
    for subfolder in CLASS_SUBFOLDERS:
        path = os.path.join(class_directory, subfolder)
        messages.append(create_directory(path))
    
    return jsonify(messages=messages)
        

# --- Admin Authentication Endpoints ---

def _handle_admin_login(username, password):
    """Shared logic for checking admin credentials."""
    with get_db_connection() as conn:
        admin = conn.execute('SELECT * FROM admins WHERE username = ?', (username,)).fetchone()

    if admin and check_password_hash(admin['password_hash'], password):
        # Successful login: store user info in the secure session
        session.clear()
        session['logged_in'] = True
        session['username'] = admin['username']
        session['session_id'] = secrets.token_hex(16) # Unique ID for this browser session
        logger.info(f"Admin '{username}' logged in successfully. Session ID: {session['session_id']}")
        return True
    return False

@app.route('/check_password', methods=['POST'])
def check_password():
    """Endpoint for general admin login."""
    data = request.get_json()
    username = data.get('username', '').strip().lower()
    password = data.get('password', '')

    if _handle_admin_login(username, password):
        return jsonify({
            "message": "Session created",
            "session_id": session['session_id']
        }), 200
    else:
        logger.warning(f"Failed login attempt for username: '{username}'")
        return jsonify({"error": "Invalid username or password"}), 401

@app.route('/portal_admin', methods=['POST'])
def portal_admin():
    """Endpoint for the result portal admin login."""
    data = request.get_json()
    username = data.get('username', '').strip().lower()
    password = data.get('password', '')

    if _handle_admin_login(username, password):
        # The frontend expects a token. We generate one for compatibility,
        # but the true authorization is handled by the server-side session.
        login_token = secrets.token_hex(16)
        session['login_token'] = login_token
        return jsonify({"message": "Password is correct", "token": login_token}), 200
    else:
        return jsonify({"error": "Password is incorrect"}), 401

@app.route('/new_admin', methods=['POST'])
def new_admin():
    """Registers a new admin with a securely hashed password."""
    data = request.get_json()
    username = data.get('username', '').strip().lower()
    password = data.get('password', '')

    if not username or not password:
        return jsonify({"error": "Username and password are required."}), 400
    if not password.startswith('@'):
        return jsonify({"error": "Password must start with '@'."}), 400

    try:
        with get_db_connection() as conn:
            hashed_password = generate_password_hash(password)
            conn.execute(
                "INSERT INTO admins (username, password_hash) VALUES (?, ?)",
                (username, hashed_password)
            )
            conn.commit()
        logger.info(f"New admin '{username}' registered successfully.")
        return jsonify({"message": "New admin registered successfully."}), 201
    except sqlite3.IntegrityError:
        return jsonify({"error": "Username already exists."}), 409
    except Exception as e:
        logger.error(f"Error creating new admin: {e}")
        return jsonify({"error": "A database error occurred."}), 500

@app.route('/get_active_sessions', methods=['GET'])
@require_login
def get_active_sessions():
    """
    Retrieves a list of all exam sessions that have been prepared (have a code)
    or are currently in progress (have student details).
    """
    try:
        with get_db_connection() as conn:
            # Fetches sessions that are relevant for monitoring
            cursor = conn.execute(
                """SELECT id, exam_code, subject_name, student_details_json 
                   FROM exam_sessions 
                   WHERE exam_code IS NOT NULL 
                   ORDER BY updated_at DESC"""
            )
            sessions = cursor.fetchall()
            
            session_list = []
            for row in sessions:
                student_name = "Waiting for student..."
                if row['student_details_json']:
                    student_details = json.loads(row['student_details_json'])
                    student_name = student_details.get('name', 'In Progress')

                session_list.append({
                    "id": row['id'],
                    "exam_code": row['exam_code'],
                    "subject": row['subject_name'],
                    "student": student_name
                })
                
        return jsonify(session_list), 200
    except Exception as e:
        logger.error(f"Error fetching active sessions: {e}")
        return jsonify({"error": "Failed to fetch active sessions."}), 500

@socketio.on('terminate_session')
@require_login # Custom decorator to check if the user is an admin via session
def handle_terminate_session(data):
    """
    Allows an admin to forcefully terminate an active exam session.
    This could involve deleting the session record or marking it as 'terminated'.
    """
    session_id_to_terminate = data.get('session_id')
    if not session_id_to_terminate:
        return
        
    try:
        with get_db_connection() as conn:
            # For now, we'll just delete the record.
            # A softer approach would be to set a 'status' column to 'terminated'.
            conn.execute("DELETE FROM exam_sessions WHERE id = ?", (session_id_to_terminate,))
            conn.commit()
        
        logger.warning(f"Admin '{session.get('username')}' terminated exam session ID: {session_id_to_terminate}")
        # Notify all admins that the session list has changed
        socketio.emit('sessions_updated')
    except Exception as e:
        logger.error(f"Error terminating session {session_id_to_terminate}: {e}")

# --- File Upload and Download Routes ---

@app.route('/upload', methods=['POST'])
def upload_file():
    # This endpoint should be protected so only admins can upload.
    if not session.get('logged_in'):
        return jsonify({"error": "Authentication required"}), 401
        
    if 'file' not in request.files:
        return jsonify({"error": "No file part in the request"}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400

    if allowed_file(file.filename):
        filename = secure_filename(file.filename)
        subdirectory = request.form.get('subdirectory', '').strip()
        upload_path = os.path.join(UPLOAD_FOLDER, subdirectory)
        os.makedirs(upload_path, exist_ok=True)
        filepath = os.path.join(upload_path, filename)
        
        try:
            file.save(filepath)
            logger.info(f"File '{filename}' uploaded to '{filepath}' by admin '{session.get('username')}'")
            
            # Notify connected clients of the new file
            socketio.emit('file_uploaded', {'filename': filename, 'subdirectory': subdirectory})
            
            return jsonify({"message": "File uploaded successfully"}), 200
        except Exception as e:
            logger.error(f"Error saving uploaded file: {e}")
            return jsonify({"error": "Failed to save file"}), 500
    else:
        return jsonify({"error": "File type not allowed"}), 400

@app.route('/downloads')
def download_from_server():
    """Lists all available files for download."""
    all_files = []
    # Simplified to only list from UPLOAD_FOLDER for clarity
    for root, _, files in os.walk(UPLOAD_FOLDER):
        for file in files:
            relative_path = os.path.relpath(os.path.join(root, file), UPLOAD_FOLDER)
            all_files.append((relative_path, 'Uploads'))
            
    return render_template('downloads.html', files=all_files, message='No files found' if not all_files else None)

@app.route('/download/<folder>/<path:filename>', methods=['GET'])
def download_files(folder, filename):
    """Serves a file for download from the specified folder."""
    directory = UPLOAD_FOLDER if folder == 'Uploads' else QUESTIONS_FOLDER
    
    # Securely join path to prevent directory traversal
    safe_path = os.path.abspath(os.path.join(directory, filename))
    if not safe_path.startswith(os.path.abspath(directory)):
        abort(404)

    try:
        return send_from_directory(directory, filename, as_attachment=True)
    except FileNotFoundError:
        abort(404)
        
#.....File RETRIVER.......
@app.route('/files', methods=['GET'])
@require_login # Protect this endpoint so only logged-in admins can see the file list
def get_files():
    """
    Retrieve a de-duplicated list of all managed files from both the database
    and the main file directories (Uploads, Questions, Results).
    """
    logger.info('Received request to retrieve all managed files.')
    all_files = {}
    seen_files = set() # Use a set to track seen files and prevent duplicates

    # --- Step 1: Scan all relevant directories on the filesystem ---
    # We scan first so the database can be treated as the "override" or primary source.
    directories_to_scan = {
        "Uploads": UPLOAD_FOLDER,
        "Questions": QUESTIONS_FOLDER,
        "Results": RESULTS_FOLDER,
        # Add other directories you want to be scannable here
    }

    for subdir_name, dir_path in directories_to_scan.items():
        if not os.path.exists(dir_path):
            continue # Skip if directory doesn't exist

        for root, _, files in os.walk(dir_path):
            for filename in files:
                # Create a unique identifier for each file to handle duplicates
                file_identifier = (subdir_name, filename)
                if file_identifier in seen_files:
                    continue # Skip if we've already processed this file

                if subdir_name not in all_files:
                    all_files[subdir_name] = []

                all_files[subdir_name].append({
                    'filename': filename,
                    'filetype': os.path.splitext(filename)[1][1:], # Get extension
                    'source': 'filesystem'
                })
                seen_files.add(file_identifier)

    # --- Step 2: Query the database and merge results ---
    # This ensures files tracked by the DB are always included.
    try:
        with get_db_connection() as conn:
            cursor = conn.execute('SELECT subdirectory, filename, filetype FROM files')
            db_files = cursor.fetchall()

        for row in db_files:
            file_identifier = (row['subdirectory'], row['filename'])
            if file_identifier in seen_files:
                continue # Already found on the filesystem, so we skip it to avoid duplicates

            if row['subdirectory'] not in all_files:
                all_files[row['subdirectory']] = []

            all_files[row['subdirectory']].append({
                'filename': row['filename'],
                'filetype': row['filetype'],
                'source': 'database'
            })
            seen_files.add(file_identifier)

    except sqlite3.Error as e:
        logger.error(f"Error retrieving files from database: {e}")
        # We can still return filesystem files even if the DB fails
        # but we should notify the client of a partial failure.
        if not all_files:
            return jsonify({"error": "Failed to retrieve any files."}), 500

    logger.info(f"Returning {len(seen_files)} unique files across all sources.")
    return jsonify(all_files)


@app.route('/get_file/<subdirectory>/<filename>')
@require_login # Protect this endpoint
def get_file(subdirectory, filename):
    """
    Securely serves a file from its specified subdirectory.
    This replaces the old version which had a hardcoded path.
    """
    logger.debug(f"Request to get file '{filename}' from subdirectory '{subdirectory}'")

    # Map the subdirectory name to its actual path on the server
    # This acts as a safelist and prevents arbitrary path requests.
    allowed_dirs = {
        "Uploads": UPLOAD_FOLDER,
        "Questions": QUESTIONS_FOLDER,
        "Results": RESULTS_FOLDER,
        "Class": os.path.join(MAIN_DIR, "Class"),
        "Passwords": os.path.join(MAIN_DIR, "Passwords"),
        "Logger": os.path.join(MAIN_DIR, "Logger"),
    }

    base_path = allowed_dirs.get(subdirectory)

    if not base_path:
        logger.warning(f"Access attempt to an invalid or non-whitelisted subdirectory: '{subdirectory}'")
        return jsonify({"error": "Invalid subdirectory"}), 400

    # Secure the filename and create a safe, absolute path
    safe_filename = secure_filename(filename)
    file_path = os.path.abspath(os.path.join(base_path, safe_filename))

    # --- Security Check: Directory Traversal ---
    # Ensure the final resolved path is still within its intended base directory.
    if not file_path.startswith(os.path.abspath(base_path)):
        logger.error(f"Directory traversal attempt blocked: '{filename}'")
        abort(403) # Forbidden

    if os.path.exists(file_path) and os.path.isfile(file_path):
        logger.info(f"Serving file from filesystem: {file_path}")
        return send_file(file_path, as_attachment=True)
    else:
        # As a fallback, check the database for a stored path. This is useful
        # if the file metadata is in the DB but the file is stored elsewhere.
        db_filepath = search_file_in_database(safe_filename, subdirectory)
        if db_filepath and os.path.exists(db_filepath) and os.path.isfile(db_filepath):
             logger.info(f"Serving file from path stored in database: {db_filepath}")
             return send_file(db_filepath, as_attachment=True)

        logger.warning(f"File not found in '{subdirectory}' or database: '{filename}'")
        abort(404) # Not Found
        
@app.route('/view_result', methods=['GET'])
@require_login # Ensure only logged-in admins can view results
def view_result():
    """
    Fetches and formats a single result file from the RESULTS_FOLDER.
    """
    filename = request.args.get('filename')
    if not filename:
        return jsonify({'error': 'Filename not provided'}), 400

    # Secure the filename and build a safe path
    safe_filename = secure_filename(filename)
    filepath = os.path.join(RESULTS_FOLDER, safe_filename)

    # Security check: Ensure the path is within the intended folder
    if not os.path.abspath(filepath).startswith(os.path.abspath(RESULTS_FOLDER)):
        logger.error(f"Attempt to access file outside of RESULTS_FOLDER: {safe_filename}")
        abort(403) # Forbidden

    try:
        if not os.path.exists(filepath):
            return jsonify({'error': 'Result file not found'}), 404

        with open(filepath, 'r', encoding='utf-8') as f:
            file_content = f.read()

        # Use the helper function to format the content
        formatted_content = result_format(file_content)

        return jsonify({'filename': safe_filename, 'content': formatted_content}), 200

    except Exception as e:
        logger.error(f"Error viewing result for '{safe_filename}': {e}")
        return jsonify({'error': 'An error occurred while reading the result file.'}), 500
    
#.........Read and Delete files on the server and database.....

@app.route('/read', methods=['GET'])
@require_login
def read_file():
    """
    Reads the text content of a specified file and returns it as JSON.
    This version uses the `extractdocx` module to handle various file formats.
    """
    subdirectory = request.args.get('subdirectory')
    filename = request.args.get('filename')

    if not subdirectory or not filename:
        return jsonify({"error": "Both 'subdirectory' and 'filename' parameters are required."}), 400

    # Use the secure whitelisting approach
    allowed_dirs = {
        "Uploads": UPLOAD_FOLDER,
        "Questions": QUESTIONS_FOLDER,
        "Results": RESULTS_FOLDER,
    }
    base_path = allowed_dirs.get(subdirectory)

    if not base_path:
        return jsonify({"error": "Access to this subdirectory is not permitted."}), 403

    safe_filename = secure_filename(filename)
    file_path = os.path.join(base_path, safe_filename)

    # Security check to prevent directory traversal
    if not os.path.abspath(file_path).startswith(os.path.abspath(base_path)):
        abort(403)

    if not os.path.exists(file_path):
        return jsonify({"error": f"File '{safe_filename}' not found in '{subdirectory}'."}), 404

    try:
        # --- KEY CHANGE: Delegate all extraction logic to your module ---
        # The extract_text_from_any_file function will handle the details.
        content = extractdocx.extract_text_from_any_file(file_path)
        
        logger.info(f"Admin '{session.get('username')}' read content from file: {file_path}")
        return jsonify({"filename": safe_filename, "content": content})
    
    except ValueError as e:
        # This catches unsupported file types from your `extractdocx` module
        logger.warning(f"Attempted to read unsupported file type: {file_path}. Error: {e}")
        # Return a user-friendly message for binary files we can't read
        content = f"[Cannot display content of this file type: {os.path.splitext(safe_filename)[1]}]"
        return jsonify({"filename": safe_filename, "content": content})

    except Exception as e:
        logger.error(f"Failed to read or process file '{file_path}': {e}")
        return jsonify({"error": f"An error occurred while processing the file: {e}"}), 500


@app.route('/delete', methods=['DELETE'])
@require_login
def delete_file():
    """
    Deletes a file from the filesystem and its corresponding entry from the database.
    """
    data = request.get_json()
    subdirectory = data.get('subdirectory')
    filename = data.get('filename')

    if not subdirectory or not filename:
        return jsonify({"error": "Both 'subdirectory' and 'filename' are required."}), 400

    # Whitelist the allowed directories for deletion
    allowed_dirs = {
        "Uploads": UPLOAD_FOLDER,
        "Questions": QUESTIONS_FOLDER,
        "Results": RESULTS_FOLDER,
    }
    base_path = allowed_dirs.get(subdirectory)

    if not base_path:
        return jsonify({"error": "Deletion from this subdirectory is not permitted."}), 403

    safe_filename = secure_filename(filename)
    file_path = os.path.join(base_path, safe_filename)

    # --- Step 1: Delete from the database ---
    try:
        with get_db_connection() as conn:
            # We delete from the DB first. If this fails, we don't touch the file.
            cursor = conn.execute(
                'DELETE FROM files WHERE subdirectory = ? AND filename = ?',
                (subdirectory, safe_filename)
            )
            conn.commit()
            if cursor.rowcount == 0:
                logger.warning(f"No database entry found for '{safe_filename}' in '{subdirectory}' during delete, but proceeding to filesystem check.")
            else:
                 logger.info(f"Deleted database entry for '{safe_filename}' in '{subdirectory}'.")

    except sqlite3.Error as e:
        logger.error(f"Database error during file deletion: {e}")
        return jsonify({"error": "A database error occurred while trying to delete the file record."}), 500

    # --- Step 2: Delete from the filesystem ---
    if os.path.exists(file_path):
        # Security check: Final check to prevent deleting outside the allowed folder
        if not os.path.abspath(file_path).startswith(os.path.abspath(base_path)):
            abort(403)
        try:
            os.remove(file_path)
            logger.info(f"Admin '{session.get('username')}' deleted file from filesystem: {file_path}")
            message = f"File '{safe_filename}' deleted successfully from both filesystem and database."
            return jsonify({"message": message}), 200
        except OSError as e:
            logger.error(f"Failed to delete file from filesystem: {e}")
            # The DB record was deleted, but the file couldn't be. This is a partial failure.
            return jsonify({"error": f"File record deleted from database, but failed to delete from filesystem: {e}"}), 500
    
    # If the file didn't exist on the filesystem but was in the DB, it's still a success.
    return jsonify({"message": f"File record for '{safe_filename}' removed from database (file was not found on filesystem)."}), 200


# ==============================================================================
# 6. EXAM CENTER LOGIC (DATABASE-DRIVEN)
# ==============================================================================

def require_login(f):
    """Decorator to protect routes that require an admin to be logged in."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('logged_in'):
            return jsonify({"error": "Authentication required to perform this action."}), 401
        return f(*args, **kwargs)
    return decorated_function

@app.route('/Timer', methods=['POST'])
@require_login
def Timer_function():
    set_time = request.form.get('set_time')
    if not set_time:
        return jsonify({'success': False, 'message': 'Time value is required.'}), 400
    
    flask_session_id = session['session_id']
    with get_db_connection() as conn:
        conn.execute("UPDATE exam_sessions SET exam_time = ? WHERE session_id = ?", (set_time, flask_session_id))
        conn.commit()

    return jsonify({'success': True, 'message': 'Time has been set successfully.'}), 200

@app.route('/generate_exam_code', methods=['POST'])
@require_login # Only a logged-in admin can generate a code
def generate_exam_code():
    """
    Generates a unique exam code for the admin's current exam session
    and saves it to the database.
    """
    # Get the admin's session ID from the secure Flask session
    admin_flask_session_id = session.get('session_id')
    if not admin_flask_session_id:
        return jsonify({"error": "Admin session not found. Please log in again."}), 401

    try:
        with get_db_connection() as conn:
            # First, find the database ID for the admin's current session
            cursor = conn.execute("SELECT id FROM exam_sessions WHERE session_id = ?", (admin_flask_session_id,))
            exam_session_row = cursor.fetchone()

            if not exam_session_row:
                return jsonify({"error": "No active exam setup found for your session."}), 404

            exam_session_db_id = exam_session_row['id']

            # Generate a unique code
            new_code = _generate_unique_code(conn)
            
            # Update the specific exam session row with the new code
            conn.execute(
                "UPDATE exam_sessions SET exam_code = ? WHERE id = ?",
                (new_code, exam_session_db_id)
            )
            conn.commit()
            
            logger.info(f"Generated exam code '{new_code}' for session ID {exam_session_db_id} by admin '{session.get('username')}'")

            # Return the new code to the frontend
            return jsonify({
                "message": "Exam code generated successfully.",
                "exam_code": new_code
            }), 200

    except sqlite3.Error as e:
        logger.error(f"Database error during exam code generation: {e}")
        return jsonify({"error": "A database error occurred."}), 500
    except Exception as e:
        logger.error(f"An unexpected error occurred during exam code generation: {e}")
        return jsonify({"error": "An unexpected error occurred."}), 500

@app.route('/Subject', methods=['POST'])
@require_login
def set_subject():
    flask_session_id = session.get('session_id')
    admin_username = session.get('username')
    
    # --- 1. Basic Validation of Form Fields ---
    if 'subject' not in request.form or \
       'question-length' not in request.form or \
       'question-template' not in request.files or \
       'answer-template' not in request.files:
        return jsonify({'success': False, 'message': 'Missing required form fields or files.'}), 400

    # --- 2. Retrieve Data ---
    subject = request.form.get('subject')
    question_length = request.form.get('question-length')
    question_template = request.files['question-template']
    answer_template = request.files['answer-template']
    # The 'contains-images' value from JS will be 'true' or 'false' as a string
    contains_images = request.form.get('contains-images') == 'true'

    # --- 3. Server-Side Security and Logic Validation ---
    # This is the crucial backstop validation.
    if contains_images:
        # If the box is checked, the server MUST verify the question file is a PDF.
        if not question_template.filename.lower().endswith('.pdf'):
            logger.warning(f"Admin '{admin_username}' tried to upload a non-PDF file for a question with images.")
            return jsonify({
                'success': False,
                'message': 'Security Error: For questions with images, only PDF files are permitted.'
            }), 400
    
    # --- 4. Process and Save Files ---
    try:
        q_filename = secure_filename(question_template.filename)
        a_filename = secure_filename(answer_template.filename)

        # Save files to the upload folder
        question_template.save(os.path.join(app.config['UPLOAD_FOLDER'], q_filename))
        answer_template.save(os.path.join(app.config['UPLOAD_FOLDER'], a_filename))
        
        # --- 5. Update Database ---
        # Ensure a session record exists before updating.
        get_or_create_exam_session(flask_session_id, admin_username)
        
        with get_db_connection() as conn:
            conn.execute(
                """UPDATE exam_sessions SET 
                   subject_name = ?, question_length = ?, question_template_filename = ?, 
                   answer_template_filename = ?, contains_images = ?
                   WHERE session_id = ?""",
                (subject, question_length, q_filename, a_filename, 1 if contains_images else 0, flask_session_id)
            )
            conn.commit()

        logger.info(f"Admin '{admin_username}' successfully configured subject '{subject}'.")
        # The 'success' flag is for compatibility with your JS.
        return jsonify({'success': True, 'message': 'Subject has been set successfully.'}), 200

    except Exception as e:
        logger.error(f"Error processing subject configuration: {e}", exc_info=True)
        return jsonify({'success': False, 'message': 'An internal server error occurred.'}), 500
    
    
@app.route('/viewer', methods=['GET'])
@require_login # This ensures only a logged-in admin can access this data.
def viewer():
    """
    Securely retrieves all configured details for the current admin's exam session
    from the database.
    """
    # Get the unique session ID for the currently logged-in admin.
    flask_session_id = session.get('session_id')
    if not flask_session_id:
        return jsonify({"message": "No active session found. Please log in again."}), 404

    try:
        with get_db_connection() as conn:
            # Fetch the entire session row using the session_id
            exam = conn.execute(
                "SELECT * FROM exam_sessions WHERE session_id = ?",
                (flask_session_id,)
            ).fetchone()

        if not exam:
            return jsonify({"message": "No exam has been configured for this session yet."}), 404

        # Prepare a structured response for the frontend
        # This structure matches what the new `fetchAndShowExamDetails` function expects.
        response_data = {
            "exam_time": exam['exam_time'],
            "subject": {
                "subject": exam['subject_name'],
                "question_length": exam['question_length'],
                "question_template_filename": exam['question_template_filename'],
                "answer_template_filename": exam['answer_template_filename'],
                "contains_images": bool(exam['contains_images'])
            }
            # We can add more details here in the future if needed
        }

        # Filter out keys that have no value to keep the response clean
        if not response_data["subject"]["subject"]:
            response_data.pop("subject")
        if not response_data["exam_time"]:
            response_data.pop("exam_time")

        if not response_data:
             return jsonify({"message": "No exam details have been saved for this session."}), 200

        return jsonify(response_data), 200

    except sqlite3.Error as e:
        logger.error(f"Database error while fetching exam session for viewer: {e}")
        return jsonify({"error": "A database error occurred."}), 500

@app.route('/extractor', methods=['POST'])
@require_login
def extractor():
    """
    Extracts questions and answers from the templates configured for the current
    admin's session and stores the extracted data in the database.
    """
    flask_session_id = session.get('session_id')
    logger.info(f"Extractor called for session: {flask_session_id}")

    # --- 1. Retrieve Session Configuration from Database ---
    try:
        with get_db_connection() as conn:
            exam = conn.execute(
                "SELECT question_template_filename, answer_template_filename, contains_images FROM exam_sessions WHERE session_id = ?",
                (flask_session_id,)
            ).fetchone()
    except sqlite3.Error as e:
        logger.error(f"DB error fetching session for extractor: {e}")
        return jsonify({'error': 'Database error occurred.'}), 500

    if not exam or not exam['question_template_filename'] or not exam['answer_template_filename']:
        return jsonify({'error': 'Exam templates have not been configured for this session.'}), 400

    q_path = os.path.join(app.config['UPLOAD_FOLDER'], exam['question_template_filename'])
    a_path = os.path.join(app.config['UPLOAD_FOLDER'], exam['answer_template_filename'])
    contains_images = bool(exam['contains_images'])

    # --- 2. Process Files using the Corrected `extractdocx` Module ---
    try:
        # --- Question Processing ---
        # The new `extract_content` handles all the logic internally.
        question_content, question_images = extractdocx.extract_content(q_path, contains_images)
        
        # If the question file only contained images, the 'question_content' will be the list of images.
        # Otherwise, it's text. We store whatever is most relevant.
        extracted_questions_data = question_images if contains_images else question_content
        
        # --- Answer Processing ---
        # We always need plain text from the answer file.
        answer_text = extractdocx.extract_text_from_any_file(a_path)
        formatted_answers = extractdocx.format_extracted_answers(answer_text)

        if not formatted_answers:
             logger.warning(f"No answers could be formatted from file: {exam['answer_template_filename']}")
             # Optionally, you can decide to return an error here if no answers are found.
             # For now, we'll proceed but it's good to be aware of.

    except (NotImplementedError, ValueError, FileNotFoundError) as e:
        logger.error(f"File processing error for session {flask_session_id}: {e}")
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        logger.error(f"Unexpected error during extraction: {e}", exc_info=True)
        return jsonify({'error': 'An unexpected error occurred during file extraction.'}), 500

    # --- 3. Store Extracted Data in the Database ---
    try:
        with get_db_connection() as conn:
            conn.execute(
                "UPDATE exam_sessions SET extracted_questions_json = ?, extracted_answers_json = ? WHERE session_id = ?",
                (json.dumps(extracted_questions_data), json.dumps(formatted_answers), flask_session_id)
            )
            conn.commit()
    except sqlite3.Error as e:
        logger.error(f"DB error saving extracted data: {e}")
        return jsonify({'error': 'Database error occurred while saving results.'}), 500

    logger.info(f"Extraction successful for session {flask_session_id}.")

    # --- 4. Return a Consistent Response to the Frontend ---
    return jsonify({
        'message': 'Extraction successful',
        'question_content': question_content,
        'question_images': question_images,
        'answer_content': formatted_answers, # Return the structured answers
    }), 200
    
    
@app.route('/student', methods=['POST'])
def create_student_portfolio():
    """
    Handles student registration for a specific exam using an exam code.
    This is the scalable version. A student is NOT logged in, so we remove @require_login.
    """
    # Get data from the form submitted by the student
    exam_code = request.form.get('exam_code', '').strip().upper()
    
    if not exam_code:
        return jsonify({"error": "Exam Code is required."}), 400

    student_details = {
        'name': request.form.get('name'),
        'class': request.form.get('class'),
        # 'subject' is now determined by the exam code, so we can ignore it from the form
    }
    # We only need name and class from the student form now.
    if not all(student_details.values()):
        return jsonify({"error": "Both Name and Class are required."}), 400

    try:
        with get_db_connection() as conn:
            # --- KEY LOGIC: Find the exam session using the provided code ---
            cursor = conn.execute(
                "SELECT id FROM exam_sessions WHERE exam_code = ? AND extracted_questions_json IS NOT NULL",
                (exam_code,)
            )
            exam_session_row = cursor.fetchone()

            if not exam_session_row:
                return jsonify({"error": "Invalid or expired Exam Code, or the exam is not yet ready."}), 404
            
            # The specific database ID of the exam this student will take
            exam_session_db_id = exam_session_row['id']
            
            # Store this specific ID in the student's secure Flask session.
            # This links the student to this exam for subsequent requests.
            session['student_exam_session_id'] = exam_session_db_id

            # Update the specific exam session row with this student's details.
            # This is useful for the admin to see who took which exam.
            conn.execute(
                "UPDATE exam_sessions SET student_details_json = ? WHERE id = ?",
                (json.dumps(student_details), exam_session_db_id)
            )
            conn.commit()

        logger.info(f"Student '{student_details['name']}' started exam with code '{exam_code}' (Session ID: {exam_session_db_id})")
        
        # On success, the frontend will redirect to /examcenter
        return jsonify({"message": "Student portfolio created successfully. Redirecting to exam..."}), 200

    except sqlite3.Error as e:
        logger.error(f"Database error during student registration: {e}")
        return jsonify({"error": "A database error occurred."}), 500
    except Exception as e:
        logger.error(f"An unexpected error occurred during student registration: {e}")
        return jsonify({"error": "An unexpected server error occurred."}), 500

@app.route('/mark', methods=['POST'])
def mark():
    """
    Marks the student's submitted answers against the correct answers
    for their specific, code-linked exam session.
    """
    # Check if the student has an active exam session ID stored.
    if 'student_exam_session_id' not in session:
        return jsonify({"error": "No active exam session found. Please start the exam again."}), 403

    exam_session_db_id = session['student_exam_session_id']
    student_answers = request.json

    if not student_answers:
        return jsonify({'error': 'No answers were provided.'}), 400

    try:
        with get_db_connection() as conn:
            # Fetch the correct answers for this specific exam session ID
            exam = conn.execute(
                "SELECT extracted_answers_json FROM exam_sessions WHERE id = ?",
                (exam_session_db_id,)
            ).fetchone()

        if not exam or not exam['extracted_answers_json']:
            return jsonify({'error': 'Correct answers for this exam could not be found. Please contact the administrator.'}), 404
            
        correct_answers = json.loads(exam['extracted_answers_json'])
        
        score = 0
        for q_num, correct_ans in correct_answers.items():
            # Ensure comparison is case-insensitive and handles different types
            if student_answers.get(q_num, '').strip().lower() == str(correct_ans).strip().lower():
                score += 1

        # Save the student's score and answers to their specific exam record
        with get_db_connection() as conn:
            conn.execute(
                "UPDATE exam_sessions SET student_answers_json = ?, student_score = ? WHERE id = ?",
                (json.dumps(student_answers), score, exam_session_db_id)
            )
            conn.commit()
        
        logger.info(f"Exam session ID {exam_session_db_id} marked. Score: {score}")
        
        # Return the final score to the frontend
        return jsonify({'message': 'Scoring complete', 'score': score}), 200
        
    except Exception as e:
        logger.error(f"An error occurred during marking for session ID {exam_session_db_id}: {e}")
        return jsonify({"error": "An internal error occurred while marking the exam."}), 500
    
@app.route('/get_score', methods=['GET'])
def get_score():
    """
    Securely retrieves the final score and other relevant details for the
    student's completed exam session, including the exam code.
    """
    if 'student_exam_session_id' not in session:
        return jsonify({"error": "No completed exam session found for this user."}), 404

    exam_session_db_id = session['student_exam_session_id']

    try:
        with get_db_connection() as conn:
            # --- KEY CHANGE: Add 'exam_code' to the SELECT query ---
            exam = conn.execute(
                """SELECT student_score, question_length, subject_name, exam_code, 
                          student_details_json, student_answers_json, extracted_answers_json 
                   FROM exam_sessions WHERE id = ?""",
                (exam_session_db_id,)
            ).fetchone()

        if not exam:
            return jsonify({"error": "Could not find the results for your exam session."}), 404

        if exam['student_score'] is None:
            return jsonify({"error": "Your exam has not been marked yet. Please wait."}), 404

        response_data = {
            "student_score": exam['student_score'],
            "student_details": json.loads(exam['student_details_json'] or '{}'),
            "student_answers": json.loads(exam['student_answers_json'] or '{}'),
            "extracted_answers": json.loads(exam['extracted_answers_json'] or '{}'),
        }
        
        # Add the remaining necessary fields to the student_details sub-object
        # for frontend convenience and compatibility.
        response_data["student_details"]["question_length"] = exam['question_length']
        response_data["student_details"]["subject"] = exam['subject_name']
        
        # --- KEY CHANGE: Add the exam_code to the response ---
        response_data["student_details"]["exam_code"] = exam['exam_code']

        return jsonify(response_data), 200

    except Exception as e:
        logger.error(f"Error retrieving score for session ID {exam_session_db_id}: {e}")
        return jsonify({"error": "An internal error occurred while fetching your score."}), 500
    
@app.route('/examcenter')
@require_login
def examcenter():
    flask_session_id = session['session_id']
    with get_db_connection() as conn:
        exam = conn.execute("SELECT * FROM exam_sessions WHERE session_id = ?", (flask_session_id,)).fetchone()
    
    if not exam or not exam['student_details_json'] or not exam['extracted_questions_json']:
        return jsonify({'error': 'Exam data is incomplete for this session.'}), 400

    student_data = json.loads(exam['student_details_json'])
    extracted_questions = json.loads(exam['extracted_questions_json'])
    
    # Add other necessary details to student_data for the template
    student_data['exam_time'] = exam['exam_time']
    print(f"Exam Time: {student_data['exam_time']}")

    # Assuming exam['exam_time'] is an integer (e.g., 240)
    total_seconds = int(exam['exam_time']) # Ensure it's an integer
    
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    seconds = total_seconds % 60
    
    # Format as "HH:MM:SS" with leading zeros
    formatted_exam_time = f"{hours:02}:{minutes:02}:{seconds:02}"
    
    student_data['exam_time'] = formatted_exam_time # Update student_data with formatted string
    print(f"Exam Time (formatted): {student_data['exam_time']}")
    # --- END OF TIMER FIX ---

    student_data['question_length'] = exam['question_length']
    print(f"Question Length: {student_data['question_length']}")

    student_data['exam_subject'] = exam['subject_name']
    print(f"Exam Subject: {student_data['exam_subject']}")

    formatted_document = format_extracted_document_with_embedded_images(extracted_questions)
    
    return jsonify({
        'student_data': student_data,
        'formatted_document': formatted_document,
        'exam_time': formatted_exam_time # Send the formatted string to the frontend
    }), 200

# This function was in the original code, preserved for `/examcenter`
def format_extracted_document_with_embedded_images(extracted_content):
    html = '''
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Extracted Document</title>
        <style>
            body {
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                line-height: 1.6;
                color: #ffff;
                max-width: 100%;
                margin: 0 auto;
                padding: 15px;
                font-size: 16px;

            }
            h1, h2, h3 {
            color: #667eea;
            margin-bottom: 15px;
            line-height: 1.2;
        }

        h1 {
            font-size: 2.5em;
            border-bottom: 2px solid #e2e8f0;
            padding-bottom: 10px;
        }

        h2 {
            font-size: 2em;
            margin-top: 30px;
        }

        h3 {
            font-size: 1.5em;
            margin-top: 25px;
        }

           p {
            margin-bottom: 15px;
            text-align: justify;
        }
           .math {
            font-style: italic;
            color: #2980b9;
            background-color: #f1f8ff;
            padding: 2px 5px;
            border-radius: 4px;
        }
           .image-container {
            margin: 20px 0;
            text-align: center;
        }

        .image-container img {
            max-width: 100%;
            height: auto;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
        }

            ol {
                padding-left: 30px;
            }
            li {
                margin-bottom: 10px;
            }
        </style>
    </head>
    <body>
    '''

    def render_item(item):
        if isinstance(item, str):
            if item.startswith('data:image/'):
                return f'<div class="image-container"><img src="{item}" alt="Exam image"></div>\n'
            else:
                return f'<p>{item}</p>\n'
        elif isinstance(item, dict):
            text = item.get('text', '')
            formulas = item.get('formulas', [])
            rendered_text = f'<p>{text}</p>\n'
            rendered_formulas = ''.join([f'<p class="math">{formula}</p>\n' for formula in formulas])
            return rendered_text + rendered_formulas
        else:
            logger.warning(f"Unsupported item type: {type(item)}")
            return ''

    if isinstance(extracted_content, list):
        for item in extracted_content:
            html += render_item(item)
    elif isinstance(extracted_content, str):
        html += render_item(extracted_content)
    else:
        logger.error(f"Unsupported content type: {type(extracted_content)}")
        html += '<p>Error: Unable to render content.</p>'

    html += '''
    </body>
    </html>
    '''
    return html
def format_paragraph(paragraph, question_length):
    """
    Format a paragraph of text by converting any math expressions to HTML and returning formatted text.
    
    Args:
        paragraph (str): The text paragraph to format.
        question_number (int): The current question number for formatting.

    Returns:
        str: The formatted paragraph with math expressions styled.
    """
    # Format math characters
    paragraph = re.sub(r'\[MATH:\s*(.*?)\s*\]', r'<span class="math">\1</span>', paragraph)

    return paragraph
    
@app.route('/Resultbank', methods=['POST'])
@require_login
def result_bank():
    flask_session_id = session['session_id']
    with get_db_connection() as conn:
        exam = dict(conn.execute("SELECT * FROM exam_sessions WHERE session_id = ?", (flask_session_id,)).fetchone())

    if not all(k in exam and exam[k] is not None for k in ['student_details_json', 'student_answers_json', 'extracted_answers_json', 'student_score']):
        return jsonify({'error': 'Incomplete exam data for result generation.'}), 400

    student_details = json.loads(exam['student_details_json'])
    student_answers = json.loads(exam['student_answers_json'])
    correct_answers = json.loads(exam['extracted_answers_json'])

    filename = f"{student_details['name']}_{student_details['class']}_results.txt"
    filepath = os.path.join(RESULTS_FOLDER, filename)
    
    try:
        with open(filepath, 'w') as f:
            f.write(f"Name: {student_details.get('name', 'N/A')}\n")
            f.write(f"Class: {student_details.get('class', 'N/A')}\n")
            f.write(f"Subject: {exam.get('subject_name', 'N/A')}\n")
            f.write(f"Exam Number: {student_details.get('exam_code', 'N/A')}\n")
            f.write(f"Score: {exam.get('student_score')} out of {exam.get('question_length', 'N/A')}\n\n")
            f.write("Student Answers:\n" + json.dumps(student_answers, indent=2) + "\n\n")
            f.write("Correct Answers:\n" + json.dumps(correct_answers, indent=2) + "\n")
        
        return jsonify({'message': 'Results saved successfully.', 'filename': filename}), 200
    except Exception as e:
        logger.error(f"Failed to write result file: {e}")
        return jsonify({'error': 'Failed to save results.'}), 500

# ==============================================================================
# 7. SOCKET.IO EVENT HANDLERS 
# ==============================================================================

@socketio.on('connect')
def handle_connect():
    """
    Handles a new client connection.
    Crucially, it checks the session cookie at the time of connection
    to see if the user is already a logged-in admin.
    """
    sid = request.sid
    client_ip = request.remote_addr
    
    # --- KEY CHANGE: Check session on connect ---
    # The session cookie is sent with the connection handshake.
    is_admin = session.get('logged_in', False)
    role = 'admin' if is_admin else 'client'
    
    # If the user is an admin, use their username. Otherwise, generate a random name.
    name = session.get('username', f"Device-{secrets.token_hex(4)}") if is_admin else f"Device-{secrets.token_hex(4)}"

    connected_clients[sid] = {
        'sid': sid,
        'ip': client_ip,
        'role': role,
        'name': name
    }
    
    if is_admin:
        logger.info(f"Admin '{name}' connected via Socket.IO with SID: {sid}")
    else:
        logger.info(f"Client connected: {connected_clients[sid]}")

    # Send the updated list of connected devices to everyone
    emit('update_connected_devices', {'devices': list(connected_clients.values())}, broadcast=True)

@socketio.on('disconnect')
def handle_disconnect():
    sid = request.sid
    if sid in connected_clients:
        logger.info(f"Client disconnected: {connected_clients[sid]}")
        del connected_clients[sid]
        emit('update_connected_devices', {'devices': list(connected_clients.values())}, broadcast=True)

@socketio.on('authenticate_admin')
def authenticate_admin(data):
    """
    This event can now be simplified or even removed. We keep it for compatibility
    with your existing frontend, but the real authentication now happens on connect.
    This acts as a re-verification step.
    """
    sid = request.sid
    
    # We just re-check the role we already assigned on connect.
    if connected_clients.get(sid, {}).get('role') == 'admin':
        logger.info(f"Admin re-verified via 'authenticate_admin' event: {connected_clients[sid]}")
        emit('admin_authenticated', {'message': 'Admin authentication confirmed.'}, room=sid)
    else:
        logger.warning(f"Failed 'authenticate_admin' event for non-admin SID: {sid}")
        emit('admin_authentication_failed', {'error': 'Authentication failed or session expired.'}, room=sid)
        

@socketio.on('upload_file_to_admin')
def receive_file(data):
    """Receives a file from a client and forwards it to all connected admins."""
    filename = secure_filename(data.get('filename', ''))
    filedata = data.get('filedata', '')
    
    if not filename or not filedata:
        return # Ignore empty requests

    filepath = os.path.join(RESULTS_FOLDER, filename)
    try:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(filedata)
        logger.info(f"Received result file '{filename}' and saved to results folder.")
        
        # Find all admin SIDs and notify them
        admin_sids = [sid for sid, info in connected_clients.items() if info.get('role') == 'admin']
        if not admin_sids:
            logger.warning("Result file received, but no admin is connected to be notified.")
            return

        for admin_sid in admin_sids:
            emit('file_received', {
                'filename': filename,
                'message': f'File {filename} received successfully in {RESULTS_FOLDER}'
            }, room=admin_sid)
    except Exception as e:
        logger.error(f"Error handling 'upload_file_to_admin': {e}")
        emit('file_received', {'error': str(e)}, room=request.sid)

@socketio.on('get_initial_devices')
def handle_get_initial_devices():
    """
    Handles a client's request to get the current list of all connected devices.
    Sends the list only to the requesting client.
    """
    sid = request.sid
    logger.info(f"Client {sid} requested the initial device list.")
    # The 'devices' key matches what the frontend expects.
    emit('update_connected_devices', {'devices': list(connected_clients.values())}, room=sid)

# ==============================================================================
# 8. GENERIC VIEW ROUTES & ERROR HANDLERS
# ==============================================================================
# This section contains routes that just render HTML templates.
"""
Handles all view pages and rendering pages managed by Flask.
Most redirects are performed using JavaScript window.href() instead of Flask's return redirect.
This approach avoids page reload and keeps the user on the same page.
"""

@app.route('/Admin1')
def Admin1():
    return render_template('Admin1.html')

@app.route('/subject')
def subject():
    """Render the Subject.html page."""
    return render_template('Subject.html')


@app.route('/Admin2')
def Adminpage():
    """Render the Admin2body.html page."""
    timestamp = int(datetime.datetime.now().timestamp())
    return render_template('Admin2body.html', timestamp=timestamp)



@app.route('/dialogue1')
def dialogue1():
    return render_template('Dialouge1.html')

@app.route('/timepage')
def timepage():
    return render_template('Timer2.html')

@app.route('/classFolder')
def render_class_folder():
    """Render the classFolder.html template."""
    return render_template('classFolder.html')

@app.route('/welcome')
def welcome_screen():
    return render_template('welcome.html')

@app.route('/video')
def video_player():
    return render_template('video.html')

@app.route('/video404', methods=['GET'])
def video_page():
    return render_template('404.html')


@app.route('/examloader')
def examloader2():
    """Render the examloader.html page."""
    return render_template('examloader2.html')

@app.route('/connect')
def connect_scan():
    return render_template('connect.html')

@app.route('/dashboard')
def dashboard():
    return render_template('Autofile.html')


@app.route('/stlogin')
def stlogin():
    """Render the studentform.html page."""
    return render_template('studentform.html')


@app.route('/scoreboard')
def scoreboard():
    """Render the scoreboard.html page."""
    timestamp = int(datetime.datetime.now().timestamp())
    return render_template('Score.html', timestamp=timestamp)

@app.route('/pencilLoader')
def pencilLoader():
    """Render the pencilLoader page"""
    return render_template('pencil.html')


@app.route('/Result_list')
def list_results():
    files = os.listdir(RESULTS_FOLDER)
    return render_template('Resultstatic.html', files=files)


@app.route('/main_display')
def main_display():
    return render_template('examcenter2.html')

@app.errorhandler(Exception)
def handle_exception(e):
    # Log the error
    app.logger.error(f"Unhandled exception: {str(e)}")
    # Return JSON instead of HTML for errors
    return jsonify(error=str(e)), 500

@app.route('/result')
def result():
    return render_template('resultspage.html')


@app.route('/login')
def login():
    return render_template('login.html')

@app.route('/RRset')
def RRset():
    return render_template('RRset.html')

@app.route('/profile')
def profile():
    return render_template('profilecard.html')

@app.route('/resultPortal')
def resultPortal():
    return render_template('Admin1Results.html')

@app.errorhandler(404)
def page_not_found(e):
    """
    Advanced 404 error handler:
    - Renders a custom 404.html page
    - Logs the error with details for debugging
    - Returns JSON response for API requests
    """
    # Log the error
    logger.error(f"404 error occurred: {str(e)}")
    logger.info(f"Requested URL: {request.url}")
    logger.info(f"Remote IP: {request.remote_addr}")
    logger.info(f"User Agent: {request.user_agent}")

    # Check if the request wants a JSON response (e.g., for API calls)
    if request.accept_mimetypes.accept_json and \
       not request.accept_mimetypes.accept_html:
        return jsonify(error="Not found", message=str(e)), 404
    
    # For regular requests, render the 404.html template
    return render_template('404.html', error=str(e)), 404


@app.errorhandler(404)
def page_not_found(e):
    logger.warning(f"404 Not Found: {request.url}")
    if request.accept_mimetypes.accept_json and not request.accept_mimetypes.accept_html:
        return jsonify(error="Not Found", message=str(e)), 404
    return render_template('404.html', error=e), 404

@app.errorhandler(Exception)
def handle_exception(e):
    # Pass through HTTP exceptions
    if isinstance(e, HTTPException):
        return e
    # Handle non-HTTP exceptions
    logger.error(f"Unhandled Exception: {e}", exc_info=True)
    if request.accept_mimetypes.accept_json and not request.accept_mimetypes.accept_html:
        return jsonify(error="Internal Server Error", message=str(e)), 500
    return render_template('505.html', error=e), 500


import socket
from flask import jsonify

@app.route('/get_host_ip', methods=['GET'])
def get_host_ip():
    try:
        host_name = socket.gethostname()
        host_ip = socket.gethostbyname(host_name)
        return jsonify({
            "host_name": host_name,
            "host_ip": host_ip
        })
    except Exception as e:
        logger.error(f"Error getting host IP: {e}")
        return jsonify({"error": "Unable to get host IP"}), 500

# ==============================================================================
# 9. APPLICATION LAUNCHER (for PyQt GUI)
# ==============================================================================

def run_flask():
    """Starts the Flask-SocketIO server."""
    logger.info("Starting Flask-SocketIO server on http://0.0.0.0:5000")
    # use_reloader=False is important when running in a separate process
    socketio.run(app, host='0.0.0.0', port=5000, use_reloader=False, allow_unsafe_werkzeug=True)

def run_pyqt(flask_process):
    """Starts the PyQt5 GUI."""
    qt_app = QApplication(sys.argv)
    browser = FuturisticBrowser(flask_process)
    sys.exit(qt_app.exec())

def cleanup_process(proc):
    """Ensures a process is terminated on exit."""
    if proc and proc.is_alive():
        logger.info(f"Terminating process with PID: {proc.pid}")
        proc.terminate()
        proc.join(timeout=5)
        if proc.is_alive():
            proc.kill()

if __name__ == '__main__':
    freeze_support() # Necessary for Windows executable

    flask_process = Process(target=run_flask)
    flask_process.start()
    
    # Register cleanup to run when the main program exits
    atexit.register(cleanup_process, flask_process)

    # Handle Ctrl+C gracefully
    def signal_handler(sig, frame):
        logger.info("Ctrl+C received. Shutting down.")
        cleanup_process(flask_process)
        sys.exit(0)
    signal.signal(signal.SIGINT, signal_handler)

    try:
        # Run the PyQt app in the main process
        run_pyqt(flask_process)
    finally:
        # Final cleanup attempt
        cleanup_process(flask_process)
