import wx
import os
import ctypes
from utils import get_asset_path

def set_window_color_key_and_alpha(hwnd, color_rgb, alpha):
    gwl_exstyle = -20
    ws_ex_layered = 0x00080000
    lwa_colorkey = 0x00000001
    lwa_alpha = 0x00000002
    
    style = ctypes.windll.user32.GetWindowLongW(hwnd, gwl_exstyle)
    ctypes.windll.user32.SetWindowLongW(hwnd, gwl_exstyle, style | ws_ex_layered)
    ctypes.windll.user32.SetLayeredWindowAttributes(hwnd, color_rgb, alpha, lwa_colorkey | lwa_alpha)

class SplashWindow(wx.Frame):
    def __init__(self, callback_finished):
        super().__init__(None, style=wx.FRAME_NO_TASKBAR | wx.BORDER_NONE | wx.STAY_ON_TOP)
        self.callback_finished = callback_finished
        
        logo_path = get_asset_path(os.path.join("resources", "images", "logo.png"))
        self.logo_image = wx.Image(logo_path, wx.BITMAP_TYPE_PNG)
        image_width = self.logo_image.GetWidth() // 2
        image_height = self.logo_image.GetHeight() // 2
        
        self.logo_image = self.logo_image.Scale(image_width, image_height, wx.IMAGE_QUALITY_HIGH)
        self.SetSize((image_width, image_height))
        self.Centre()
        
        self.logo_bitmap = wx.Bitmap(self.logo_image)
        self.SetBackgroundColour(wx.Colour(255, 0, 255))
        
        set_window_color_key_and_alpha(self.GetHandle(), 0x00FF00FF, 0)
        
        self.ticks_count = 0
        self.fade_ticks = 66
        self.hold_ticks = 66
        self.total_ticks = 200
        
        self.timer = wx.Timer(self)
        self.Bind(wx.EVT_TIMER, self.on_timer_tick, self.timer)
        self.Bind(wx.EVT_PAINT, self.on_paint)
        
        self.SetDoubleBuffered(True)
        self.timer.Start(15)

    def on_paint(self, event):
        paint_dc = wx.PaintDC(self)
        paint_dc.SetBackground(wx.Brush(wx.Colour(255, 0, 255)))
        paint_dc.Clear()
        paint_dc.DrawBitmap(self.logo_bitmap, 0, 0, useMask=True)

    def on_timer_tick(self, event):
        self.ticks_count += 1
        
        if self.ticks_count <= self.fade_ticks:
            alpha = int(255 * (self.ticks_count / float(self.fade_ticks)))
        elif self.ticks_count <= self.fade_ticks + self.hold_ticks:
            alpha = 255
        elif self.ticks_count <= self.total_ticks:
            remaining_ticks = self.total_ticks - self.ticks_count
            alpha = int(255 * (remaining_ticks / float(self.fade_ticks)))
        else:
            self.timer.Stop()
            self.Close()
            self.callback_finished()
            return
            
        alpha_clamped = max(0, min(255, alpha))
        set_window_color_key_and_alpha(self.GetHandle(), 0x00FF00FF, alpha_clamped)
