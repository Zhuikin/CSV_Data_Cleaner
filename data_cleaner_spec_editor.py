from pathlib import Path
import json
from PyQt6.QtWidgets import (
    QWidget,
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QSizePolicy,
    QLabel,
    QFileDialog,
    QMessageBox
)
from PyQt6.QtCore import (
    Qt
)


class SpecsEditor(QWidget):
    """ Simple text editor widget to eidt specs and save them as JSON files
    """
    def __init__(self, parent_tab: QTabWidget, p_t_index: int):
        super().__init__()

        self.parent_tab = parent_tab
        self.p_t_index = p_t_index
        self.text_editor = QTextEdit(self)
        self.text_editor.setPlainText("No specs file loaded.")
        self.text_editor.textChanged.connect(self.on_text_changed)
        self.setup_ui()

    def setup_ui(self):
        """ Assembles the Editor UI
        """
        buttons_wgt = QWidget(self)
        buttons_wgt_layout = QHBoxLayout(buttons_wgt)
        buttons_wgt_layout.setAlignment(Qt.AlignmentFlag.AlignLeft)

        load_button = QPushButton("Load", self)
        load_button.sizePolicy().setHorizontalPolicy(QSizePolicy.Policy.Fixed)
        load_button.setFixedWidth(100)
        load_button.clicked.connect(self.on_load_file)
        buttons_wgt_layout.addWidget(load_button)

        save_button = QPushButton("Save", self)
        save_button.sizePolicy().setHorizontalPolicy(QSizePolicy.Policy.Fixed)
        save_button.setFixedWidth(100)
        save_button.clicked.connect(self.on_save_file)
        buttons_wgt_layout.addWidget(save_button)

        h = ("Note: The edited file is not auto-loaded in the main app. "
             "Use the \"Load specs\" button once saved.")
        hint_label = QLabel(h, self)
        hint_label.sizePolicy().setHorizontalPolicy(
            QSizePolicy.Policy.Expanding
        )
        buttons_wgt_layout.addWidget(hint_label)

        main_layout = QVBoxLayout(self)
        main_layout.addWidget(buttons_wgt)
        main_layout.addWidget(self.text_editor)

    def on_save_file(self):
        """ Event action for clikcing the save button.
        """
        try:
            self.text_editor.textChanged.disconnect()
        except TypeError:
            pass

        save_data, is_json, do_save = self.check_json()
        if not do_save:
            return

        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Save specs as json",
            "",
            "JSON files (*.json);;Text files (*.txt);;All files (*)"
        )
        if file_path:
            try:
                with open(file_path, "w", encoding="utf-8") as file:
                    if is_json:
                        json.dump(
                            save_data, file, indent=4,
                            ensure_ascii=False
                        )
                    else:
                        file.write(save_data)
                self.parent_tab.setTabText(
                    self.p_t_index,
                    file_path.split("/")[-1]
                )
                self.text_editor.textChanged.connect(self.on_text_changed)
            except IOError:
                self.parent_tab.setTabText(
                    self.p_t_index,
                    "Unsaved JSON"
                )

    def check_json(self) -> tuple:
        """ Validates the text in the editor as JSON

        Returns:
            save_data: will be either a dict or a string for saving
            is_json (bool): if true, save_data is a valid json
            do_save (bool): confirmation if bad data should be saved
        """
        text = self.text_editor.toPlainText()
        try:
            save_data = json.loads(self.text_editor.toPlainText())
            is_json = True
            do_save = True
        except json.JSONDecodeError:
            save_data = text
            is_json = False
            do_save = False

        if not is_json:
            response = QMessageBox.question(
                None,
                "Invalid JSON",
                "Text in the editor is not valid JSON.\nSave anyway?",
                QMessageBox.StandardButton.No | QMessageBox.StandardButton.Yes
            )
            if response == QMessageBox.StandardButton.Yes:
                do_save = True

        return save_data, is_json, do_save


    def on_load_file(self):
        """ Event action for clicking the load button.
        """
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Save specs as json",
            "",
            "JSON files (*.json);;Text files (*.txt);;All files (*)"
        )
        if file_path:
            self.load_file(file_path)

    def load_file(self, filename: str):
        """ Loads the specified file into the editor
        """
        try:
            self.text_editor.textChanged.disconnect()
        except TypeError:
            pass
        try:
            with open(filename, "r", encoding="utf-8") as file:
                specs_text = file.read()
        except IOError:
            specs_text = "No specs file loaded."
        self.text_editor.setPlainText(specs_text)
        self.parent_tab.setTabText(
            self.p_t_index,
            filename.split("/")[-1]
        )
        self.text_editor.textChanged.connect(self.on_text_changed)

    def on_text_changed(self):
        """ Event action for typing in the editor.
        """
        self.parent_tab.setTabText(
            self.p_t_index,
            "Unsaved JSON"
        )
        try:
            self.text_editor.textChanged.disconnect()
        except TypeError:
            pass
