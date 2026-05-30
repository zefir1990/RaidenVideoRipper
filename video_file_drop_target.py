import wx

class VideoFileDropTarget(wx.FileDropTarget):
    def __init__(self, callback_open_file):
        super().__init__()
        self.callback_open_file = callback_open_file

    def OnDropFiles(self, coordinate_x, coordinate_y, filenames):
        if filenames:
            self.callback_open_file(filenames[0])
            return True
        return False
