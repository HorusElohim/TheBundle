import sys
from PySide6.QtWidgets import QApplication
from bundle.player import BundlePlayer


def main():
    app = QApplication(sys.argv)
    app.setStyle("fusion")
    window = BundlePlayer()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
