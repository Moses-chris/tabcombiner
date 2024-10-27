import sys
import platform
from PyQt6.QtWidgets import (QApplication, QMainWindow, QTabWidget, 
                           QWidget, QVBoxLayout, QLabel, QMenu)
from PyQt6.QtCore import Qt, QPoint, QTimer
from PyQt6.QtGui import QWindow, QScreen

# Platform-specific imports
if platform.system() == "Linux":
    from Xlib import display, X
    from Xlib.protocol import event
    import Xlib.XK
    import subprocess
elif platform.system() == "Windows":
    import win32gui
    import win32con
    import win32process

class WindowGrabber:
    """Handle platform-specific window operations"""
    
    def __init__(self):
        self.system = platform.system()
        if self.system == "Linux":
            self.display = display.Display()
            self.root = self.display.screen().root
        
    def get_window_list(self):
        """Get list of all windows"""
        windows = []
        
        if self.system == "Linux":
            def get_windows(window):
                windows = []
                for child in window.query_tree().children:
                    try:
                        if child.get_attributes().map_state == X.IsViewable:
                            win_class = child.get_wm_class()
                            if win_class and win_class[1] != "tabCombiner":
                                windows.append({
                                    'id': child.id,
                                    'title': child.get_wm_name() or "Unnamed Window",
                                    'window': child
                                })
                        windows.extend(get_windows(child))
                    except:
                        continue
                return windows
                
            return get_windows(self.root)
            
        elif self.system == "Windows":
            def enum_windows_callback(hwnd, windows):
                if win32gui.IsWindowVisible(hwnd):
                    title = win32gui.GetWindowText(hwnd)
                    class_name = win32gui.GetClassName(hwnd)
                    if title and class_name != "tabCombiner":
                        windows.append({
                            'id': hwnd,
                            'title': title,
                            'window': hwnd
                        })
                return True
                
            windows = []
            win32gui.EnumWindows(enum_windows_callback, windows)
            return windows
            
        return windows

    def reparent_window(self, window_id, container_id):
        """Reparent a window to our container"""
        if self.system == "Linux":
            window = self.display.create_resource_object('window', window_id)
            container = self.display.create_resource_object('window', container_id)
            window.reparent(container, 0, 0)
            self.display.sync()
        elif self.system == "Windows":
            win32gui.SetParent(window_id, container_id)

class WindowContainer(QWidget):
    """Container for captured windows"""
    
    def __init__(self, window_info, parent=None):
        super().__init__(parent)
        self.window_info = window_info
        self.window_id = window_info['id']
        self.title = window_info['title']
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Create window container
        self.container = QWidget.createWindowContainer(
            QWindow.fromWinId(self.window_id), self)
        layout.addWidget(self.container)

class TabWindow(QMainWindow):
    """Main window manager"""
    
    def __init__(self):
        super().__init__()
        self.setAcceptDrops(True)
        self.setWindowTitle("Window Manager")
        
        # Initialize window grabber
        self.grabber = WindowGrabber()
        
        # Create tab widget
        self.tab_widget = DraggableTabWidget(self)
        self.setCentralWidget(self.tab_widget)
        
        # Create window menu
        self.create_window_menu()
        
        # Set up window properties
        self.resize(800, 600)
        
        # Update window list periodically
        self.update_timer = QTimer(self)
        self.update_timer.timeout.connect(self.update_window_menu)
        self.update_timer.start(1000)  # Update every second
    
    def create_window_menu(self):
        """Create menu for window selection"""
        menubar = self.menuBar()
        self.window_menu = menubar.addMenu('Windows')
        self.update_window_menu()
    
    def update_window_menu(self):
        """Update the list of available windows"""
        self.window_menu.clear()
        for window in self.grabber.get_window_list():
            action = self.window_menu.addAction(window['title'])
            action.setData(window)
            action.triggered.connect(lambda checked, w=window: self.add_window(w))
    
    def add_window(self, window_info):
        """Add a window as a new tab"""
        container = WindowContainer(window_info, self)
        self.tab_widget.addTab(container, window_info['title'])

class DraggableTabWidget(QTabWidget):
    """Custom tab widget with drag and drop support"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setTabsClosable(True)
        self.setMovable(True)
        self.tabCloseRequested.connect(self.handleTabClose)
    
    def handleTabClose(self, index):
        """Handle tab close events"""
        widget = self.widget(index)
        if isinstance(widget, WindowContainer):
            # Return window to normal state
            if platform.system() == "Linux":
                display_obj = display.Display()
                window = display_obj.create_resource_object('window', widget.window_id)
                root = display_obj.screen().root
                window.reparent(root, 0, 0)
                window.map()
                display_obj.sync()
            elif platform.system() == "Windows":
                win32gui.SetParent(widget.window_id, 0)
                win32gui.ShowWindow(widget.window_id, win32con.SW_SHOW)
        
        self.removeTab(index)
        widget.deleteLater()

def main():
    app = QApplication(sys.argv)
    app.setApplicationName("tabCombiner")
    
    window = TabWindow()
    window.show()
    
    sys.exit(app.exec())

if __name__ == "__main__":
    main()