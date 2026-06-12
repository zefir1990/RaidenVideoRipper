import os
import wx
from editor_window import EditorWindow
from splash_window import SplashWindow

def start_editor():
    window = EditorWindow()
    window.Show()

if __name__ == "__main__":
    app = wx.App()
    
    configuration_path = wx.StandardPaths.Get().GetUserConfigDir()
    configuration_file_path = os.path.join(configuration_path, "raiden_video_ripper_config.ini")
    config = wx.FileConfig(localFilename=configuration_file_path)
    
    splash_shown = config.ReadBool("splashScreenShown", False)
    if splash_shown:
        start_editor()
    else:
        config.WriteBool("splashScreenShown", True)
        config.Flush()
        splash = SplashWindow(start_editor)
        splash.Show()
        
    app.MainLoop()
