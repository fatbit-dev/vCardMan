import os

import vobject

from PyQt5.QtWidgets import (
    QMainWindow, QSplitter, QListWidget, QListWidgetItem,
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QFileDialog,
    QMessageBox, QAction, QStatusBar, QPushButton,
)
from PyQt5.QtCore import Qt

from vcardman.ui.editor import VCardEditor
from vcardman.utils.vcard_utils import (
    contact_display_name,
    card_matches,
    clean_card_whitespace,
    normalize_binary_fields,
)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("vCard Manager")
        self.resize(900, 650)

        self._vcards = []
        self._sorted_vcards = []   # all cards, sorted
        self._filtered_vcards = [] # subset currently shown in the list
        self._current_file = ""
        self._dirty = False
        self._new_card = None  # card being created, not yet confirmed

        self._build_menu()
        self._build_central()
        self._build_statusbar()
        self._update_status()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_menu(self):
        mb = self.menuBar()

        file_menu = mb.addMenu("&File")

        act_open = QAction("&Open\u2026", self)
        act_open.setShortcut("Ctrl+O")
        act_open.triggered.connect(self._open_file)
        file_menu.addAction(act_open)

        file_menu.addSeparator()

        act_save = QAction("&Save", self)
        act_save.setShortcut("Ctrl+S")
        act_save.triggered.connect(self._save_file)
        file_menu.addAction(act_save)

        act_saveas = QAction("Save &As\u2026", self)
        act_saveas.setShortcut("Ctrl+Shift+S")
        act_saveas.triggered.connect(self._save_file_as)
        file_menu.addAction(act_saveas)

        file_menu.addSeparator()

        act_quit = QAction("&Quit", self)
        act_quit.setShortcut("Ctrl+Q")
        act_quit.triggered.connect(self.close)
        file_menu.addAction(act_quit)

        mb.addMenu("&Edit")

        help_menu = mb.addMenu("&Help")
        act_about = QAction("&About", self)
        act_about.triggered.connect(self._show_about)
        help_menu.addAction(act_about)

    def _build_central(self):
        splitter = QSplitter(Qt.Horizontal)
        splitter.setHandleWidth(4)

        left = QWidget()
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(4, 4, 4, 4)
        left_layout.addWidget(QLabel("Contacts"))

        self._search_box = QLineEdit()
        self._search_box.setPlaceholderText("Search contacts\u2026")
        self._search_box.textChanged.connect(self._on_search_changed)
        left_layout.addWidget(self._search_box)

        self._contact_list = QListWidget()
        self._contact_list.currentRowChanged.connect(self._on_contact_selected)
        left_layout.addWidget(self._contact_list)

        list_btn_row = QWidget()
        list_btn_layout = QHBoxLayout(list_btn_row)
        list_btn_layout.setContentsMargins(0, 0, 0, 0)
        self._add_btn = QPushButton("Add")
        self._add_btn.clicked.connect(self._add_contact)
        self._delete_btn = QPushButton("Delete")
        self._delete_btn.clicked.connect(self._delete_contact)
        self._delete_btn.setEnabled(False)
        list_btn_layout.addWidget(self._add_btn)
        list_btn_layout.addWidget(self._delete_btn)
        left_layout.addWidget(list_btn_row)

        self._editor = VCardEditor()
        self._editor.on_change_callback = self._mark_dirty
        self._editor.on_cancel_callback = self._on_cancel_new_contact

        splitter.addWidget(left)
        splitter.addWidget(self._editor)
        splitter.setStretchFactor(0, 13)
        splitter.setStretchFactor(1, 30)
        splitter.setSizes([270, 630])

        self.setCentralWidget(splitter)

    def _build_statusbar(self):
        self._statusbar = QStatusBar()
        self.setStatusBar(self._statusbar)

    # ------------------------------------------------------------------
    # State helpers
    # ------------------------------------------------------------------

    def _update_status(self):
        if not self._current_file:
            msg = "No file opened"
        else:
            count = len(self._vcards)
            dirty = " [modified]" if self._dirty else ""
            msg = f"{self._current_file}  \u2014  {count} contact(s){dirty}"
        self._statusbar.showMessage(msg)

        title = "vCard Manager"
        if self._current_file:
            title += f" \u2014 {os.path.basename(self._current_file)}"
            if self._dirty:
                title += " *"
        self.setWindowTitle(title)

    def _mark_dirty(self):
        self._dirty = True
        current_card = self._editor._card
        # If Apply was clicked while creating a new card, exit new-card mode
        if self._new_card is not None:
            self._new_card = None
            self._contact_list.setEnabled(True)
            self._search_box.setEnabled(True)
            self._add_btn.setEnabled(True)
            self._populate_list(selected_card=current_card)
            self._editor.set_card(current_card, new_card_mode=False)
            self._delete_btn.setEnabled(self._contact_list.currentRow() >= 0)
        else:
            self._populate_list(selected_card=current_card)
        self._update_status()

    def _confirm_discard(self):
        if not self._dirty:
            return True
        reply = QMessageBox.question(
            self, "Unsaved Changes",
            "You have unsaved changes. Discard them?",
            QMessageBox.Discard | QMessageBox.Cancel,
        )
        return reply == QMessageBox.Discard

    # ------------------------------------------------------------------
    # File operations
    # ------------------------------------------------------------------

    def _open_file(self):
        if not self._confirm_discard():
            return
        path, _ = QFileDialog.getOpenFileName(
            self, "Open VCF File", "",
            "vCard Files (*.vcf *.vcard);;All Files (*)"
        )
        if not path:
            return
        try:
            with open(path, "r", encoding="utf-8", errors="replace") as fh:
                raw = fh.read()
            cards = list(vobject.readComponents(raw))
        except Exception as exc:
            QMessageBox.critical(self, "Error", f"Failed to read file:\n{exc}")
            return

        self._vcards = cards
        self._current_file = path
        self._dirty = False
        self._populate_list()
        self._editor.set_card(None)
        self._update_status()

    def _save_file(self):
        if not self._current_file:
            self._save_file_as()
            return
        self._write_file(self._current_file)

    def _save_file_as(self):
        path, _ = QFileDialog.getSaveFileName(
            self, "Save VCF File", self._current_file or "",
            "vCard Files (*.vcf *.vcard);;All Files (*)"
        )
        if not path:
            return
        previous_file = self._current_file
        self._current_file = path
        if not self._write_file(path):
            self._current_file = previous_file
            self._update_status()

    def _write_file(self, path):
        try:
            with open(path, "w", encoding="utf-8") as fh:
                for card in self._vcards:
                    clean_card_whitespace(card)
                    normalize_binary_fields(card)
                    fh.write(card.serialize())
        except Exception as exc:
            QMessageBox.critical(self, "Error", f"Failed to save file:\n{exc}")
            return False
        self._dirty = False
        self._update_status()
        self._statusbar.showMessage(f"Saved to {path}", 4000)
        return True

    # ------------------------------------------------------------------
    # Contact list
    # ------------------------------------------------------------------

    def _populate_list(self, selected_card=None):
        self._sorted_vcards = sorted(
            self._vcards,
            key=lambda card: contact_display_name(card).casefold(),
        )
        self._apply_filter(selected_card=selected_card)

    def _apply_filter(self, selected_card=None):
        term = self._search_box.text()
        self._filtered_vcards = [
            card for card in self._sorted_vcards if card_matches(card, term)
        ]

        self._contact_list.blockSignals(True)
        self._contact_list.clear()
        for card in self._filtered_vcards:
            item = QListWidgetItem(contact_display_name(card))
            self._contact_list.addItem(item)

        if selected_card is not None and selected_card in self._filtered_vcards:
            self._contact_list.setCurrentRow(
                self._filtered_vcards.index(selected_card)
            )

        self._contact_list.blockSignals(False)

    def _on_search_changed(self, _text):
        self._apply_filter()

    def _on_contact_selected(self, row):
        if 0 <= row < len(self._filtered_vcards):
            self._editor.set_card(self._filtered_vcards[row])
        else:
            self._editor.set_card(None)
        self._delete_btn.setEnabled(row >= 0 and self._new_card is None)

    # ------------------------------------------------------------------
    # Add / Delete contacts
    # ------------------------------------------------------------------

    def _add_contact(self):
        card = vobject.vCard()
        card.add('version').value = '3.0'
        card.add('fn').value = ''
        self._new_card = card
        self._vcards.append(card)

        # Clear the search so the new (empty) card is always visible
        self._search_box.blockSignals(True)
        self._search_box.clear()
        self._search_box.blockSignals(False)

        self._populate_list(selected_card=card)
        self._editor.set_card(card, new_card_mode=True)
        self._contact_list.setEnabled(False)
        self._search_box.setEnabled(False)
        self._add_btn.setEnabled(False)
        self._delete_btn.setEnabled(False)

    def _delete_contact(self):
        row = self._contact_list.currentRow()
        if row < 0 or row >= len(self._filtered_vcards):
            return
        card = self._filtered_vcards[row]
        reply = QMessageBox.question(
            self, "Delete Contact",
            f"Delete '{contact_display_name(card)}'?",
            QMessageBox.Yes | QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return
        self._vcards.remove(card)
        self._dirty = True
        self._populate_list()
        self._editor.set_card(None)
        self._delete_btn.setEnabled(False)
        self._update_status()

    def _on_cancel_new_contact(self):
        if self._new_card is not None:
            self._vcards.remove(self._new_card)
            self._new_card = None
        self._contact_list.setEnabled(True)
        self._search_box.setEnabled(True)
        self._add_btn.setEnabled(True)
        self._delete_btn.setEnabled(False)
        self._populate_list()
        self._editor.set_card(None)
        self._update_status()

    # ------------------------------------------------------------------
    # Misc
    # ------------------------------------------------------------------

    def _show_about(self):
        QMessageBox.about(
            self, "About vCard Manager",
            "<b>vCard Manager</b><br>A simple VCF editor built with PyQt5 and vobject."
        )

    def closeEvent(self, event):
        if self._confirm_discard():
            event.accept()
        else:
            event.ignore()
