import sys
import os
from pathlib import Path
from data_cleaner import CleanerCSV
from data_cleaner_ui import CleanerCSVWindow
from PyQt6.QtWidgets import QApplication

BASE_DIR = Path(__file__).parent
os.chdir(BASE_DIR)


def run_command_line(config_file):
    cleaner = CleanerCSV(config_file)
    cleaner.html_profile()
    cleaner.run_all_cleaners()
    cleaner.html_profile()
    cleaner.csv_write_clean()


def run_gui():
    app = QApplication(sys.argv)
    window = CleanerCSVWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    if len(sys.argv) < 2:
        run_gui()
    else:
        run_command_line(BASE_DIR / sys.argv[1])
