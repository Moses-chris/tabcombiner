import sys
from PyQt6.QtWidgets import (QApplication, QMainWindow, QTabWidget, 
                           QWidget, QVBoxLayout, QPushButton, QMenu)
from PyQt6.QtCore import Qt, QPoint
from PyQt6.QtGui import QDragEnterEvent, QDropEvent, QDragMoveEvent

class TabWindow(QMainWindow):
    """Main window that can host other windows as tabs"""
    
    def __init__(self):
        super().__init__()
        self.setAcceptDrops(True)
        self.setWindowTitle("Window Manager")
        
        # Create the tab widget
        self.tab_widget = DraggableTabWidget(self)
        self.setCentralWidget(self.tab_widget)
        
        # Set up window properties
        self.resize(800, 600)
        
    def dragEnterEvent(self, event: QDragEnterEvent):
        """Handle drag enter events for window combining"""
        if event.mimeData().hasFormat("application/x-window-id"):
            event.acceptProposedAction()
    
    def dropEvent(self, event: QDropEvent):
        """Handle drop events to combine windows"""
        window_id = int(event.mimeData().data("application/x-window-id"))
        self.addWindowAsTab(window_id)
        
    def addWindowAsTab(self, window_id):
        """Add a window as a new tab"""
        window = QWidget.find(window_id)
        if window:
            # Create a container for the window
            container = QWidget()
            layout = QVBoxLayout(container)
            layout.addWidget(window)
            
            # Add the container as a new tab
            self.tab_widget.addTab(container, window.windowTitle())

class DraggableTabWidget(QTabWidget):
    """Custom tab widget that supports drag and drop"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setTabsClosable(True)
        self.setMovable(True)
        self.tabCloseRequested.connect(self.handleTabClose)
        
        # Enable drag and drop
        self.setAcceptDrops(True)
    
    def mousePressEvent(self, event):
        """Handle mouse press events for tab dragging"""
        if event.button() == Qt.MouseButton.RightButton:
            # Show context menu
            menu = QMenu(self)
            detach_action = menu.addAction("Detach Tab")
            action = menu.exec(self.mapToGlobal(event.pos()))
            
            if action == detach_action:
                self.detachCurrentTab()
        else:
            super().mousePressEvent(event)
    
    def handleTabClose(self, index):
        """Handle tab close button clicks"""
        widget = self.widget(index)
        self.removeTab(index)
        
        # Create new window for the detached tab if needed
        if self.count() == 0:
            self.parent().close()
        else:
            widget.setParent(None)
            widget.show()
    
    def detachCurrentTab(self):
        """Detach the current tab into a new window"""
        current_index = self.currentIndex()
        if current_index >= 0:
            # Get the tab content
            tab_name = self.tabText(current_index)
            widget = self.widget(current_index)
            
            # Remove the tab
            self.removeTab(current_index)
            
            # Create a new window
            new_window = TabWindow()
            new_window.tab_widget.addTab(widget, tab_name)
            new_window.show()
            
            # Close the window if no tabs remain
            if self.count() == 0:
                self.parent().close()

def main():
    app = QApplication(sys.argv)
    
    # Create the main window
    window = TabWindow()
    window.show()
    
    sys.exit(app.exec())

if __name__ == "__main__":
    main()