from PyQt5.QtWidgets import (
    #QLabel,
    #QLineEdit,
    QWidget,
    #QApplication,
    #QFormLayout,
    #QComboBox,
    #QCheckBox,
    #QPushButton,
    #QFileDialog,
    #QPlainTextEdit,
    QVBoxLayout,
    #QStyle,
    #QMainWindow,
    QTabWidget,
)
from gui.TabWindow import TabWindow

class TableWindow(QWidget):
    def __init__(self, parent=None):
        super(QWidget, self).__init__(parent)
        self.layout = QVBoxLayout(self)

        self.tabs = QTabWidget()
        self.tab1 = TabWindow()
        self.tab2 = TabWindow()
        self.tab3 = TabWindow()
        self.tabs.addTab(self.tab1,'Dummy Tab 1')

