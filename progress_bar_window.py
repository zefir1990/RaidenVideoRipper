import wx
from translation import translate_text as _

class ProgressBarWindow(wx.Dialog):
    def __init__(self, parent, title, status_text):
        super().__init__(parent, title=title, style=wx.DEFAULT_DIALOG_STYLE)
        self.parent = parent
        self.status_label = wx.StaticText(self, label=status_text)
        self.gauge = wx.Gauge(self, range=100, size=(250, 25))
        self.cancel_button = wx.Button(self, label=_("Cancel"))
        self.cancel_button.Bind(wx.EVT_BUTTON, self.on_cancel)

        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(self.status_label, 0, wx.ALL | wx.ALIGN_CENTER_HORIZONTAL, 15)
        sizer.Add(self.gauge, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM | wx.EXPAND, 15)
        sizer.Add(self.cancel_button, 0, wx.ALL | wx.ALIGN_CENTER_HORIZONTAL, 10)

        self.SetSizerAndFit(sizer)
        self.CenterOnParent()

        self.SetBackgroundColour(wx.Colour(30, 30, 30))
        self.status_label.SetForegroundColour(wx.Colour(255, 255, 255))
        self.cancel_button.SetBackgroundColour(wx.Colour(45, 45, 45))
        self.cancel_button.SetForegroundColour(wx.Colour(255, 255, 255))

    def set_progress(self, progress):
        self.gauge.SetValue(progress)

    def set_status(self, text):
        self.status_label.SetLabel(text)
        self.Layout()

    def on_cancel(self, event):
        self.parent.cancel_in_progress()
        self.EndModal(wx.ID_CANCEL)
