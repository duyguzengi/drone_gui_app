import sys
import traceback
from PyQt5.QtWidgets import QApplication, QMessageBox
from gui.main_window import MainWindow

def main():
    app = QApplication(sys.argv)
    
    try:
        window = MainWindow()
        window.show()
        sys.exit(app.exec_())

    except Exception as e:
        # Hata yakalama ve kullanıcıya bildirme
        error_msg = traceback.format_exc()
        QMessageBox.critical(None, "Fatal Error", f"An error occurred:\n\n{error_msg}")
        sys.exit(1)

if __name__ == "__main__":
    main()

