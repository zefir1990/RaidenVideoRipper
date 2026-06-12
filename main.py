import wx
from editor_window import EditorWindow
from splash_window import SplashWindow

def start_editor():
    window = EditorWindow()
    window.Show()

if __name__ == "__main__":
    app = wx.App()
    splash = SplashWindow(start_editor)
    splash.Show()
    app.MainLoop()
