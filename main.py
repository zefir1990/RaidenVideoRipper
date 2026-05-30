import wx
from editor_window import EditorWindow

if __name__ == "__main__":
    app = wx.App()
    window = EditorWindow()
    window.Show()
    app.MainLoop()
