from PyQt6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton
from PyQt6.QtCore import Qt


class AboutDialog(QDialog):
    def __init__(self, settings=None, parent=None):
        super().__init__(parent)
        self.setObjectName("SettingsDialog")
        self.setWindowTitle("About FFMigo")
        self.setMinimumWidth(400)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 32, 32, 32)
        layout.setSpacing(24)

        title = QLabel("FFMigo Video Editor")
        title.setObjectName("AboutTitle")
        title.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        layout.addWidget(title)

        version = QLabel("Version 1.0")
        version.setObjectName("AboutVersion")
        version.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        layout.addWidget(version)

        desc = QLabel("AI-powered video editing with natural language commands. Transform your videos using simple text descriptions.")
        desc.setWordWrap(True)
        desc.setObjectName("AboutDesc")
        desc.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        layout.addWidget(desc)

        dev_info = QLabel("Developed by Apurv")
        dev_info.setObjectName("AboutDevInfo")
        dev_info.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        layout.addWidget(dev_info)

        links_layout = QHBoxLayout()
        links_layout.setSpacing(20)
        links_layout.setAlignment(Qt.AlignmentFlag.AlignHCenter)

        twitter_btn = QPushButton("🐦 Twitter")
        twitter_btn.setObjectName("TwitterButton")
        twitter_btn.clicked.connect(lambda: self._open_url("https://twitter.com/apurvns"))
        links_layout.addWidget(twitter_btn)

        github_btn = QPushButton("📦 GitHub")
        github_btn.setObjectName("GitHubButton")
        github_btn.clicked.connect(lambda: self._open_url("https://github.com/apurvns/ffmigo"))
        links_layout.addWidget(github_btn)

        contributors_btn = QPushButton("👥 Contributors")
        contributors_btn.setObjectName("ContributorsButton")
        contributors_btn.clicked.connect(lambda: self._open_url("https://github.com/apurvns/ffmigo/graphs/contributors"))
        links_layout.addWidget(contributors_btn)

        layout.addLayout(links_layout)

        close_btn = QPushButton("Close")
        close_btn.setObjectName("AboutCloseButton")
        close_btn.clicked.connect(self.accept)
        close_btn.setFixedWidth(120)

        btn_layout = QHBoxLayout()
        btn_layout.addStretch(1)
        btn_layout.addWidget(close_btn)
        btn_layout.addStretch(1)
        layout.addLayout(btn_layout)

    def _open_url(self, url: str):
        from PyQt6.QtCore import QUrl
        from PyQt6.QtGui import QDesktopServices
        QDesktopServices.openUrl(QUrl(url))


