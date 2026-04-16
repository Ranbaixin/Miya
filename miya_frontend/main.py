import sys
import os

# 添加项目根目录到路径
FRONTEND_DIR = os.path.abspath(os.path.dirname(__file__))
MIYA_ROOT = os.path.abspath(os.path.join(FRONTEND_DIR, ".."))
sys.path.insert(0, FRONTEND_DIR)
sys.path.insert(0, MIYA_ROOT)

from PyQt5.QtWidgets import QApplication
from PyQt5.QtGui import QIcon
from ui.pyqt_chat_window import ChatWindow


def main():
    app = QApplication(sys.argv)
    app.setWindowIcon(QIcon("ui/img/window_icon.png"))

    win = ChatWindow()
    win.setWindowTitle("弥娅 AI")
    win.show()

    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
