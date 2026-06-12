import os
import wx

def clear_persistent_memory():
    app = wx.App()
    configuration_path = wx.StandardPaths.Get().GetUserConfigDir()
    configuration_file_path = os.path.join(configuration_path, "raiden_video_ripper_config.ini")
    if os.path.exists(configuration_file_path):
        os.remove(configuration_file_path)

if __name__ == "__main__":
    clear_persistent_memory()
