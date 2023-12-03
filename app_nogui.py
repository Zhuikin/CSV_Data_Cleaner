import sys
import os
from pathlib import Path
from data_cleaner import CleanerCSV

BASE_DIR = Path(__file__).parent
DEFAULT_CONFIG = BASE_DIR / "default_specs.json"
os.chdir(BASE_DIR)


def run_command_line(config_file):
    cleaner = CleanerCSV(config_file)
    cleaner.html_profile()
    cleaner.run_all_cleaners()
    cleaner.html_profile()
    cleaner.csv_write_clean()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        run_command_line(DEFAULT_CONFIG)
    else:
        run_command_line(BASE_DIR / sys.argv[1])
