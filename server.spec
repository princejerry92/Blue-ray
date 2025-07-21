# -*- mode: python ; coding: utf-8 -*-
# File: CBT.spec

from PyInstaller.utils.hooks import collect_data_files
from PyInstaller.building.build_main import Analysis, PYZ, EXE, COLLECT
import os

# Paths
main_script = 'server2.py'
icon_path = os.path.join(os.path.abspath('.'), 'C:\\CBT\\.venv\\pyWinicon.ico')

# Adding Flask static and templates directories
flask_data_files = [
    ('static', 'static'),
    ('templates', 'templates')
]

# Analysis of the codebase, adding hidden imports, and data files
a = Analysis(
    [main_script],
    pathex=['.'],
    binaries=[],
    datas=collect_data_files('extractdocx') + collect_data_files('jaraco.text') + collect_data_files('pyQtwin') +
        flask_data_files + collect_data_files('extract_text'),
    hiddenimports=[
        # Flask-SocketIO and dependencies (updated for gevent)
        'flask_socketio', 'socketio', 'engineio.async_drivers.threading', 'engineio.async_drivers.gevent',
        'gevent', 'gevent.monkey', 'pkg_resources.py2_warn', 'gunicorn', 'gunicorn.glogging', 'gunicorn.workers.ggevent',

        # DNS
        'dns',
        'dns.asyncbackend',
        'dns.asyncquery',
        'dns.asyncresolver',
        'dns.e164',
        'dns.namedict',
        'dns.tsigkeyring',
        'dns.versioned',
        'dns.dnssec',
        'dns.name',
        'dns.message',
        'dns.resolver',
        'dns.exception',
        'dns.rdatatype',
        'dns.rdataclass',
        'dns.rdata',
        'dns.flags',
        'dns.rrset',
        'dns.renderer',
        'dns.rdtypes',
        'dns.tokenizer',
        'dns.wire',
        'dns.zone',
        'dns.ipv4',
        'dns.ipv6',
        'dns.update',
        'dns.version',

        # EngineIO and Flask-SocketIO
        'engineio',
        'engineio.async_drivers.threading',
        'engineio.async_drivers.gevent',
        'engineio.async_sockets',
        'engineio.packet',
        'engineio.payload',
        'engineio.socket',
        'engineio.namespace',
        'engineio.async_namespace',
        'engineio.client',
        'engineio.server',
        'engineio.exceptions',
        'flask_socketio',
        'socketio',

        #gevent
        'gevent',
        'gevent.builtins',
        'gevent.monkey',
        'gevent.greenlet',
        'gevent.socket',
        'gevent.ssl',
        'gevent.thread',
        'gevent.threading',
        'gevent.select',
        'geventwebsocket',
        'engineio.async_drivers.gevent',
        'dns.dnssec',
        'dns.e164',
        'dns.hash',
        'dns.namedict',
        'dns.tsigkeyring',
        'dns.update',
        'dns.version',
        'dns.zone'

        # Document handling imports
        'docx',
        'python-docx',
        'PyPDF2',
        'PyPDF2.pdf',
        'PyPDF2.generic',
        'fpdf',
        'fitz',
        'pymupdf',
        'pdf2image',

            
        # PyQt5 and PyQtWebEngine dependencies
        'PyQt5', 'PyQt5.QtCore', 'PyQt5.QtWidgets', 'PyQt5.QtWebEngineWidgets', 'PyQt5.QtGui', 'PyQt5.QtWebChannel',
        
        # Docx, PDF, and image handling
        'docx', 'PyPDF2', 'fpdf', 'fitz', 'pdf2image', 'PIL', 'python-docx',

        # Additional dependencies
        'sqlite3', 'base64', 'io', 'chardet', 'logging', 'tqdm', 'multiprocessing', 're'
    ],
    hookspath=[],
    runtime_hooks=[],
    excludes=['PySide6', 'PySide6.QtCore', 'PySide6.QtGui', 'PySide6.QtWidgets'],  
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=None,
)

# Packing into a single bundled file
pyz = PYZ(a.pure, a.zipped_data, cipher=None)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='Dylan CBT VII',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,  # Set to True if console output is needed
    icon=icon_path,
)

# Gathering the necessary files and creating the final bundle
coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    name='Dylan CBT VII'
)
