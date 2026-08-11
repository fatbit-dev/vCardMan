import vobject

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFormLayout, QLineEdit, QTextEdit,
    QPushButton, QScrollArea, QSizePolicy, QFrame, QLabel,
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPixmap

from .vcard_utils import get_field, get_all_fields, clean_card_whitespace, get_photo_data


class VCardEditor(QWidget):
    """Form widget that displays and allows editing of a single vCard."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._card = None
        self._new_card_mode = False
        self.on_change_callback = None
        self.on_cancel_callback = None
        self._build_ui()

    def _build_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(8, 8, 8, 8)

        # Horizontal layout: form on left, photo on right
        content_layout = QHBoxLayout()
        content_layout.setContentsMargins(0, 0, 0, 0)

        # Left side: scroll area with form
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        content_layout.addWidget(scroll)

        container = QWidget()
        scroll.setWidget(container)

        form = QFormLayout(container)
        form.setRowWrapPolicy(QFormLayout.WrapLongRows)
        form.setLabelAlignment(Qt.AlignRight | Qt.AlignVCenter)
        form.setSpacing(6)

        # Simple single-line fields
        self._fields = {}
        simple = [
            ("fn",       "Full Name"),
            ("n_given",  "First Name"),
            ("n_family", "Last Name"),
            ("org",      "Organization"),
            ("title",    "Title"),
            ("bday",     "Birthday"),
            ("url",      "URL"),
        ]
        for key, label in simple:
            le = QLineEdit()
            self._fields[key] = le
            form.addRow(label + ":", le)

        # Multi-value fields (one value per line)
        self._multi = {}
        multi = [
            ("tel",   "Phones\n(one per line)"),
            ("email", "Emails\n(one per line)"),
            ("adr",   "Addresses\n(one per line)"),
        ]
        for key, label in multi:
            te = QTextEdit()
            te.setFixedHeight(72)
            te.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            self._multi[key] = te
            form.addRow(label + ":", te)

        self._note = QTextEdit()
        self._note.setFixedHeight(90)
        form.addRow("Note:", self._note)

        btn_row = QWidget()
        btn_layout = QHBoxLayout(btn_row)
        btn_layout.setContentsMargins(0, 0, 0, 0)
        self._apply_btn = QPushButton("Apply Changes")
        self._apply_btn.clicked.connect(self._apply_changes)
        self._cancel_btn = QPushButton("Cancel")
        self._cancel_btn.clicked.connect(self._on_cancel_clicked)
        self._cancel_btn.setVisible(False)
        btn_layout.addWidget(self._apply_btn)
        btn_layout.addWidget(self._cancel_btn)
        form.addRow("", btn_row)

        # Right side: photo display
        photo_panel = QWidget()
        photo_layout = QVBoxLayout(photo_panel)
        photo_layout.setContentsMargins(0, 0, 0, 0)
        photo_layout.addWidget(QLabel("Photo"))
        self._photo_label = QLabel()
        self._photo_label.setMaximumWidth(200)
        self._photo_label.setMaximumHeight(200)
        self._photo_label.setScaledContents(True)
        self._photo_label.setStyleSheet("border: 1px solid gray;")
        photo_layout.addWidget(self._photo_label, 1, Qt.AlignTop | Qt.AlignHCenter)
        photo_layout.addStretch()
        content_layout.addWidget(photo_panel)

        content_layout.setStretchFactor(scroll, 2)
        content_layout.setStretchFactor(photo_panel, 1)
        outer.addLayout(content_layout)

        self.set_card(None)

    # ------------------------------------------------------------------

    def set_card(self, card, new_card_mode=False):
        """Populate the form from *card* (vobject vCard), or clear if None."""
        self._card = card
        self._new_card_mode = new_card_mode
        self._cancel_btn.setVisible(new_card_mode)
        enabled = card is not None
        all_widgets = (
            list(self._fields.values())
            + list(self._multi.values())
            + [self._note, self._apply_btn]
        )
        for w in all_widgets:
            w.setEnabled(enabled)

        if not enabled:
            for le in self._fields.values():
                le.clear()
            for te in self._multi.values():
                te.clear()
            self._note.clear()
            return

        self._fields["fn"].setText(get_field(card, "fn"))
        n_obj = card.contents.get("n")
        if n_obj:
            v = n_obj[0].value
            self._fields["n_given"].setText(v.given or "")
            self._fields["n_family"].setText(v.family or "")
        else:
            self._fields["n_given"].clear()
            self._fields["n_family"].clear()

        for key in ("org", "title", "bday", "url"):
            self._fields[key].setText(get_field(card, key))

        for key, te in self._multi.items():
            values = get_all_fields(card, key)
            te.setPlainText("\n".join(values))

        self._note.setPlainText(get_field(card, "note"))

        # Load and display photo
        photo_data = get_photo_data(card)
        if photo_data:
            pixmap = QPixmap()
            pixmap.loadFromData(photo_data)
            if not pixmap.isNull():
                self._photo_label.setPixmap(pixmap)
            else:
                self._photo_label.clear()
        else:
            self._photo_label.clear()

    # ------------------------------------------------------------------

    def _apply_changes(self):
        if self._card is None:
            return
        card = self._card

        def set_simple(field, value):
            value = value.strip()
            objs = card.contents.get(field, [])
            if value:
                if objs:
                    objs[0].value = value
                else:
                    card.add(field).value = value
            else:
                if field in card.contents:
                    del card.contents[field]

        set_simple("fn", self._fields["fn"].text())

        given = self._fields["n_given"].text().strip()
        family = self._fields["n_family"].text().strip()
        n_obj = card.contents.get("n")
        if given or family:
            if n_obj:
                n_obj[0].value.given = given
                n_obj[0].value.family = family
            else:
                n = card.add("n")
                n.value = vobject.vcard.Name(family=family, given=given)
        else:
            if "n" in card.contents:
                del card.contents["n"]

        for key in ("org", "title", "bday", "url"):
            set_simple(key, self._fields[key].text())

        for key, te in self._multi.items():
            lines = [line for line in te.toPlainText().splitlines() if line.strip()]
            if key in card.contents:
                del card.contents[key]
            for line in lines:
                card.add(key).value = line.strip()

        set_simple("note", self._note.toPlainText())

        clean_card_whitespace(card)

        if callable(self.on_change_callback):
            self.on_change_callback()

    def _on_cancel_clicked(self):
        if callable(self.on_cancel_callback):
            self.on_cancel_callback()
