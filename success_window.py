import os
import sys
import subprocess
import wx
from translation import translate_text as _

class SuccessWindow(wx.Dialog):
    def __init__(self, parent, file_path):
        super().__init__(parent, title=_("Success"), style=wx.DEFAULT_DIALOG_STYLE)
        self.file_path = file_path

        emoji_font = wx.Font(36, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL)
        emoji_label = wx.StaticText(self, label="✅")
        emoji_label.SetFont(emoji_font)

        message_label = wx.StaticText(self, label=_("All files were successfully cut."))
        link_button = wx.Button(self, label=_("Click here to open the location."))
        link_button.Bind(wx.EVT_BUTTON, self.on_link_clicked)

        ok_button = wx.Button(self, label=_("OK"))
        ok_button.Bind(wx.EVT_BUTTON, self.on_ok)

        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(emoji_label, 0, wx.ALL | wx.ALIGN_CENTER_HORIZONTAL, 15)
        sizer.Add(message_label, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM | wx.ALIGN_CENTER_HORIZONTAL, 15)
        sizer.Add(link_button, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM | wx.ALIGN_CENTER_HORIZONTAL, 15)
        sizer.Add(ok_button, 0, wx.ALL | wx.ALIGN_CENTER_HORIZONTAL, 15)

        self.SetSizerAndFit(sizer)
        self.CenterOnParent()

        self.SetBackgroundColour(wx.Colour(30, 30, 30))
        message_label.SetForegroundColour(wx.Colour(255, 255, 255))

        link_button.SetBackgroundColour(wx.Colour(30, 30, 30))
        link_button.SetForegroundColour(wx.Colour(0, 122, 217))
        link_button.SetWindowStyleFlag(wx.BORDER_NONE)

        ok_button.SetBackgroundColour(wx.Colour(45, 45, 45))
        ok_button.SetForegroundColour(wx.Colour(255, 255, 255))

    def on_link_clicked(self, event):
        if sys.platform == "win32":
            subprocess.Popen(["explorer.exe", "/select,", os.path.normpath(self.file_path)])
        self.EndModal(wx.ID_OK)

    def on_ok(self, event):
        self.EndModal(wx.ID_OK)
