from PySide6.QtWidgets import QMessageBox


def warning_popup(parent, title, message):
    QMessageBox.warning(
        parent,
        title,
        message,
        buttons=QMessageBox.Ok,
        defaultButton=QMessageBox.Ok,
    )


def critical_popup(parent, title, message):
    QMessageBox.critical(
        parent,
        title,
        message,
        buttons=QMessageBox.Ok,
        defaultButton=QMessageBox.Ok,
    )
