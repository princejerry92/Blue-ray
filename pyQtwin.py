import sys
import multiprocessing
from multiprocessing import Process
import time
import signal
from PyQt5.QtCore import QObject
from PyQt5 import QtCore, QtGui, QtWidgets, QtMultimedia, QtWebEngineWidgets
from PyQt5.QtCore import QUrl, QTimer, QSize, Qt
from PyQt5.QtWidgets import (
    QApplication, QWidget, QHBoxLayout, QVBoxLayout, QPushButton, 
    QLineEdit, QFrame, QSplashScreen, QMessageBox
)
from PyQt5.QtGui import QPixmap
from PyQt5.QtMultimedia import QMediaPlayer, QSoundEffect, QAudioOutput, QAudioDeviceInfo
from PyQt5.QtWebEngineWidgets import QWebEngineView
from PyQt5.QtWebEngineWidgets import QWebEngineSettings
from PyQt5.QtMultimedia import QMediaPlayer, QMediaContent
from PyQt5.QtMultimedia import QSoundEffect


class SoundPlayer(QObject):
    def __init__(self):
        super().__init__()
        self.effect = QSoundEffect()
        self.effect.setSource(QUrl.fromLocalFile("../cbtenv/static/img/assets/mixkit-intro-news-sound-1151.wav"))

    def play_sound(self):
        self.effect.play()

class WebGLAnimationWidget(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet("background-color: #000000;")
        self.webview = QWebEngineView(self)
        layout = QVBoxLayout(self)
        layout.addWidget(self.webview)
        self.webview.setUrl(QUrl("about:blank"))
        self.webview.setHtml("""
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="utf-8">
                <title>WebGL Animation</title>
                <style>
                    body { margin: 0; overflow: hidden; }
                    canvas { width: 100%; height: 100%; }
                    #text-overlay {
                        position: absolute;
                        bottom: 20px;
                        width: 100%;
                        text-align: center;
                        color: white;
                        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                        font-size: 24px;
                        font-weight: bold;
                    }
                </style>
            </head>
            <body>
                <canvas id="glcanvas"></canvas>
                <div id="text-overlay">A product of ARCTIC FOX INC</div>
                <script src="https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js"></script>
                <script>
                    const scene = new THREE.Scene();
                    const camera = new THREE.PerspectiveCamera(75, window.innerWidth / window.innerHeight, 0.1, 1000);
                    const renderer = new THREE.WebGLRenderer({canvas: document.getElementById('glcanvas')});
                    renderer.setSize(window.innerWidth, window.innerHeight);

                    const geometry = new THREE.TorusKnotGeometry(10, 3, 100, 16);
                    const material = new THREE.MeshBasicMaterial({color: 0x00BFFF, wireframe: true});
                    const torusKnot = new THREE.Mesh(geometry, material);
                    scene.add(torusKnot);

                    camera.position.z = 30;

                    function animate() {
                        requestAnimationFrame(animate);
                        torusKnot.rotation.x += 0.01;
                        torusKnot.rotation.y += 0.01;
                        renderer.render(scene, camera);
                    }
                    animate();

                    window.addEventListener('resize', function() {
                        camera.aspect = window.innerWidth / window.innerHeight;
                        camera.updateProjectionMatrix();
                        renderer.setSize(window.innerWidth, window.innerHeight);
                    });
                </script>
            </body>
            </html>
        """)

class FuturisticBrowser(QtWidgets.QWidget):
    def __init__(self, flask_process):
        super().__init__()
        self.flask_process = flask_process
        self.initUI()
        self.sound_player = SoundPlayer()
        self.show_splash_screen()

    def show_splash_screen(self):
        pixmap = QPixmap(800, 600)
        pixmap.fill(Qt.GlobalColor.black)
        self.splash = QSplashScreen(pixmap, Qt.WindowType.WindowStaysOnTopHint)
        self.splash.setFixedSize(800, 600)
        
        self.webgl_widget = WebGLAnimationWidget()
        self.webgl_widget.setFixedSize(800, 600)
        
        layout = QVBoxLayout()
        layout.addWidget(self.webgl_widget)
        self.splash.setLayout(layout)
        
        self.splash.show()
        QTimer.singleShot(3000, self.hide_splash_screen)

    def hide_splash_screen(self):
        self.splash.close()
        self.showMaximized()
        self.sound_player.play_sound()

    def initUI(self):
        self.setWindowTitle('Futuristic Browser')
        self.setStyleSheet("""
            QWidget {
                background-color: #0F0F23;
                color: #E0E0FF;
                border-radius: 15px;
            }
            QPushButton {
                background-color: #1E3A8A;
                color: #E0E0FF;
                border: none;
                padding: 10px;
                border-radius: 10px;
                font-size: 16px;
                margin: 5px;
            }
            QPushButton:hover {
                background-color: #2563EB;
            }
            QLineEdit {
                background-color: #1F2937;
                color: #E0E0FF;
                border: 2px solid #3B82F6;
                padding: 8px;
                border-radius: 10px;
                font-size: 14px;
            }
            QFrame#sidebar {
                background-color: #1F2937;
                border-radius: 15px;
                margin: 5px;
                padding: 5px;
            }
        """)

        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)

        self.side_nav = QFrame()
        self.side_nav.setObjectName("sidebar")
        self.side_nav.setFixedWidth(120)
        
        side_nav_layout = QVBoxLayout(self.side_nav)
        side_nav_layout.setContentsMargins(0, 0, 0, 0)
        side_nav_layout.setSpacing(10)

        self.start_button = self.create_button('▶', 'Start', self.load_start)
        self.home_button = self.create_button('🏠', 'Home', self.load_home)
        self.admin_button = self.create_button('🛡️', 'Admin', self.load_admin)
        self.url_bar_button = self.create_button('🌐', 'Toggle URL Bar', self.toggle_url_bar)
        self.close_button = self.create_button('❌', 'Close', self.close_browser)

        side_nav_layout.addWidget(self.start_button)
        side_nav_layout.addWidget(self.home_button)
        side_nav_layout.addWidget(self.admin_button)
        side_nav_layout.addWidget(self.url_bar_button)
        side_nav_layout.addStretch()
        side_nav_layout.addWidget(self.close_button)

        content_layout = QVBoxLayout()
        
        nav_layout = QHBoxLayout()
        self.back_button = self.create_button('←', 'Back', self.web_view_back)
        self.forward_button = self.create_button('→', 'Forward', self.web_view_forward)
        self.reload_button = self.create_button('🔄', 'Reload', self.web_view_reload)
        nav_layout.addWidget(self.back_button)
        nav_layout.addWidget(self.forward_button)
        nav_layout.addWidget(self.reload_button)
        nav_layout.addStretch()

        content_layout.addLayout(nav_layout)

        self.url_input_widget = QLineEdit()
        self.url_input_widget.setPlaceholderText('Enter URL...')
        self.url_input_widget.returnPressed.connect(self.load_url)
        self.url_input_widget.setVisible(False)
        content_layout.addWidget(self.url_input_widget)

        self.web_view = QWebEngineView()
        self.web_view.setUrl(QUrl('http://localhost:5000'))
        self.web_view.setStyleSheet("border-radius: 15px;")
        content_layout.addWidget(self.web_view)

        main_layout.addWidget(self.side_nav)
        main_layout.addLayout(content_layout)

        # Set up web settings
        self.web_view.settings().setAttribute(QWebEngineSettings.WebAttribute.LocalStorageEnabled, True)
        self.web_view.settings().setAttribute(QWebEngineSettings.WebAttribute.PluginsEnabled, True)
        self.web_view.settings().setAttribute(QWebEngineSettings.WebAttribute.JavascriptEnabled, True)

    def create_button(self, icon, tooltip, callback):
        button = QPushButton(icon)
        button.setToolTip(tooltip)
        button.setFixedSize(QSize(60, 60))
        button.clicked.connect(callback)
        return button

    def load_start(self):
        self.web_view.setUrl(QUrl('http://localhost:5000/loader'))

    def load_home(self):
        self.web_view.setUrl(QUrl('http://localhost:5000/home'))

    def load_admin(self):
        self.web_view.setUrl(QUrl('http://localhost:5000/login'))

    def close_browser(self):
        reply = QMessageBox.question(self, 'Close Window', 'Are you sure you want to close the Software?',
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            QApplication.quit()

    def load_url(self):
        url = self.url_input_widget.text()
        if not url.startswith('http'):
            url = 'http://' + url
        self.web_view.setUrl(QUrl(url))

    def toggle_url_bar(self):
        self.url_input_widget.setVisible(not self.url_input_widget.isVisible())

    def web_view_back(self):
        self.web_view.back()

    def web_view_forward(self):
        self.web_view.forward()

    def web_view_reload(self):
        self.web_view.reload()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_F5:
            self.web_view.reload()
    
    def closeEvent(self, event):
        try:
            if hasattr(self, 'flask_process') and self.flask_process.is_alive():
                print("Terminating Flask process...")
                self.flask_process.terminate()
                self.flask_process.join(timeout=5)
                if self.flask_process.is_alive():
                    print("Flask process still running, killing it...")
                    self.flask_process.kill()
        except Exception as e:
            print(f"Error during closeEvent: {str(e)}")
        finally:
            event.accept()

def run_pyqt(flask_process):
    qt_app = QApplication(sys.argv)
    browser = FuturisticBrowser(flask_process)
    sys.exit(qt_app.exec())
