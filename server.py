#import eventlet  # Ensure eventlet is imported
#eventlet.monkey_patch()
from flask import Flask, send_from_directory, render_template, request, session, flash, jsonify, Response
import os
import re
from fpdf import FPDF
import fitz  # PyMuPDF
import base64
import io
import threading
from io import BytesIO
from PIL import Image
import logging
import datetime
import time
import secrets
import socket
import tqdm
import pyparsing
import struct
import base64
import platform
import sys
from multiprocessing import Process
import jinja2
import socketio
import gevent
from gevent import *
import signal
import subprocess
import random
import chardet
import greenlet
import json
import keyboard
import jsonpickle
from PyPDF2 import PdfReader
from docx import Document
from docx.shared import Inches
from flask_socketio import SocketIO, emit, join_room, leave_room
from werkzeug.utils import secure_filename, safe_join
from flask import send_file, jsonify, abort
import werkzeug
import sqlite3
from pyQtwin import *
import atexit
from flask_cors import CORS
from flask import json
from engineio.async_drivers import gevent
#from pyngrok import ngrok
from multiprocessing import Queue
from werkzeug.exceptions import HTTPException
import extractdocx
from extractdocx import (
    extract_content,
    convert_doc_to_docx,
    convert_docx_to_pdf,
    convert_docx_to_txt,
    extract_content,
    extract_pdf_content,
    determine_image_format,
    extract_potential_formulas,
    pdf_to_txt,
    convert_pdf_to_images,
    convert_doc_to_docx,
    extract_docx_content
)
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

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger('connect_app')
BUFFER_SIZE = 1024 * 4  # 4KB

# Set the authtoken directly in the code
#ngrok.set_auth_token("1iwJoz6NHdgKU0ccOMs0jGsi23f_6GgozfQAgfXW2bMEXgbWd")



BASE_DIR = os.path.abspath(os.path.dirname(__file__))
MAIN_DIR = os.path.join(BASE_DIR, 'ExamTester')
UPLOAD_FOLDER = os.path.join(MAIN_DIR, 'Uploads')
RESULTS_FOLDER = os.path.join(MAIN_DIR, 'Results')
QUESTIONS_FOLDER = os.path.join(MAIN_DIR, 'Questions')
PASSWORD_FOLDER = os.path.join(MAIN_DIR, 'Passwords')

# Ensure directories exist
for folder in [UPLOAD_FOLDER, RESULTS_FOLDER, QUESTIONS_FOLDER]:
    os.makedirs(folder, exist_ok=True)

ALLOWED_EXTENSIONS = {'txt', 'pdf', 'doc', 'docx', 'jpeg', 'jpg', 'png', 'json'}

app = Flask(__name__, template_folder='templates')
app.secret_key = 'supersecretkey'  # Change to a secure key in production
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['RESULTS_FOLDER'] = RESULTS_FOLDER
app.config['QUESTIONS_FOLDER'] = QUESTIONS_FOLDER
app.config['TEMPLATES_AUTO_RELOAD'] = True
app.config['STATIC_FOLDER'] = 'static'
ADMIN_SID = None  # Store the session ID for the admin client
ADMIN_TOKEN = None  # Store dynamically generated token after successful login

# Database setup (using users.db)
def init_db():
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()

    # Create the 'files' table if it doesn't exist
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS files (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        filename TEXT NOT NULL,
        subdirectory TEXT NOT NULL,
        filetype TEXT NOT NULL,
        filedata TEXT  -- Store Base64-encoded file data as TEXT
    )
    ''')

    # Create the 'cors_origins' table if it doesn't exist
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS cors_origins (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        origin TEXT UNIQUE NOT NULL
    )
    ''')

    # Create the 'admins' table if it doesn't exist
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS admins (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL
    )
    ''')

    conn.commit()
    conn.close()

init_db()


#..... CORS configuration...

# Fetch allowed CORS origins from the 'cors_origins' table
def get_allowed_origins():
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute('SELECT origin FROM cors_origins')
    origins = [row[0] for row in cursor.fetchall()]
    conn.close()
    return origins

# Dynamic CORS configuration using origins from the database
def update_cors_config():
    allowed_origins = get_allowed_origins() or ['*']  # Default to '*' if no origins in DB
    CORS(app, 
         resources={r"/*": {"origins": allowed_origins}}, 
         methods=["GET", "HEAD", "POST", "PATCH", "DELETE", "OPTIONS"],
         allow_headers=["Content-Type", "Authorization"],
         supports_credentials=True)

update_cors_config()

@app.route('/admin/add_origin', methods=['POST'])
def add_origin():
    new_origin = request.json.get('origin')
    if not new_origin:
        return jsonify({"error": "Origin is required"}), 400
    
    try:
        conn = sqlite3.connect('users.db')
        cursor = conn.cursor()
        cursor.execute('INSERT INTO cors_origins (origin) VALUES (?)', (new_origin,))
        conn.commit()
        conn.close()
        update_cors_config()  # Update CORS after adding a new origin
        return jsonify({"message": "Origin added successfully"}), 201
    except sqlite3.IntegrityError:
        return jsonify({"error": "Origin already exists"}), 400

@app.route('/admin/delete_origin', methods=['DELETE'])
def delete_origin():
    origin_to_delete = request.json.get('origin')
    if not origin_to_delete:
        return jsonify({"error": "Origin is required"}), 400
    
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute('DELETE FROM cors_origins WHERE origin = ?', (origin_to_delete,))
    conn.commit()
    conn.close()
    update_cors_config()  # Update CORS after deleting the origin
    return jsonify({"message": "Origin deleted successfully"}), 200


# SocketIO configuration
socketio = SocketIO(app, 
                    async_mode='gevent',
                    async_handler='threading',
                    logger=True,
                    timeout=60, 
                    engineio_logger=True)

SUBDIRECTORIES = ["Class", "Results", "Questions", "Passwords", "Logger", "Uploads"]
MAIN_DIRECTORY = os.path.join(os.getcwd(), "ExamTester")
CLASS_SUBFOLDERS = ["Jss1", "Jss2", "Jss3", "SS1", "SS2", "SS3"]

# Additinal config
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['RESULTS_FOLDER'] = RESULTS_FOLDER
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 1
app.config['TEMPLATES_AUTO_RELOAD'] = True
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # Limit file size to 16MB for uploads
SEPARATOR = "<SEPARATOR>"

# Store ngrok URL globally so it persists between requests
#ngrok_url = None
#ngrok_process = None

# Global dictionary to store frontend entries
data_store = {}

#Dictionary to store hostip and connected devices

host_data = {}
scan_data = {'active_ips': {}, 'count': 0}  # Initialize with empty values

# Global variables to track admin and clients
connected_clients = {}  # {session_id: {'role': 'admin' or 'client'}}
ADMIN_SID = None


def allowed_file(filename):
    """Check if the uploaded file is allowed based on its extension."""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def find_file_in_directory(directory, filename):
    """
    Search for a file in the given directory (and subdirectories) using os.walk.
    Returns the full path of the file if found, otherwise None.
    """
    for root, dirs, files in os.walk(directory):
        if filename in files:
            return os.path.join(root, filename)
    return None

def get_file_list():
    upload_files = [(file, 'Uploads') for file in os.listdir(UPLOAD_FOLDER)]
    question_files = [(file, 'Questions') for file in os.listdir(QUESTIONS_FOLDER)]
    return upload_files + question_files

def search_file_in_database(filename, subdirectory):
    try:
        conn = sqlite3.connect('users.db')
        c = conn.cursor()
        
        c.execute('SELECT filedata FROM files WHERE filename = ? AND subdirectory = ?', (filename, subdirectory))
        result = c.fetchone()
        
        return result[0] if result else None
    
    except Exception as e:
        app.logger.error(f"Database error: {str(e)}")
        return None
    finally:
        conn.close()


@app.route('/')
def loader():
    return render_template('loader.html')


def validate_subdirectory(subdirectory):
    """
    Validate that the given subdirectory is one of the allowed subdirectories
    and that it exists under the main directory.
    """
    if subdirectory not in SUBDIRECTORIES:
        return False, f"Invalid subdirectory: {subdirectory}. Must be one of {SUBDIRECTORIES}."
    
    subdirectory_path = os.path.join(MAIN_DIRECTORY, subdirectory)
    
    if not os.path.exists(subdirectory_path):
        return False, f"Subdirectory does not exist: {subdirectory_path}."
    
    return True, subdirectory_path


#the dirgod that brings to birth the main directories
@app.route('/init', methods=['GET'])
def initialize_directories():
    """Initialize the directory structure and return the status messages."""
    messages = []
    
    # Create the main directory
    messages.append(create_directory(MAIN_DIRECTORY))
    
    # Create the subdirectories
    for subdirectory in SUBDIRECTORIES:
        path = os.path.join(MAIN_DIRECTORY, subdirectory)
        messages.append(create_directory(path))
    
    # Create the class subfolders
    class_directory = os.path.join(MAIN_DIRECTORY, "Class")
    for subfolder in CLASS_SUBFOLDERS:
        path = os.path.join(class_directory, subfolder)
        messages.append(create_directory(path))
    
    return jsonify(messages=messages)

def create_directory(path):
    """Helper function to create a directory if it doesn't exist."""
    if not os.path.exists(path):
        os.makedirs(path)
        return f"Created directory: {path}"
    else:
        return f"Directory already exists: {path}"
    
@app.route('/get_host_ip', methods=['GET'])
def get_host_data():
    try:
        logging.info('Fetching host data...')
        data = subprocess.check_output(['ipconfig']).decode('utf-8').split('\n')
        
        for line in data:
            if 'IPv4 Address' in line:
                host_data['host_ip'] = line.split(':')[-1].strip()
            elif 'Host Name' in line:
                host_data['host_name'] = line.split(':')[-1].strip()
        
        # Set default host_name if not found
        host_data.setdefault('host_name', 'Admin1')
        
        logging.info('Host data fetched successfully.')
        logging.info(f'Host IP: {host_data["host_ip"]}, Host Name: {host_data["host_name"]}')
        
        return jsonify(host_data)
    
    except Exception as e:
        logging.error(f'Error fetching host data: {str(e)}')
        return jsonify({'error': str(e)}), 500


@app.route('/get_connected_devices', methods=['GET'])
def get_connected_devices():
    """Return a list of all connected devices"""
    devices = []
    
    for sid, info in connected_clients.items():
        device = {
            'sid': sid,
            'name': info.get('name', 'Unknown'),
            'ip': info.get('ip', '0.0.0.0'),
            'role': info.get('role', 'client')
        }
        devices.append(device)
    return jsonify({'devices': devices})



# Admin1 Uploads File to the Server
@app.route('/upload', methods=['POST'])
def upload_file():
    logging.info("Received upload request")
    
    if 'file' not in request.files:
        logging.error("No file part in the request")
        return jsonify({"error": "No file part in the request"}), 400
    
    file = request.files['file']
    
    if file.filename == '':
        logging.error("No selected file")
        return jsonify({"error": "No selected file"}), 400

    if allowed_file(file.filename):
        filename = secure_filename(file.filename)
        subdirectory = request.form.get('subdirectory', '').strip()
        
        # Construct upload path
        upload_path = os.path.join(UPLOAD_FOLDER, subdirectory)
        
        try:
            # Create directory if it doesn't exist
            os.makedirs(upload_path, exist_ok=True)
        except Exception as e:
            logging.error(f"Failed to create directory {upload_path}: {str(e)}")
            return jsonify({"error": "Directory creation failed", "details": str(e)}), 500
        
        filepath = os.path.join(upload_path, filename)
        
        try:
            # Save the file
            file.save(filepath)
            logging.info(f"File saved at {filepath}")
            
            # Notify clients
            try:
                socketio.emit('file_uploaded', {'filename': filename, 'subdirectory': subdirectory})
                socketio.emit('file_recieved',{'filename': filename, 'subdirectory': subdirectory})
                logging.info(f"Notified clients of uploaded file: {filename}")
            except Exception as e:
                logging.error(f"Failed to notify clients: {str(e)}")

            return jsonify({"message": "File uploaded successfully"}), 200
        
        except Exception as e:
            logging.error(f"Error saving file: {str(e)}")
            return jsonify({"error": "Failed to save file", "details": str(e)}), 500
    else:
        logging.error(f"File type not allowed: {file.filename}")
        return jsonify({"error": "File type not allowed"}), 400


#....................Admin Result portal.................

# Function to validate token
def validate_admin_token(token):
    global ADMIN_TOKEN
    return token == ADMIN_TOKEN

# Function to generate a token
def generate_token():
    return secrets.token_hex(16)

# Function to update device information
def update_device_info():
    device_info = [
        {
            'sid': sid,
            'name': info.get('name', 'Unknown'),  # Handle missing 'name'
            'ip': info.get('ip', '0.0.0.0'),     # Handle missing 'ip'
            'role': info.get('role', 'client')   # Handle missing 'role'
        } for sid, info in connected_clients.items()
    ]
    socketio.emit('update_connected_devices', {'devices': device_info})

# Admin authentication event
@socketio.on('authenticate_admin')
def authenticate_admin(data):
    global ADMIN_SID
    token = data.get('token')
    
    # Validate token
    if token == ADMIN_TOKEN:
        ADMIN_SID = request.sid  # Update the global ADMIN_SID with the client's socket ID
        connected_clients[request.sid] = {'role': 'admin'}  # Update role to 'admin' in connected_clients
       
        # Emit response to the admin client
        socketio.emit('admin_authenticated', {
            'message': 'Admin authenticated successfully',
            'response': data
        }, room=ADMIN_SID)  # Send message back to the admin
        
        return {'message': 'Admin authenticated successfully'}  # Return response for confirmation
        
    else:
        socketio.emit('admin_authentication_failed', {
            'error': 'Invalid token. Authentication failed.'
        }, room=request.sid)
        return {'message': 'Invalid token. Authentication failed.'}


# File upload event
@socketio.on('upload_file_to_admin')
def receive_file(data):
    global ADMIN_SID
    print(f"Received 'upload_file_to_admin' event with data: {data}")

    try:
        if not ADMIN_SID:
            emit('file_received', {'error': 'Admin is not connected. Cannot process the file.'}, room=request.sid)
            return

        # Check if 'filename' exists in data
        filename = data.get('filename')
        filedata = data.get('filedata')

        if not filename:
            emit('file_received', {'error': 'Filename is missing'}, room=request.sid)
            return

        # Secure the filename
        filename = secure_filename(filename)

        # Check if the file type is allowed (implement allowed_file function)
        if allowed_file(filename):
            filepath = os.path.join(RESULTS_FOLDER, filename)

           # Write the file data to disk
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(filedata)

            # Emit both filename and message back to the client
            emit('file_received', {
                'filename': filename,  # Include the filename in the emitted data
                'message': f'File {filename} received successfully in {RESULTS_FOLDER}'
            }, room=ADMIN_SID)
            #Emit file upload track
            emit('upload_progress', {'filename': data['filename'], 'progress': data['progress']}, room=request.sid)

            print(f'File {filename} received and saved successfully in {RESULTS_FOLDER}')
        else:
            emit('file_received', {'error': 'File type not allowed'}, room=request.sid)
            print(f"File type for {filename} is not allowed")

    except Exception as e:
        print(f"Error receiving file: {str(e)}")
        emit('file_received', {'error': str(e)}, room=request.sid)
        
@socketio.on('get_file')
def handle_get_file(data):
    filename = data.get('filename')
    subdirectory = data.get('subdirectory')
    app.logger.info(f"Received request to get file: {filename} in subdirectory: {subdirectory}")
    
    try:
        
        secure_filename_str = secure_filename(filename)
        
        # Define paths
        questions_path = os.path.join(QUESTIONS_FOLDER, subdirectory) if subdirectory else QUESTIONS_FOLDER
        upload_path = os.path.join(UPLOAD_FOLDER, subdirectory) if subdirectory else UPLOAD_FOLDER
        
        
        # Search for file in both folders
        file_path = find_file_in_directory(questions_path, secure_filename_str) or find_file_in_directory(upload_path, secure_filename_str)
        
        if file_path:
            # Ensure the path is safe
            if os.path.abspath(file_path).startswith((os.path.abspath(QUESTIONS_FOLDER), os.path.abspath(UPLOAD_FOLDER))):
                emit('file_received', {
                    'filename': filename, 
                    'message': f'File {filename} received successfully, file upload success',
                    'status': 'success'
                }, broadcast=True)
                    
                return send_file(file_path, as_attachment=True, download_name=filename)
            else:
                app.logger.warning(f"Access denied for path: {file_path}")
                return jsonify({"error": "Access denied"}), 403
        else:
            # If the file is not found in the OS, search the database
            app.logger.info(f"File not found in OS, searching database...")
            db_file_path = search_file_in_database(filename, subdirectory)
            if db_file_path and os.path.exists(db_file_path):
                # Emit received message first
                emit('file_received', {
                    'filename': filename, 
                    'message': f'File {filename} received successfully, file upload success',
                    'status': 'success'
                }, broadcast=True)
                # Return the file content using the path stored in the database
                app.logger.info(f"Returning file from path stored in database: {db_file_path}")
                
                return send_file(db_file_path, as_attachment=True, download_name=filename)
            else:
                app.logger.warning(f"File not found in database or at stored path: {filename}")
                return jsonify({"error": "File not found"}), 404

    except Exception as e:
        app.logger.error(f"Error in get_file: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500


def find_file_in_directory(directory, filename):
    """
    Search for a file in the given directory (and subdirectories) using os.walk.
    Returns the full path of the file if found, otherwise None.
    """
    for root, dirs, files in os.walk(directory):
        if filename in files:
            return os.path.join(root, filename)
    return None

def search_file_in_database(filename, subdirectory):
    try:
        conn = sqlite3.connect('users.db')
        c = conn.cursor()
        
        c.execute('SELECT filedata FROM files WHERE filename = ? AND subdirectory = ?', (filename, subdirectory))
        result = c.fetchone()
        
        return result[0] if result else None
    
    except Exception as e:
        app.logger.error(f"Database error: {str(e)}")
        return None
    finally:
        conn.close()

def write_to_disk(file_data, filename, subdirectory):
    """
    Write file data to disk.
    """
    try:
        # Log the type and a preview of the file data (if it's not too large)
        app.logger.info(f"Preparing to write file: {filename} to {subdirectory}")
        app.logger.info(f"Type of file_data: {type(file_data)}")
        
        # If file_data is a string, log a preview (first 100 characters)
        if isinstance(file_data, str):
            app.logger.info(f"File data (string preview): {file_data[:100]}")
        elif isinstance(file_data, bytes):
            app.logger.info(f"File data (bytes length): {len(file_data)} bytes")
        else:
            app.logger.info("Unexpected file_data type received.")

        target_dir = os.path.join(QUESTIONS_FOLDER, subdirectory)
        os.makedirs(target_dir, exist_ok=True)

        file_path = os.path.join(target_dir, secure_filename(filename))
        
        # Ensure file_data is in bytes
        if isinstance(file_data, str):
            file_data = file_data.encode('utf-8')  # Convert string to bytes
        with open(file_path, 'wb') as f:
            f.write(file_data)
        app.logger.info(f"File written to disk at {file_path}")

    except Exception as e:
        app.logger.error(f"Error writing file to disk: {str(e)}")


@socketio.on('file_received')
def handle_file_received(data):
    """
    Broadcast file received event to all connected clients.
    """
    filename = data.get('filename')
    emit('file_received', {
        'filename': filename,
        'status': 'success',
        'message': f"File {filename} received success, file recieved successfully by the server"
    }, broadcast=True)
    return filename



@socketio.on('file_content')
def receive_file(file_data, filename, subdirectory):
    """
    Handle received file content.
    """
    print(f"Received 'file_content' event with data: {data}")
    
    try:
        filename = data.get('filename')
        filedata = data.get('filedata')

        if not filename:
            emit('file_received', {'error': 'Filename is missing'}, broadcast=True)
            return

        if filedata is None:
            emit('file_received', {'error': 'File data is missing'}, broadcast=True)
            return

        filename = secure_filename(filename)

        if allowed_file(filename):
            subdirectory = data.get('subdirectory', '')  # Get subdirectory if provided
            target_dir = os.path.join(QUESTIONS_FOLDER, subdirectory)
            os.makedirs(target_dir, exist_ok=True)
            filepath = os.path.join(target_dir, filename)
            with open(filepath, 'wb') as f:  # Use 'wb' mode for binary writing
                f.write(filedata.encode() if isinstance(filedata, str) else filedata)
                emit('file_received', {'filename': filename, 'message': f'File {filename} received successfully'}, broadcast=True)
        else:
            emit('file_received', {'error': 'File type not allowed'}, broadcast=True)

    except Exception as e:
        emit('file_received', {'error': str(e)}, broadcast=True)


# Event for handling upload progress
@socketio.on('upload_progress')
def handle_upload_progress(data):
    print(f"Received upload progress: {data['filename']} - {data['progress']}%")
    emit('upload_progress_ack', {'filename': data['filename'], 'progress': data['progress']}, room=request.sid)

# Single `handle_connect` function
@socketio.on('connect')
def handle_connect():
    device_name = f"Device-{random.randint(1000, 9999)}"
    client_ip = request.remote_addr

    # Store client details
    connected_clients[request.sid] = {
        'role': 'client',
        'name': device_name,
        'ip': client_ip
    }

    emit('connect_response', {'message': 'Connected to the server. Please authenticate if you are the admin.'}, room=request.sid)
    print(f'Client connected: {device_name} (IP: {client_ip}) with SID: {request.sid}')

    # Emit updated device info to all clients
    update_device_info()
    update_device_count()

# Handle client disconnect
@socketio.on('disconnect')
def handle_disconnect():
    global ADMIN_SID
    client_info = connected_clients.pop(request.sid, None)

    if client_info and client_info['role'] == 'admin':
        print('Admin disconnected')
        ADMIN_SID = None
    else:
        print(f'Client {request.sid} disconnected')
        update_device_info()
        update_device_count()

# Handle generic messages from clients
@socketio.on('message')
def handle_message(msg):
    print(f"Message from client {request.sid}: {msg}")
    send(f"Server received: {msg}")

# Function to update the device count
def update_device_count():
    device_count = len(connected_clients)
    socketio.emit('update_connected_devices', {'device_count': device_count}, room=request.sid)



def result_format(file_content):
    """
    Format the file content from "Name: ... Class: ... Subject: ... Type A Exam Number: ... Score: ... out of ... 
    Student Answers: 1A 2B ... Correct Answers: 1A 2B ..." 
    to "Name: ... Class: ... Subject: ... Type A Exam Number: ... Score: ... out of ... 
    Student Answers: 1A 2B ... Correct Answers: 1A 2B ..."
    """
    lines = file_content.splitlines()
    formatted_lines = []
    student_answers = {}
    correct_answers = {}

    for line in lines:
        if line.startswith("Student Answers:"):
            student_answers_line = line.replace("Student Answers:", "").strip()
            # Extract question numbers and answers (no "q" or colons in the new format)
            student_answers_list = re.findall(r'(\d+)([A-Z])', student_answers_line)
            for question, answer in student_answers_list:
                student_answers[int(question)] = answer
        elif line.startswith("Correct Answers:"):
            correct_answers_line = line.replace("Correct Answers:", "").strip()
            # Extract question numbers and answers (no "q" or colons in the new format)
            correct_answers_list = re.findall(r'(\d+)([A-Z])', correct_answers_line)
            for question, answer in correct_answers_list:
                correct_answers[int(question)] = answer
        else:
            formatted_lines.append(line)

    # Format Student Answers and Correct Answers in ascending order
    student_answers_formatted = " ".join(f"{question}{answer}" for question, answer in sorted(student_answers.items()))
    correct_answers_formatted = " ".join(f"{question}{answer}" for question, answer in sorted(correct_answers.items()))

    # Append formatted answers to the result
    formatted_lines.append(f"Student Answers: {student_answers_formatted}")
    formatted_lines.append(f"Correct Answers: {correct_answers_formatted}")

    return "\n".join(formatted_lines)


@app.route('/view_result', methods=['GET'])
def view_result():
    try:
        # Get the filename from the query parameters
        filename = request.args.get('filename')

        if not filename:
            return jsonify({'error': 'Filename not provided'}), 400

        # Secure the filename to prevent directory traversal attacks
        filename = secure_filename(filename)

        # Construct the full path to the file
        filepath = os.path.join(RESULTS_FOLDER, filename)

        # Check if the file exists
        if not os.path.exists(filepath):
            return jsonify({'error': 'File not found'}), 404

        # Read the file content
        with open(filepath, 'r', encoding='utf-8') as file:
            file_content = file.read()

        # Format the file content
        formatted_content = result_format(file_content)

        # Return the formatted file content as JSON
        return jsonify({'filename': filename, 'content': formatted_content}), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500
        
#.........End of Admin portal...........


#.....client downloads from server......(manually)

#.... Serve files from the upload folder directly
@app.route('/uploads/<path:filename>', methods=['GET'])
def download_file(filename):
    try:
        return send_from_directory(app.config['UPLOAD_FOLDER'], filename, as_attachment=True)
    except FileNotFoundError:
        return jsonify({"error": "File not found"}), 404
    

@app.route('/downloads')
def download_from_server():
    app.logger.info('Download requested from client')

    # Get the list of all files in UPLOAD_FOLDER, including those in hidden subdirectories
    upload_files = []
    for root, dirs, files in os.walk(app.config['UPLOAD_FOLDER']):
        for file in files:
            # Construct the relative path from UPLOAD_FOLDER to the file
            relative_path = os.path.relpath(os.path.join(root, file), app.config['UPLOAD_FOLDER'])
            upload_files.append(relative_path)  # Store the relative path for each file

    app.logger.info(f"Files in UPLOAD_FOLDER, including hidden subdirectories: {upload_files}")


    # Get the list of files in QUESTIONS_FOLDER, including subdirectories
    question_files = []
    for root, dirs, files in os.walk(app.config['QUESTIONS_FOLDER']):
        for file in files:
            relative_path = os.path.relpath(root, app.config['QUESTIONS_FOLDER'])
            question_files.append((os.path.join(relative_path, file), 'Questions'))
    app.logger.info(f"Files in QUESTIONS_FOLDER: {question_files}")

    # Prepare the list of files to pass to the template
    files = []

    # Add files from UPLOAD_FOLDER
    for file in upload_files:
        files.append((file, 'Uploads'))

    # Add files from QUESTIONS_FOLDER
    files.extend(question_files)

    # If no files found in both folders, render a message in your template
    if not files:
        return render_template('downloads.html', files=[], message='No files found in both folders.')

    # Render the downloads.html template with the list of files
    return render_template('downloads.html', files=files)

@app.route('/download/<folder>/<path:filename>', methods=['GET'])
def download_files(folder, filename):
    app.logger.info('Link clicked by client')
    if folder == 'Uploads':
        directory = app.config['UPLOAD_FOLDER']
    elif folder == 'Questions':
        directory = app.config['QUESTIONS_FOLDER']
    else:
        abort(404)  # Return a 404 error if the folder is not recognized
        app.logger.info('File not available')

    # Search for the file in the directory
    file_path = os.path.join(directory, filename)
    app.logger.info(f'Searching for file: {file_path}')
    if os.path.exists(file_path):
        app.logger.info('File found on disk')
        return send_file(file_path, as_attachment=True)

    # If not found in the directory, search in the database
    file_data = search_file_in_database(filename, folder)
    app.logger.info('Database search function called')
    if file_data:
        app.logger.info('File found in database')
    return send_file(file_path, as_attachment=True, download_name=filename)

    # If the file is not found in both the directory and the database, return a 404 error
    app.logger.warning(f"File not found: {filename}")
    abort(404)
    
"""This section validates the Admin and Authenciates him 
it initializes the database and takes the parameters from 
the front end at checks them against stored database password parameters
"""

#chexks password endpoint....General check...
@app.route('/check_password', methods=['POST'])
def check_password():
    """Check if the provided username and password are correct."""
    # Get the JSON data from the request
    data = request.get_json()
    
    # Validate JSON structure
    if 'username' not in data or 'password' not in data:
        return jsonify({"error": "Invalid request"}), 400
    
    print(f"Received username: {data['username']}")
    print(f"Received password: {data['password']}")
    
    username = data['username'].strip().lower()
    password = data['password']

    # Default usernames and passwords for 'admin1' and 'admin2'
    default_credentials = {
        'admin1': '@RoyalRangers',
        'admin2': '@1234ABCD'
        
    }

    # Check default credentials first
    if username in default_credentials and password == default_credentials[username]:
        print(f"Password is correct for default user '{username}'")
        return jsonify({"message": "Password is correct"}), 200
    
    # Now check the database for any other admin users
    try:
        conn = sqlite3.connect('users.db')  #  database name
        cursor = conn.cursor()

        # Query the database for the given username and password
        cursor.execute("SELECT * FROM admins WHERE username = ? AND password = ?", (username, password))
        admin = cursor.fetchone()

        if admin:
            print(f"Password is correct for user '{username}'")
            return jsonify({"message": "Password is correct"}), 200
        else:
            print(f"Password is incorrect for user '{username}'")
            return jsonify({"error": "Password is incorrect"}), 404

    except sqlite3.Error as e:
        print(f"Database error: {e}")
        return jsonify({"error": "Database error occurred."}), 500

    finally:
        conn.close()
        
# Result portal Admin checker......
@app.route('/portal_admin', methods=['POST'])
def portal_admin():
    """Check if the provided username and password are correct."""
    global ADMIN_TOKEN  # To store the dynamically generated token

    # Get the JSON data from the request
    data = request.get_json()
    
    # Validate JSON structure
    if 'username' not in data or 'password' not in data:
        return jsonify({"error": "Invalid request"}), 400
    
    print(f"Received username: {data['username']}")
    print(f"Received password: {data['password']}")
    
    username = data['username'].strip().lower()
    password = data['password']

    # Default usernames and passwords for 'admin1' and 'admin2'
    default_credentials = {
        'admin1': '@RoyalRangers',
        'admin2': '@1234ABCD'
    }

    # Check default credentials first
    if username in default_credentials and password == default_credentials[username]:
        print(f"Password is correct for default user '{username}'")
        ADMIN_TOKEN = generate_token()  # Generate token
        return jsonify({"message": "Password is correct", "token": ADMIN_TOKEN}), 200
    
    # Now check the database for any other admin users
    try:
        conn = sqlite3.connect('users.db')  # Database name
        cursor = conn.cursor()

        # Query the database for the given username and password
        cursor.execute("SELECT * FROM admins WHERE username = ? AND password = ?", (username, password))
        admin = cursor.fetchone()

        if admin:
            print(f"Password is correct for user '{username}'")
            ADMIN_TOKEN = generate_token()  # Generate token
            return jsonify({"message": "Password is correct", "token": ADMIN_TOKEN}), 200
        else:
            print(f"Password is incorrect for user '{username}'")
            return jsonify({"error": "Password is incorrect"}), 404

    except sqlite3.Error as e:
        print(f"Database error: {e}")
        return jsonify({"error": "Database error occurred."}), 500

    finally:
        conn.close()
        
  #.....create new Admin....  
@app.route('/new_admin', methods=['POST'])
def new_admin():
    """Register a new admin with a username and a password."""
    data = request.get_json()

    # Validate input data
    if 'username' not in data or 'password' not in data:
        return jsonify({"error": "Invalid request. Username and password are required."}), 400

    username = data['username'].strip().lower()
    password = data['password']

    # Ensure password starts with '@'
    if not password.startswith('@'):
        return jsonify({"error": "Password must start with '@'."}), 400

    try:
        conn = sqlite3.connect('users.db')  # Your database name
        cursor = conn.cursor()

        # Check if the username already exists
        cursor.execute("SELECT * FROM admins WHERE username = ?", (username,))
        existing_admin = cursor.fetchone()

        if existing_admin:
            return jsonify({"error": "Username already exists."}), 400

        # Insert the new admin
        cursor.execute("INSERT INTO admins (username, password) VALUES (?, ?)", (username, password))
        conn.commit()

        return jsonify({"message": "New admin registered successfully."}), 201

    except sqlite3.Error as e:
        print(f"Database error: {e}")
        return jsonify({"error": "A database error occurred."}), 500

    finally:
        conn.close()
#.....Ends password validation and Authenciation

"""This section Exam centre controls the exam process from setting of the time the subject
the marking and recording and Result process Everything to complete the full exam"""

#Timer funnction
@app.route('/Timer', methods=['GET', 'POST'])
def Timer_function():
    """Handle setting the timer via a POST request and render Timer2.html."""
    if request.method == 'POST':
        set_time = request.form.get('set_time')
        if set_time:
            data_store['exam_time'] = set_time
            session['exam_time'] = set_time
            flash('Time has been set successfully!', 'success')
            return jsonify({'success': True, 'message': 'Time has been set successfully.'}), 200
    return render_template('Timer2.html')


@app.route('/Subject', methods=['POST'])
def set_subject():
    logger.info('subject constructor called')
    """Handle setting the subject and uploading associated files via a POST request."""
    subject = request.form.get('subject')
    question_length = request.form.get('question-length')
    question_template = request.files.get('question-template')
    answer_template = request.files.get('answer-template')
    contains_images = request.form.get('contains-images', 'false') == 'true'  # Frontend checkbox value
    logger.info("Templates recieved ")

    if not subject or not question_length:
        return jsonify({'success': False, 'message': 'Subject and number of questions are required.'}), 400

    subject_details = {
        'subject': subject,
        'question_length': question_length,
        'question_template_filename': None,
        'answer_template_filename': None,
        'contains_images': contains_images  # Store the contains_images flag
    }
    logger.info('subject dictionary constructed')

    for file, key in [(question_template, 'question_template_filename'), (answer_template, 'answer_template_filename')]:
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)

            if key == 'question_template_filename' and contains_images:
                # Rename file to include marker "image_pdf" if the checkbox is selected
                filename = f'image_pdf_{filename}'

            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            subject_details[key] = filename
        else:
            return jsonify({'success': False, 'message': f'Invalid or missing {key.replace("_filename", "")} file.'}), 400

    # Save details in data_store
    data_store['subject'] = subject_details
    logger.info('subject dictionary saved to global dictionary')
    return jsonify({'success': True, 'message': 'Subject has been set successfully.'}), 200



@app.route('/viewer', methods=['GET'])
def viewer():
    """View all details stored in the global dictionary and return as JSON."""
    if not data_store:
        return jsonify({'message': 'No exam details have been saved.'}), 200
    return jsonify(data_store), 200


@app.route('/retriever', methods=['GET'])
def retriever():
    """Retrieve student's score, extracted questions, answers, and other relevant details from data_store."""
    
    # Extract necessary information from data_store
    student_score = data_store.get('student_score')  # Score calculated after submission
    extracted_questions = data_store.get('extracted_questions', [])  # Questions extracted earlier
    extracted_answers = data_store.get('extracted_answers', {})  # Correct answers extracted earlier
    student_data = data_store.get('students', {})  # Student-related data
    student_answers = data_store.get('student_answers', {})  # Student answers, default to empty dict

    # Debugging: Print extracted information
    print("DEBUG: Student Score:", student_score)
    print("DEBUG: Extracted Questions:", extracted_questions)
    print("DEBUG: Extracted Answers:", extracted_answers)
    print("DEBUG: Student Details:", student_data)
    print("DEBUG: Student Answers:", student_answers)

    # Prepare the data to send to the frontend
    result = {
        'student_score': student_score,
        'extracted_questions': extracted_questions,
        'extracted_answers': extracted_answers,
        'student_details': student_data,
        'student_answers': student_answers
    }

    # Return the data as JSON response
    return jsonify(result), 200


@app.route('/extractor', methods=['POST'])
def extractor():
    global data_store
    logger.info("Extractor called successfully")

    # Retrieve templates from the global data_store
    question_template = data_store.get('subject', {}).get('question_template_filename')
    answer_template = data_store.get('subject', {}).get('answer_template_filename')
    logger.info('Templates retrieved successfully')

    # Ensure both templates are present
    if not question_template or not answer_template:
        return jsonify({'error': 'Question or answer template not found in the dictionary.'}), 400

    # Paths to the question and answer files
    question_path = os.path.join(app.config['UPLOAD_FOLDER'], question_template)
    answer_path = os.path.join(app.config['UPLOAD_FOLDER'], answer_template)

    try:
        ### PROCESSING QUESTION TEMPLATE ###
        contains_images = 'image_pdf' in question_template.lower()

        # Convert question to PDF if needed
        if question_template.lower().endswith(('docx', 'doc', 'txt')):
            question_pdf_path = convert_docx_to_pdf(question_path)
            logger.info(f"convert_docx_to_pdf called for {question_path}")
        else:
            question_pdf_path = question_path

        # Extract content from the question file (may contain images)
        question_content, question_images = extract_content(question_pdf_path, contains_images)

        # Store extracted question content or images in the global data_store
        if question_images:
            logger.info("Saving extracted images to data_store['extracted_questions']")
            data_store['extracted_questions'] = question_images  # Store images if present
        else:
            data_store['extracted_questions'] = question_content  # Store text if no images

        ### PROCESSING ANSWER TEMPLATE ###
        # Answer template can never have images, so skip image extraction
        answer_extension = answer_template.rsplit('.', 1)[-1].lower()

        if answer_extension == 'pdf':
            # Convert the PDF to text using extract_pdf_content
            logger.info(f"Extracting text from answer PDF: {answer_path}")
            answer_content, _ = pdf_to_txt(answer_path)  # No images for answers
        elif answer_extension in {'doc', 'docx'}:
            # Convert DOC/DOCX to plain text using appropriate function
            if answer_extension == 'doc':
                # Convert .doc to .docx first, if necessary
                answer_docx_path = convert_doc_to_docx(answer_path)
                if not answer_docx_path:
                    raise ValueError(f"Failed to convert {answer_path} to .docx")
                answer_content = extract_docx_content(answer_docx_path)
            else:
                # For .docx files, extract text directly
                answer_content = extract_content(answer_path)
        elif answer_extension == 'txt':
            # For .txt files, read the content directly
            answer_content = extract_content(answer_path)
        else:
            raise ValueError(f"Unsupported file format for answer template: {answer_extension}")

        # Format the extracted answer content
        formatted_answers = format_extracted_answers(answer_content)

        # Store the formatted answers in the global data_store
        data_store['extracted_answers'] = formatted_answers
        data_store['question_images'] = question_images

        logger.info("Extraction successful")

        return jsonify({
            'message': 'Extraction successful',
            'question_content': question_content,
            'question_images': question_images,
            'answer_content': formatted_answers,
            'answer_images': []  # No images for answers
        }), 200

    except Exception as e:
        logger.error(f"Error during extraction: {str(e)}")
        return jsonify({'error': f'Error during extraction: {str(e)}'}), 500

def is_base64(s):
    """Check if a string is base64 encoded."""
    pattern = r'^data:.*;base64,'
    if re.match(pattern, s):
        return True
    try:
        # Try to decode the string (minus any potential data URI prefix)
        base64.b64decode(s.split(',')[-1])
        return True
    except:
        return False

def format_extracted_answers(answer_content):
    """
    Format extracted answers from string content to a dictionary format.
    """
    # Check if answer_content is a tuple
    if isinstance(answer_content, tuple):
        # Assuming the first element is the relevant content
        answer_content = answer_content[0]  # You can adjust this based on your needs

    if not isinstance(answer_content, str):
        if isinstance(answer_content, list):
            # If it's a list of dictionaries with 'text' key
            answer_content = '\n'.join([item.get('text', '') for item in answer_content])
        else:
            raise ValueError(f"Unexpected answer content type: {type(answer_content)}")

    formatted_answers = {}

    # Check if content is base64 encoded
    if is_base64(answer_content):
        # Extract the base64 encoded part if it's a data URI
        base64_content = answer_content.split(',')[-1]
        # Decode base64 content
        try:
            decoded_content = base64.b64decode(base64_content).decode('utf-8')
        except UnicodeDecodeError:
            # If UTF-8 decoding fails, try with ISO-8859-1
            decoded_content = base64.b64decode(base64_content).decode('iso-8859-1')
    else:
        # If not base64, use the content as is
        decoded_content = answer_content

    # Remove BOM character if present
    if decoded_content.startswith('\ufeff'):
        decoded_content = decoded_content[1:]

    for line in decoded_content.splitlines():
        line = line.strip()
        if line:  # Ensure line is not empty
            # Try to match the expected format (number followed by letter)
            match = re.match(r'(\d+)([A-Za-z])', line)
            if match:
                question_number = 'q' + match.group(1)  # 'q1', 'q2', etc.
                answer = match.group(2).upper()  # 'A', 'B', etc.
                formatted_answers[question_number] = answer

    return formatted_answers

#Endpoint that deals with student info and prepares the exam
@app.route('/student', methods=['POST', 'GET']) 
def create_student_portfolio():
    if request.method == 'POST':
        """
        Endpoint to receive student details from the frontend, combine with extracted exam details,
        and create a new student portfolio.

        Returns:
            JSON response with a success message or error.
        """
        try:
            # Retrieve student details from form data
            student_name = request.form.get('name')
            student_class = request.form.get('class')
            subject = request.form.get('subject')
            exam_number = request.form.get('exam_number')

            # Ensure required fields are provided
            if not all([student_name, student_class, subject, exam_number]):
                return jsonify({'error': 'All student details are required.'}), 400

            # Create a temporary list to store student details
            student_details = [student_name, student_class, subject, exam_number]

            # Retrieve additional information from the global dictionary
            extracted_questions = data_store.get('extracted_questions')
            exam_subject = data_store.get('subject', {}).get('subject')
            question_length = data_store.get('subject', {}).get('question_length')
            exam_time = data_store.get('exam_time')

            # Append additional information to the student details list
            student_details.extend([extracted_questions, exam_subject, question_length, exam_time])

            # Create a new dictionary named 'students'
            students = {
                'name': student_name,
                'class': student_class,
                'subject': subject,
                'exam_number': exam_number,
                'extracted_questions': extracted_questions,
                'exam_subject': exam_subject,
                'question_length': question_length,
                'exam_time': exam_time
            }

            # Store the student dictionary in the global data_store
            data_store['students'] = students

            # Log success message
            app.logger.info('Student portfolio created: %s', students)

            return jsonify({'message': 'Student portfolio created successfully.'}), 200
        except Exception as e:
            return jsonify({'error': f'Failed to create student portfolio: {str(e)}'}), 500
    elif request.method == 'GET':  # Corrected syntax
        if 'students' in data_store:
            return jsonify(data_store['students']), 200
        else:
            return jsonify({'error': 'cannot retrieve student details'}), 404  # Corrected error message
        
        
@app.route('/mark', methods=['POST'])
def mark():
    global data_store
    """Compare student answers with extracted answers and calculate the score."""
    
    # Debug: Print the raw data received from the front-end
    print("Received data from student:", request.data)

    # Parse the JSON data sent by the JavaScript
    student_answers = request.json  # Expecting a dictionary format {'q1': 'A', 'q2': 'B', ...}
    extracted_answers = data_store.get('extracted_answers', {})  # Add default empty dict to avoid NoneType

    # Debug: Print the extracted answers from the backend
    print("Extracted correct answers:", extracted_answers)

    if not extracted_answers:
        return jsonify({'error': 'Extracted answers not found. Please run the extractor first.'}), 400

    if not student_answers:
        return jsonify({'error': 'Student answers not provided.'}), 400

    # Store student answers in the global dictionary
    data_store['student_answers'] = student_answers

    # Debug: Print stored student answers
    print("Stored student answers in data_store:", data_store['student_answers'])

    score = 0

    # Assume extracted_answers is a dictionary like {'q1': 'A', 'q2': 'B', ...}
    # Debug: Print the type of extracted answers
    print("Type of extracted answers:", type(extracted_answers))

    if isinstance(extracted_answers, dict):
        # Iterate through the answers to calculate the score
        for question, correct_answer in extracted_answers.items():
            student_answer = student_answers.get(question)
            
            # Debug: Print each comparison between student's answer and correct answer
            print(f"Comparing {question}: student's answer = {student_answer}, correct answer = {correct_answer}")

            if student_answer and student_answer.strip().lower() == correct_answer.strip().lower():
                score += 1
    else:
        return jsonify({'error': 'Invalid format for extracted answers.'}), 400

    # Debug: Print the final score
    print("Calculated score:", score)

    # Store the score in the global dictionary
    data_store['student_score'] = score
    
    # Retrieve or initialize student details
    student_details = data_store.get('students', {})
    if student_details:
        # Update student details with the score
        student_details['score'] = score
        student_details['question_length'] = len(extracted_answers)  # Add total question length

        # Debug: Print updated student details
        print("Updated student details with score and question length:", student_details)

        # Store back updated student details
        data_store['students'] = student_details
    else:
        # Debug: Print that student details were not found
        print("Student details not found in data_store.")

    return jsonify({'message': 'Scoring complete', 'score': score}), 200


@app.route('/examrecord', methods=['GET'])
def examrecord():
    """Organize and return the exam record."""
    exam_record = {
        'student_name': data_store.get('student_name', 'Unknown Student'),
        'student_class': data_store.get('student_class', 'Unknown Class'),
        'subject': data_store.get('subject', {}).get('subject', 'Unknown Subject'),
        'extracted_answers': data_store.get('extracted_answers', 'No Answers'),
        'student_answers': data_store.get('student_answers', 'No Answers'),
        'score': data_store.get('student_score', 0)
    }
    return jsonify({'exam_record': exam_record}), 200


@app.route('/reset', methods=['POST'])
def reset():
    """Remove a specific value from the global dictionary and session."""
    key_to_remove = request.form.get('key')
    if key_to_remove:
        data_store.pop(key_to_remove, None)
        session.pop(key_to_remove, None)
        return jsonify({'success': True, 'message': f'{key_to_remove} has been removed successfully.'}), 200

    return jsonify({'success': False, 'message': 'No key provided to remove.'}), 400



@app.route('/examcenter')
def examcenter():
    """Extract and format content and images from the question and answer templates."""
    logger.info("Extractor called successfully")
    logger.info("Data store is called")

    student_data = data_store.get('students')

    # Check if student_data is None
    if not student_data:
        logger.error("No student data found.")
        return jsonify({'error': 'No student data found.'}), 400

    # Check if 'extracted_questions' exists in student_data
    extracted_questions = student_data.get('extracted_questions', None)
    if not extracted_questions:
        logger.error("'extracted_questions' not found in student data.")
        return jsonify({'error': 'No extracted questions found.'}), 400

    try:
        # Format the document and images
        formatted_document = format_extracted_document_with_embedded_images(extracted_questions)

        return jsonify({
            'student_data': student_data,
            'formatted_document': formatted_document,
            'exam_time': student_data.get('exam_time')
        }), 200

    except Exception as e:
        logger.error(f"Unhandled exception during formatting: {str(e)}")
        return jsonify({'error': f'Error during formatting: {str(e)}'}), 500

def format_extracted_document_with_embedded_images(extracted_content):
    html = '''
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Extracted Document</title>
        <style>
        }
            body {
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                line-height: 1.6;
                color: #333;
                max-width: 100%;
                margin: 0 auto;
                padding: 20px;
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


def format_paragraph(paragraph, question_number):
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
def result_bank():
    """Endpoint to save student results to a .txt file in the RESULTS_FOLDER."""

    # Retrieve data from request
    student_details = request.json.get('student_details')
    student_answers = request.json.get('student_answers')
    extracted_answers = request.json.get('extracted_answers')
    
    # Check for missing keys or None values
    if not student_details or not student_answers or not extracted_answers:
        return jsonify({'error': 'Incomplete data provided.'}), 400
    
    # Ensure the 'score' key exists
    if 'score' not in student_details:
        return jsonify({'error': 'Score not found in student details.'}), 400
    
    # Construct file content
    file_content = []
    file_content.append(f"Name: {student_details.get('name', 'N/A')}")
    file_content.append(f"Class: {student_details.get('class', 'N/A')}")
    file_content.append(f"Subject: {student_details.get('subject', 'N/A')}")
    file_content.append(f"Exam Number: {student_details.get('exam_number', 'N/A')}")
    file_content.append(f"Score: {student_details.get('score')} out of {student_details.get('question_length', 'N/A')}")
    
    
    file_content.append("\nStudent Answers:")
    for question, answer in sorted(student_answers.items(), key=lambda x: int(x[0][1:])):  # Sort by question number
        file_content.append(f"{question}: {answer}")
    
    file_content.append("\nCorrect Answers:")
    for question, answer in sorted(extracted_answers.items(), key=lambda x: int(x[0][1:])):  # Sort by question number
        file_content.append(f"{question}: {answer}")

    # Generate the filename using student details (e.g., exam number or name)
    filename = f"{student_details['name']}_{student_details['class']}_results.txt"
    filepath = os.path.join(RESULTS_FOLDER, filename)

    # Write to file
    try:
        with open(filepath, 'w') as file:
            file.write("\n".join(file_content))
        
        return jsonify({'message': 'Results uploaded successfully.', 'filename': filename}), 200

    except Exception as e:
        return jsonify({'error': f'Failed to save results: {str(e)}'}), 500
    
 #.......END OF EXAMCENTER SECTION.........

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

@app.route('/Autofile')
def Autofile():
    """Render the Autofile.html page."""
    return render_template('Autofile.html')


@app.route('/dialogue1')
def dialogue1():
    return render_template('Dialouge1.html')

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

@app.route('/home')
def home():
    return render_template('Home.html')


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

@app.errorhandler(Exception)
def handle_exception(e):
    """
    General exception handler:
    - Logs unexpected errors
    - Returns a 500 Internal Server Error for unhandled exceptions
    """
    # Log the error
    logger.error(f"Unhandled exception: {str(e)}", exc_info=True)

    # Return JSON instead of HTML for API requests
    if request.accept_mimetypes.accept_json and \
       not request.accept_mimetypes.accept_html:
        return jsonify(error="Internal Server Error", message=str(e)), 500
    
    # For regular requests, you can create a custom 500.html template
    return render_template('500.html', error=str(e)), 500

#......End of flask view section....

"""This section handles file download and upload to server 
for the client computer"""

# List Available Files for Download
# List files with download URLs
@app.route('/list_files', methods=['GET'])
def list_files():
    try:
        files = []
        for root, _, filenames in os.walk(app.config['UPLOAD_FOLDER']):
            for filename in filenames:
                file_path = os.path.join(root, filename)
                relative_path = os.path.relpath(file_path, app.config['UPLOAD_FOLDER'])
                download_url = f"/uploads/{relative_path.replace(os.path.sep, '/')}"  # Create a URL-friendly path
                files.append({
                    "filename": filename,
                    "download_url": download_url
                })
        
        return jsonify({"files": files}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# Upload and send result to a remote server
@app.route('/resultuploader', methods=['POST'])
def resultuploader():
    logger.info("Received file upload request")

    if 'file' not in request.files:
        logger.error("No file part in the request")
        return jsonify({'error': 'No file part'}), 400
    
    file = request.files['file']
    if file.filename == '':
        logger.error("No selected file")
        return jsonify({'error': 'No selected file'}), 400

    ip = request.form.get('ip')
    if not ip:
        logger.error("No IP address provided")
        return jsonify({'error': 'No IP address provided'}), 400

    filename = secure_filename(file.filename)

    # Save the file temporarily
    temp_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    file.save(temp_path)
    filesize = os.path.getsize(temp_path)

    logger.info(f"File received: {filename}, IP: {ip}, Size: {filesize} bytes")

    def generate():
        try:
            s = socket.socket()
            ip_address, port = ip.split(":")
            port = int(port)
            s.connect((ip_address, port))
            s.send(f"{filename}{SEPARATOR}{filesize}".encode())

            with open(temp_path, 'rb') as f:
                progress = tqdm.tqdm(range(filesize), f"Sending {filename}", unit="B", unit_scale=True, unit_divisor=1024)
                while True:
                    bytes_read = f.read(BUFFER_SIZE)
                    if not bytes_read:
                        break
                    s.sendall(bytes_read)
                    progress.update(len(bytes_read))

            s.close()
            os.remove(temp_path)  # Clean up the temporary file
            yield b'DONE'
        except Exception as e:
            logger.error(f"Error during file upload: {str(e)}")
            yield b'ERROR'
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)  # Ensure cleanup in case of errors

    return Response(generate(), mimetype='application/octet-stream')

#..............End of Result uploader section............

"""This is the CRUD SECTION
this section handles The create, read , update, delete functions of the app"""


@app.route('/create', methods=['POST'])
def create_file():
    logging.info('Received POST request to create file')
    print('new file request')
    
    # Retrieve form data
    subdirectory = request.form.get('subdirectory')
    filename = request.form.get('filename')
    file = request.files.get('file')

    if not file:
        return jsonify({"error": "No file provided"}), 400

    file_type = file.filename.split('.')[-1].lower()  # Extract file extension

    logging.info(f'Received request data: subdirectory={subdirectory}, filename={file.filename}, file_type={file_type}')

    # Validate the subdirectory
    is_valid, response = validate_subdirectory(subdirectory)
    if not is_valid:
        logging.error(f'Invalid subdirectory: {response}')
        return jsonify({"error": response}), 400

    # Create subdirectory if it does not exist
    if not os.path.exists(response):
        os.makedirs(response)

    # Define the file path
    file_path = os.path.join(response, file.filename)

    if os.path.exists(file_path):
        logging.error(f'File already exists: {file_path}')
        return jsonify({"error": f"File '{file.filename}' already exists in '{subdirectory}'."}), 400

    try:
        # Save the file directly to the file system
        file.save(file_path)
        logging.info(f'File saved: {file_path}')

        logging.info('Connecting to SQLite database')
        conn = sqlite3.connect('users.db')
        c = conn.cursor()

        logging.info(f'Inserting file entry into database: filename={file.filename}, subdirectory={subdirectory}, file_type={file_type}')
        # Insert only the file path into the database
        c.execute('INSERT INTO files (filename, subdirectory, filetype, filedata) VALUES (?, ?, ?, ?)',
                  (file.filename, subdirectory, file_type, file_path))

        conn.commit()
        conn.close()

        logging.info(f'File created successfully: {file_path}')
        return jsonify({"message": f"File '{file.filename}' created successfully in '{subdirectory}'."})
    except Exception as e:
        logging.error(f'Error creating file: {str(e)}')
        return jsonify({"error": f"Failed to create file: {str(e)}"}), 500


#.....File RETRIVER.......

@app.route('/files', methods=['GET'])
def get_files():
    """Retrieve list of files from both the database and the Questions subdirectory."""
    logging.info('Received GET request to retrieve files')
    all_files = {}

    try:
        # Connect to the SQLite database
        logging.info('Connecting to SQLite database')
        conn = sqlite3.connect('users.db')
        c = conn.cursor()

        # Fetch all files from the 'files' table
        logging.info('Fetching files from database')
        c.execute('SELECT subdirectory, filename, filetype FROM files')
        db_files = c.fetchall()

        # Organize files retrieved from the database
        for subdirectory, filename, filetype in db_files:
            if subdirectory not in all_files:
                all_files[subdirectory] = []
            all_files[subdirectory].append({
                'filename': filename,
                'filetype': filetype,
                'source': 'database'
            })

        logging.debug(f'Retrieved {len(db_files)} files from database')
        conn.close()

    except Exception as e:
        logging.error(f'Error retrieving files from database: {str(e)}')
        return jsonify({"error": "Failed to retrieve files from the database."}), 500

    # Retrieve files from the 'Questions' subdirectory within the MAIN_DIRECTORY
    try:
        questions_path = os.path.join(MAIN_DIRECTORY, "Questions")
        if os.path.exists(questions_path):
            logging.info(f'Scanning the Questions subdirectory at {questions_path}')
            
            # Get all files in the 'Questions' subdirectory
            for root, dirs, files in os.walk(questions_path):
                for file in files:
                    file_path = os.path.join(root, file)
                    rel_path = os.path.relpath(file_path, MAIN_DIRECTORY)
                    subdirectory = "Questions"

                    if subdirectory not in all_files:
                        all_files[subdirectory] = []
                    all_files[subdirectory].append({
                        'filename': file,
                        'filetype': os.path.splitext(file)[1][1:],  # Get file extension without the dot
                        'source': 'filesystem'
                    })

            logging.info(f'Retrieved {len(all_files.get("Questions", []))} files from the Questions subdirectory')

    except Exception as e:
        logging.error(f'Error retrieving files from the Questions subdirectory: {str(e)}')
        return jsonify({"error": "Failed to retrieve files from the Questions subdirectory."}), 500

    return jsonify(all_files)


@app.route('/get_file/<filename>/<subdirectory>')
def get_file(filename, subdirectory):
    app.logger.debug(f"Received request to get file: {filename} in subdirectory: {subdirectory}")
    
    try:
        # Construct the full path to the file in the OS
        file_path = os.path.join(QUESTIONS_FOLDER, subdirectory, secure_filename(filename))
        app.logger.debug(f"Constructed file path: {file_path}")

        # Check if the file exists in the OS
        if os.path.exists(file_path):
            # Ensure the path is safe to prevent directory traversal attacks
            if os.path.abspath(file_path).startswith(os.path.abspath(QUESTIONS_FOLDER)):
                # Return the file content
                app.logger.info(f"Returning file from OS: {file_path}")
                return send_file(file_path, as_attachment=True, download_name=filename)
            else:
                app.logger.warning(f"Access denied for path: {file_path}")
                return jsonify({"error": "Access denied"}), 403
        else:
            # If the file is not found in the OS, search the database
            app.logger.info(f"File not found in OS, searching database...")
            db_file_path = search_file_in_database(filename, subdirectory)
            if db_file_path and os.path.exists(db_file_path):
                # Return the file content using the path stored in the database
                app.logger.info(f"Returning file from path stored in database: {db_file_path}")
                return send_file(db_file_path, as_attachment=True, download_name=filename)
            else:
                app.logger.warning(f"File not found in database or at stored path: {filename}")
                return jsonify({"error": "File not found"}), 404

    except Exception as e:
        app.logger.error(f"Error in get_file: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500
def search_file_in_database(filename, subdirectory):
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    
    c.execute('SELECT filedata FROM files WHERE filename = ? AND subdirectory = ?', (filename, subdirectory))
    result = c.fetchone()
    
    conn.close()
    
    return result[0] if result else None

@app.route('/read', methods=['GET'])
def read_file():
    """
    Read the contents of a file from the specified subdirectory.
    Expects 'subdirectory' and 'filename' as query parameters.
    """
    subdirectory = request.args.get('subdirectory')
    filename = request.args.get('filename')

    is_valid, response = validate_subdirectory(subdirectory)
    if not is_valid:
        return jsonify({"error": response}), 400

    file_path = os.path.join(response, filename)
    
    if not os.path.exists(file_path):
        return jsonify({"error": f"File '{filename}' does not exist in '{subdirectory}'."}), 404

    try:
        with open(file_path, 'r') as file:
            content = file.read()
        return jsonify({"filename": filename, "content": content})
    except Exception as e:
        return jsonify({"error": f"Failed to read file: {str(e)}"}), 500


@app.route('/update', methods=['PUT'])
def update_file():
    """
    Update the contents of an existing file in the specified subdirectory.
    Expects JSON with 'subdirectory', 'filename', and 'content' keys.
    """
    data = request.json
    subdirectory = data.get('subdirectory')
    filename = data.get('filename')
    content = data.get('content', '')

    is_valid, response = validate_subdirectory(subdirectory)
    if not is_valid:
        return jsonify({"error": response}), 400

    file_path = os.path.join(response, filename)
    
    if not os.path.exists(file_path):
        return jsonify({"error": f"File '{filename}' does not exist in '{subdirectory}'."}), 404

    try:
        with open(file_path, 'w') as file:
            file.write(content)
        return jsonify({"message": f"File '{filename}' updated successfully in '{subdirectory}'."})
    except Exception as e:
        return jsonify({"error": f"Failed to update file: {str(e)}"}), 500


@app.route('/delete', methods=['DELETE'])
def delete_file():
    """
    Delete a file from the specified subdirectory or database.
    Expects JSON with 'subdirectory' and 'filename' keys.
    """
    data = request.json
    subdirectory = data.get('subdirectory')
    filename = data.get('filename')

    is_valid, response = validate_subdirectory(subdirectory)
    if not is_valid:
        return jsonify({"error": response}), 400

    file_path = os.path.join(response, filename)

    # Attempt to delete the file from the filesystem
    if os.path.exists(file_path):
        try:
            os.remove(file_path)
            message = f"File '{filename}' deleted successfully from '{subdirectory}' filesystem."
        except Exception as e:
            return jsonify({"error": f"Failed to delete file from filesystem: {str(e)}"}), 500
    else:
        message = f"File '{filename}' does not exist in the filesystem."
    
    # Attempt to delete the file from the database
    try:
        conn = sqlite3.connect('users.db')
        c = conn.cursor()
        c.execute('DELETE FROM files WHERE subdirectory = ? AND filename = ?', (subdirectory, filename))
        conn.commit()
        conn.close()
        message += f" File '{filename}' also deleted from '{subdirectory}' database."
    except Exception as e:
        return jsonify({"error": f"Failed to delete file from database: {str(e)}"}), 500

    return jsonify({"message": message})


# Flask function to run in a separate process
def run_flask():
    try:
        print("Starting Flask server...")
        socketio.run(app, debug=False, host='0.0.0.0', port=5000, use_reloader=False)
    except KeyboardInterrupt:
        app.logger.info('Shutting down server...')
        print("Flask process interrupted. Shutting down...")
    finally:
        socketio.stop()  # Gracefully stop the Flask-SocketIO server

# Overriding the closeEvent method to stop Flask and clean up
def closeEvent(self, event):
    try:
        if hasattr(self, 'flask_process') and self.flask_process.is_alive():
            print("Terminating Flask process...")
            self.flask_process.terminate()
            self.flask_process.join(timeout=5)
            if self.flask_process.is_alive():
                print("Flask process still running, force killing it...")
                self.flask_process.kill()
    except Exception as e:
        print(f"Error during closeEvent: {str(e)}")
    finally:
        event.accept()

# PyQt function to run in the main process
def run_pyqt(flask_process):
    qt_app = QApplication(sys.argv)
    browser = FuturisticBrowser(flask_process)
    # Connect closeEvent for cleanup
    browser.closeEvent = lambda event: closeEvent(browser, event)
    sys.exit(qt_app.exec())

# Graceful exit for the Flask process at program end
def cleanup_process(flask_process):
    if flask_process.is_alive():
        print("Cleaning up Flask process...")
        flask_process.terminate()
        flask_process.join()

if __name__ == '__main__':
    multiprocessing.freeze_support()

    # Signal handler to cleanly exit on Ctrl+C
    def signal_handler(sig, frame):
        print("Exiting the application...")
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)

    # Create and start the Flask process
    flask_process = Process(target=run_flask)
    flask_process.start()
    print("Flask process started with PID:", flask_process.pid)

    # Ensure Flask process is cleaned up at exit
    atexit.register(cleanup_process, flask_process)

    # Run the PyQt5 app
    run_pyqt(flask_process)
