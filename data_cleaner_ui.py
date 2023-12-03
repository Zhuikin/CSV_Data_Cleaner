from pathlib import Path
from typing import Callable
from PyQt6.QtWidgets import (
    QMainWindow,
    QPushButton,
    QTabWidget,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QSizePolicy,
    QFileDialog,
    QMessageBox
)
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtCore import (
    Qt,
    QUrl,
    QThread,
    pyqtSignal,
    QSettings
)
from data_cleaner import CleanerCSV
from data_cleaner_spec_editor import SpecsEditor

BASE_DIR = Path(__name__).parent.absolute()
INI_FILE_NAME = (BASE_DIR / "settings.ini").__str__()
BUTTONS_WIDTH = 150
MINIMUM_WINDOW = (800, 600)


class CleanerCSVWindow(QMainWindow):
    """ GUI class for the CleanerCSV app.
    """
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Cleaner CSV")
        self.setMinimumSize(*MINIMUM_WINDOW)
        geometry = QSettings(
            INI_FILE_NAME,
            QSettings.Format.IniFormat
        ).value("geometry")
        if geometry is not None:
            self.restoreGeometry(geometry)
        else:
            self.setGeometry(100, 100, *MINIMUM_WINDOW)

        self.tabs_widget = QTabWidget(self)
        self.cleaner = None
        self.long_task_thread = None

        (
            self.spec_load_button,
            self.cleaner_launch_button,
            self.specs_file_label,
            self.status_label,
            self.browser_specs,
            self.browser_clean,
            self.browser_source,
            self.browser_log
        ) = self.setup_ui()

    def setup_ui(self):
        """ Creates the main GUI window.

        Retruns:
            tuple: A set of handles for minipulating the created widgets
        """

        # control and file selection widget
        control_wgt = QWidget(self)
        control_wgt_layout = QHBoxLayout(control_wgt)
        control_wgt_layout.setAlignment(Qt.AlignmentFlag.AlignLeft)
        # button will launch the cleaning process
        cleaner_launch_button = self.make_button("Clean data")
        cleaner_launch_button.clicked.connect(self.on_cleaner_launch_click)
        cleaner_launch_button.setEnabled(False)
        control_wgt_layout.addWidget(cleaner_launch_button)
        # button will bring up the file selection dialog for spec files
        spec_load_button = self.make_button("Load specs")
        spec_load_button.clicked.connect(self.on_spec_load_click)
        control_wgt_layout.addWidget(spec_load_button)
        # label showing the currently selected spec files name
        specs_file_label = QLabel("No specs file loaded", self)
        specs_file_label.sizePolicy().setHorizontalPolicy(
            QSizePolicy.Policy.Expanding
        )
        control_wgt_layout.addWidget(specs_file_label)

        status_label = QLabel("", self)
        status_label.sizePolicy().setHorizontalPolicy(
            QSizePolicy.Policy.Expanding
        )

        # tabbed info widgets
        # placeholder pages to preload into the browser widgets
        url_placeholder = QUrl.fromLocalFile(
            (BASE_DIR / "empty_page.html").__str__()
        )
        url_readme = QUrl.fromLocalFile(
            (BASE_DIR / "readme_page.html").__str__()
        )

        # tab 0 intro message
        self.make_browser_widget(
            url_readme,
            tab_title="Introduction"
        )

        # tab 1 specs file
        # text editor specs display
        browser_specs = SpecsEditor(self.tabs_widget, 1)
        self.tabs_widget.addTab(browser_specs, "No specs loaded")

        # tab 2 cleaned profile view
        browser_clean = self.make_browser_widget(
            url_placeholder,
            tab_title="Current profile"
        )

        # tab 3 source profile view
        browser_source = self.make_browser_widget(
            url_placeholder,
            tab_title="Source profile"
        )

        # tab 4 log viewer
        browser_log = self.make_browser_widget(
            url_placeholder,
            tab_title="Logfile"
        )

        # Main Layout
        main_layout = QVBoxLayout()
        main_layout.addWidget(control_wgt)
        main_layout.addWidget(self.tabs_widget)
        main_layout.addWidget(status_label)

        self.tabs_widget.tabBarClicked.connect(self.on_tab_clicked)

        central_widget = QWidget(self)
        central_widget.setLayout(main_layout)

        self.setCentralWidget(central_widget)
        return (
            spec_load_button,
            cleaner_launch_button,
            specs_file_label,
            status_label,
            browser_specs,
            browser_clean,
            browser_source,
            browser_log
        )

    def closeEvent(self, event):
        """ Saves window geometry data when the GUI is terminated.
        """
        QSettings(
            INI_FILE_NAME,
            QSettings.Format.IniFormat
        ).setValue("geometry", self.saveGeometry())
        event.accept()

    def make_browser_widget(
            self,
            preload_url: QUrl,
            tab_title: str
    ) -> QWebEngineView:
        """ Assembles and returns a Qt html browser widget.

        Args:
            preload_url (QUrl): The page to load in the widget
            tab_title: Tab name as displaed on the tab-bar handle
        """
        wgt = QWidget()
        layout = QVBoxLayout(wgt)
        browser = QWebEngineView()
        browser.page().setUrl(preload_url)
        layout.addWidget(browser)
        self.tabs_widget.addTab(wgt, tab_title)
        return browser

    def make_button(
            self,
            button_label: str
    ) -> QPushButton:
        """ Makes a button.
        """
        button = QPushButton(button_label, self)
        button.sizePolicy().setHorizontalPolicy(QSizePolicy.Policy.Fixed)
        button.setFixedWidth(BUTTONS_WIDTH)
        return button

    def on_spec_load_click(self):
        """ Action for the select spec button click.

            Runs the QFileDialog and sends the selected file to
            concerned methods
        """
        full_file_name, _ = QFileDialog.getOpenFileName(
            self,
            "Save specs as json",
            "",
            "JSON files (*.json);;Text files (*.txt);;All files (*)"
        )
        # full_file_name, _ = QFileDialog.getOpenFileName()
        if not full_file_name:
            return
        print("Launcihng attach cleaner")
        self.attach_cleaner(full_file_name)

    def toggle_buttons_enabled(self, set_to: bool):
        """ Locks or unlocks interface buttons
        """
        self.spec_load_button.setEnabled(set_to)
        self.cleaner_launch_button.setEnabled(set_to)

    def attach_cleaner(self, full_file_name: str):
        """ Creates a cleaner instance from the given specs json file.

        Will load the spec, the specified source file and launch the
        Profiler for the source data, sending the results to the respective
        interface elements.

        Args:
            full_file_name: Name of the specs file to use
        """
        self.toggle_buttons_enabled(False)
        if self.cleaner:
            self.cleaner.release_files()
            self.cleaner = None
        self.cleaner = CleanerCSV(Path(full_file_name))
        loaded_spec = self.cleaner.cfg_file.__str__()
        self.specs_file_label.setText(loaded_spec)

        # update the spec editor
        self.browser_specs.load_file(full_file_name)

        # update the log browser
        log_path = str(self.cleaner.logfile.absolute())
        self.browser_log.page().setUrl(
            QUrl.fromLocalFile(log_path)
        )

        # chance to bail out on bad specs
        if Path(full_file_name) != self.cleaner.cfg_file:
            response = QMessageBox.question(
                None,
                "Invalid spec",
                "The spec file could not be loaded.\nRun default spec?",
                QMessageBox.StandardButton.No | QMessageBox.StandardButton.Yes
            )
            if response != QMessageBox.StandardButton.Yes:
                self.toggle_buttons_enabled(True)
                return

        # run profile on source data
        self.status_label.setText("Profiling input data. "
                                  "This might take a minute")
        # delete (possible) previous connections before updating the task
        if self.long_task_thread:
            self.long_task_thread.long_task_done.disconnect()
        self.long_task_thread = LongTaskThread(
            info="Source data profiler",
            task=self.cleaner.html_profile
        )
        self.long_task_thread.long_task_done.connect(
            self.on_long_task_input_profiler
        )
        self.long_task_thread.start()

    def cleaning_tasks(self):
        """ Helper method for launching the cleaning process.
        """
        self.cleaner.run_all_cleaners()
        self.cleaner.html_profile()
        self.cleaner.csv_write_clean()

    def on_cleaner_launch_click(self):
        """ Launches the cleaning and output profiling tasks.

        The tasks can take some time and will be launched as a new thread.
        """
        self.toggle_buttons_enabled(False)

        self.status_label.setText("Processing dataframe. "
                                  "This might take a minute")
        if self.long_task_thread:
            self.long_task_thread.long_task_done.disconnect()

        self.long_task_thread = LongTaskThread(
            info="Cleaning Tasks",
            task=self.cleaning_tasks
        )
        self.long_task_thread.long_task_done.connect(
            self.on_long_task_cleaning
        )
        self.long_task_thread.start()

    def on_long_task_cleaning(self, result):
        """ Event action to launch when after pass of cleaning has finished.
        """
        self.status_label.setText(result)
        self.toggle_buttons_enabled(True)
        profile_url = self.cleaner.output_profile.absolute().__str__()
        profile_url = QUrl.fromLocalFile(profile_url)
        self.browser_clean.page().setUrl(profile_url)
        self.browser_log.reload()

    def on_long_task_input_profiler(self, result):
        """ Event action to launch when the input data processing is finished.
        """
        self.status_label.setText(result)
        self.toggle_buttons_enabled(True)
        profile_url = self.cleaner.input_profile.absolute().__str__()
        profile_url = QUrl.fromLocalFile(profile_url)
        self.browser_source.page().setUrl(profile_url)
        self.browser_log.reload()

    def on_tab_clicked(self, index):
        """ Event action for clicking into the tab selection element.

        Updates the log display tab. The other tabs will update when their
        appropriate procesesses run.
        """
        if index == 4:
            self.browser_log.reload()


class LongTaskThread(QThread):
    """ Threaded worker class for the profiling tasks
    """
    # event triggered on task completion
    long_task_done = pyqtSignal(str)

    def __init__(self, info: str, task: Callable, **task_kwargs: dict):
        super().__init__()
        self.info = info
        self.task = task
        self.task_kwargs = task_kwargs
        self.has_kwargs = False if not task_kwargs else True

    def run(self):
        if self.has_kwargs:
            self.task(**self.task_kwargs)
        else:
            self.task()
        self.long_task_done.emit(f"Task completed: {self.info}")
