BUTTON_STYLE = """
QPushButton {
    color: white;
    background-color: rgba(0, 0, 0, 0); /* No background */
    border: none;
    font-size: 16px;
    font-weight: bold;
    font-family: 'Arial';
}
QPushButton:hover {
    color: #AAAAAA; /* Light grey on hover */
}
"""

SLIDER_STYLE = """
QSlider::groove:horizontal {
    height: 8px;
    background: rgba(255, 255, 255, 50);
    margin: 2px 0;
}
QSlider::handle:horizontal {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
        stop:0 #5e81ac, stop:1 #88c0d0);
    border: 1px solid #5e81ac;
    width: 18px;
    margin: -2px 0;
    border-radius: 9px;
    opacity: 0.7;
}
QSlider::add-page:horizontal {
    background: rgba(255, 255, 255, 28);
}
QSlider::sub-page:horizontal {
    background: rgba(0, 120, 215, 100);
}
"""

LABEL_STYLE = """
QLabel {
    color: white;
    font-size: 12px;
    font-family: 'Arial';
    background-color: rgba(0, 0, 0, 0); /* No background */
}
"""
