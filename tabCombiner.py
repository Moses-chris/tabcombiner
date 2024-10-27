import sys
import platform
from PyQt6.QtWidgets import (QApplication, QMainWindow, QTabWidget, 
                           QWidget, QVBoxLayout, QLabel, QMenu, QMainWindow,
                           QMenuBar, QStatusBar)
from PyQt6.QtCore import Qt, QPoint, QTimer
from PyQt6.QtGui import QWindow, QScreen, QAction

# Platform-specific imports
if platform.system() == "Linux":
    from Xlib import display, X
    from Xlib.protocol import event
    import Xlib.XK
    import subprocess

class WindowGrabber:
    """Handle platform-specific window operations"""
    
    def __init__(self):
        self.system = platform.system()
        if self.system == "Linux":
            self.display = display.Display()
            self.root = self.display.screen().root
            self._cached_windows = []
            self._last_update = 0
    
    def get_window_list(self):
        """Get list of all windows"""
        if self.system == "Linux":
            windows = []
            try:
                def get_windows(window):
                    children = []
                    try:
                        children = window.query_tree().children
                    except:
                        return []

                    results = []
                    for child in children:
                        try:
                            attrs = child.get_attributes()
                            if attrs.map_state == X.IsViewable:
                                win_class = child.get_wm_class()
                                win_name = child.get_wm_name()
                                
                                # Skip our own window and windows without names
                                if (win_class and win_class[1] != "tabCombiner" and 
                                    win_name and isinstance(win_name, str) and 
                                    win_name.strip()):
                                    results.append({
                                        'id': child.id,
                                        'title': win_name,
                                        'window': child
                                    })
                            results.extend(get_windows(child))
                        except:
                            continue
                    return results

                windows = get_windows(self.root)
                # Sort windows by title for consistent menu ordering
                windows.sort(key=lambda x: x['title'])
                self._cached_windows = windows
                
            except Exception as e:
                print(f"Error getting window list: {e}")
                # Return cached windows if there's an error
                return self._cached_windows
                
            return windows
            
        return []

    def reparent_window(self, window_id, container_id):
        """Reparent a window to our container"""
        if self.system == "Linux":
            try:
                window = self.display.create_resource_object('window', window_id)
                container = self.display.create_resource_object('window', container_id)
                window.reparent(container, 0, 0)
                self.display.sync()
            except Exception as e:
                print(f"Error reparenting window: {e}")

class WindowContainer(QWidget):
    """Container for captured windows"""
    
    def __init__(self, window_info, parent=None):
        super().__init__(parent)
        self.window_info = window_info
        self.window_id = window_info['id']
        self.title = window_info['title']
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        try:
            # Create window container
            self.container = QWidget.createWindowContainer(
                QWindow.fromWinId(self.window_id), self)
            layout.addWidget(self.container)
        except Exception as e:
            # If window capture fails, show error message
            error_label = QLabel(f"Failed to capture window: {self.title}\nError: {str(e)}")
            error_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            layout.addWidget(error_label)

class TabWindow(QMainWindow):
    """Main window manager"""
    
    def __init__(self):
        super().__init__()
        self.setAcceptDrops(True)
        self.setWindowTitle("Window Manager")
        
        # Initialize window grabber
        self.grabber = WindowGrabber()
        
        # Create central widget and layout
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.layout = QVBoxLayout(self.central_widget)
        
        # Create menu bar
        self.create_menu_bar()
        
        # Create tab widget
        self.tab_widget = DraggableTabWidget(self)
        self.layout.addWidget(self.tab_widget)
        
        # Create status bar
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        
        # Set up window properties
        self.resize(800, 600)
        
        # Initialize window list
        self.window_actions = []
        self.update_window_list()
        
        # Set up periodic window list refresh
        self.refresh_timer = QTimer(self)
        self.refresh_timer.timeout.connect(self.refresh_window_list)
        self.refresh_timer.start(5000)  # Refresh every 5 seconds
    
    def create_menu_bar(self):
        """Create the menu bar"""
        self.menubar = QMenuBar()
        self.setMenuBar(self.menubar)
        
        # Create Windows menu
        self.window_menu = QMenu('Windows', self)
        self.menubar.addMenu(self.window_menu)
    
    def update_window_list(self):
        """Update the list of available windows"""
        try:
            # Clear existing menu items
            self.window_menu.clear()
            self.window_actions.clear()
            
            # Get new window list
            windows = self.grabber.get_window_list()
            
            # Add windows to menu
            for window in windows:
                action = QAction(window['title'], self)
                action.setData(window)
                action.triggered.connect(lambda checked, w=window: self.add_window(w))
                self.window_menu.addAction(action)
                self.window_actions.append(action)
            
            # Update status
            self.status_bar.showMessage(f"Found {len(windows)} windows")
            
        except Exception as e:
            self.status_bar.showMessage(f"Error updating window list: {str(e)}")
    
    def refresh_window_list(self):
        """Periodic refresh of window list"""
        try:
            new_windows = self.grabber.get_window_list()
            current_titles = {action.text() for action in self.window_actions}
            new_titles = {w['title'] for w in new_windows}
            
            # Only update if window list has changed
            if current_titles != new_titles:
                self.update_window_list()
        except Exception as e:
            self.status_bar.showMessage(f"Error refreshing window list: {str(e)}")
    
    def add_window(self, window_info):
        """Add a window as a new tab"""
        try:
            # Check if window is already added
            for i in range(self.tab_widget.count()):
                container = self.tab_widget.widget(i)
                if container.window_id == window_info['id']:
                    self.status_bar.showMessage(f"Window '{window_info['title']}' is already added")
                    self.tab_widget.setCurrentIndex(i)
                    return
            
            # Add new window
            container = WindowContainer(window_info, self)
            self.tab_widget.addTab(container, window_info['title'])
            self.tab_widget.setCurrentWidget(container)
            self.status_bar.showMessage(f"Added window: {window_info['title']}")
            
        except Exception as e:
            self.status_bar.showMessage(f"Error adding window: {str(e)}")

class DraggableTabWidget(QTabWidget):
    """Custom tab widget with drag and drop support"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setTabsClosable(True)
        self.setMovable(True)
        self.tabCloseRequested.connect(self.handleTabClose)
    
    def handleTabClose(self, index):
        """Handle tab close events"""
        try:
            widget = self.widget(index)
            if isinstance(widget, WindowContainer):
                if platform.system() == "Linux":
                    display_obj = display.Display()
                    window = display_obj.create_resource_object('window', widget.window_id)
                    root = display_obj.screen().root
                    window.reparent(root, 0, 0)
                    window.map()
                    display_obj.sync()
            
            self.removeTab(index)
            widget.deleteLater()
            
        except Exception as e:
            print(f"Error closing tab: {e}")

def main():
    app = QApplication(sys.argv)
    app.setApplicationName("tabCombiner")
    
    window = TabWindow()
    window.show()
    
    sys.exit(app.exec())

if __name__ == "__main__":
    main()