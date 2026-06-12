import wx
import os
import ctypes
from utils import get_asset_path

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
        
        self.ticks_count = 0
        self.fade_ticks = 66
        self.hold_ticks = 66
        self.total_ticks = 200
        
        self.timer = wx.Timer(self)
        self.Bind(wx.EVT_TIMER, self.on_timer_tick, self.timer)
        self.Bind(wx.EVT_PAINT, self.on_paint)
        
        self.update_layered_window_state(0)
        self.timer.Start(15)

    def on_paint(self, event):
        pass

    def update_layered_window_state(self, alpha):
        hwnd = self.GetHandle()
        
        gwl_exstyle = -20
        ws_ex_layered = 0x00080000
        
        style = ctypes.windll.user32.GetWindowLongW(hwnd, gwl_exstyle)
        if not (style & ws_ex_layered):
            ctypes.windll.user32.SetWindowLongW(hwnd, gwl_exstyle, style | ws_ex_layered)

        hdc_screen = ctypes.windll.user32.GetDC(0)
        hdc_mem = ctypes.windll.gdi32.CreateCompatibleDC(hdc_screen)
        
        width = self.logo_bitmap.GetWidth()
        height = self.logo_bitmap.GetHeight()
        
        dib_info = (ctypes.c_long * 10)()
        dib_info[0] = 40
        dib_info[1] = width
        dib_info[2] = -height
        dib_info[3] = 1 | (32 << 16)
        dib_info[4] = 0
        
        bits_ptr = ctypes.c_void_p()
        hbmp_dib = ctypes.windll.gdi32.CreateDIBSection(
            hdc_screen, ctypes.byref(dib_info), 0, ctypes.byref(bits_ptr), None, 0
        )
        
        hbmp_old = ctypes.windll.gdi32.SelectObject(hdc_mem, hbmp_dib)
        
        logo_bitmap_raw = self.logo_bitmap.ConvertToImage()
        raw_alpha = logo_bitmap_raw.GetAlpha()
        raw_rgb = logo_bitmap_raw.GetData()
        
        alpha_bytearray = bytearray(raw_alpha)
        rgb_bytearray = bytearray(raw_rgb)
        
        buffer_len = width * height * 4
        pixel_buffer = (ctypes.c_ubyte * buffer_len)()
        
        for idx in range(width * height):
            rgb_idx = idx * 3
            buf_idx = idx * 4
            a = alpha_bytearray[idx]
            
            val = (a * alpha) // 255
            
            r = (rgb_bytearray[rgb_idx] * val) // 255
            g = (rgb_bytearray[rgb_idx + 1] * val) // 255
            b = (rgb_bytearray[rgb_idx + 2] * val) // 255
            
            pixel_buffer[buf_idx] = b
            pixel_buffer[buf_idx + 1] = g
            pixel_buffer[buf_idx + 2] = r
            pixel_buffer[buf_idx + 3] = val
            
        ctypes.memmove(bits_ptr, pixel_buffer, buffer_len)
        
        class POINT(ctypes.Structure):
            _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]
            
        class SIZE(ctypes.Structure):
            _fields_ = [("cx", ctypes.c_long), ("cy", ctypes.c_long)]
            
        class BLENDFUNCTION(ctypes.Structure):
            _fields_ = [
                ("BlendOp", ctypes.c_byte),
                ("BlendFlags", ctypes.c_byte),
                ("SourceConstantAlpha", ctypes.c_byte),
                ("AlphaFormat", ctypes.c_byte)
            ]
            
        pt_zero = POINT(0, 0)
        
        screen_pos = self.GetScreenPosition()
        pt_dest = POINT(screen_pos.x, screen_pos.y)
        
        wnd_size = SIZE(width, height)
        
        ac_src_alpha = 0x01
        blend = BLENDFUNCTION(0, 0, 255, ac_src_alpha)
        
        ulw_alpha = 0x00000002
        
        ctypes.windll.user32.UpdateLayeredWindow(
            hwnd, hdc_screen, ctypes.byref(pt_dest), ctypes.byref(wnd_size),
            hdc_mem, ctypes.byref(pt_zero), 0, ctypes.byref(blend), ulw_alpha
        )
        
        ctypes.windll.gdi32.SelectObject(hdc_mem, hbmp_old)
        ctypes.windll.gdi32.DeleteObject(hbmp_dib)
        ctypes.windll.gdi32.DeleteDC(hdc_mem)
        ctypes.windll.user32.ReleaseDC(0, hdc_screen)

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
        self.update_layered_window_state(alpha_clamped)
