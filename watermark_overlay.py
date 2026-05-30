import wx
import ctypes

def set_window_color_key(hwnd, color_rgb):
    gwl_exstyle = -20
    ws_ex_layered = 0x00080000
    lwa_colorkey = 0x00000001
    
    style = ctypes.windll.user32.GetWindowLongW(hwnd, gwl_exstyle)
    ctypes.windll.user32.SetWindowLongW(hwnd, gwl_exstyle, style | ws_ex_layered)
    ctypes.windll.user32.SetLayeredWindowAttributes(hwnd, color_rgb, 0, lwa_colorkey)

class WatermarkOverlay(wx.Frame):
    def __init__(self, parent, watermark_image_path):
        super().__init__(parent, style=wx.FRAME_NO_TASKBAR | wx.BORDER_NONE | wx.FRAME_FLOAT_ON_PARENT)
        self.watermark_image_path = watermark_image_path
        self.watermark_image = None
        self.aspect_ratio = 1.0
        self.watermark_rect = wx.Rect(150, 150, 200, 200)
        self.drag_action = None
        self.drag_start_position = None
        self.drag_start_rect = None
        self.resize_threshold = 10
        self.video_display_rect = wx.Rect()

        self.load_watermark_image()
        self.SetBackgroundColour(wx.Colour(255, 0, 255))
        
        self.Bind(wx.EVT_PAINT, self.on_paint)
        self.Bind(wx.EVT_LEFT_DOWN, self.on_left_down)
        self.Bind(wx.EVT_LEFT_UP, self.on_left_up)
        self.Bind(wx.EVT_MOTION, self.on_motion)
        self.Bind(wx.EVT_SIZE, self.on_size)
        self.SetDoubleBuffered(True)
        
        set_window_color_key(self.GetHandle(), 0x00FF00FF)

    def load_watermark_image(self):
        try:
            image = wx.Image(self.watermark_image_path, wx.BITMAP_TYPE_ANY)
            if image.IsOk():
                self.watermark_image = image
                self.aspect_ratio = float(image.GetWidth()) / float(image.GetHeight())
                new_width = 150
                new_height = int(new_width / self.aspect_ratio)
                self.watermark_rect = wx.Rect(150, 150, new_width, new_height)
        except Exception:
            self.watermark_image = None

    def update_watermark_image_path(self, path):
        self.watermark_image_path = path
        self.load_watermark_image()
        self.clamp_watermark_rect()
        self.Refresh()

    def set_video_display_rect(self, rect):
        self.video_display_rect = rect
        self.clamp_watermark_rect()
        self.Refresh()

    def clamp_watermark_rect(self):
        if self.video_display_rect.IsEmpty():
            return
        
        x = max(self.video_display_rect.x, min(self.watermark_rect.x, self.video_display_rect.Right - 10))
        y = max(self.video_display_rect.y, min(self.watermark_rect.y, self.video_display_rect.Bottom - 10))
        
        width = max(10, min(self.watermark_rect.width, self.video_display_rect.Right - x))
        height = max(10, min(self.watermark_rect.height, self.video_display_rect.Bottom - y))
        
        self.watermark_rect = wx.Rect(x, y, width, height)

    def on_size(self, event):
        self.Refresh()
        event.Skip()

    def on_paint(self, event):
        dc = wx.PaintDC(self)
        dc.SetBackground(wx.Brush(wx.Colour(255, 0, 255)))
        dc.Clear()
        
        if self.video_display_rect.IsEmpty():
            return

        if self.watermark_image and self.watermark_image.IsOk():
            scaled_width = max(1, self.watermark_rect.width)
            scaled_height = max(1, self.watermark_rect.height)
            scaled_image = self.watermark_image.Scale(scaled_width, scaled_height, wx.IMAGE_QUALITY_HIGH)
            bitmap = wx.Bitmap(scaled_image)
            dc.DrawBitmap(bitmap, self.watermark_rect.x, self.watermark_rect.y, useMask=True)

        dc.SetPen(wx.Pen(wx.Colour(255, 255, 255), 1, wx.PENSTYLE_SHORT_DASH))
        dc.SetBrush(wx.TRANSPARENT_BRUSH)
        dc.DrawRectangle(self.watermark_rect)

        dc.SetPen(wx.Pen(wx.Colour(255, 255, 255), 1, wx.PENSTYLE_SOLID))
        dc.SetBrush(wx.Brush(wx.Colour(255, 255, 255)))
        
        handles = [
            self.watermark_rect.GetTopLeft(),
            self.watermark_rect.GetTopRight(),
            self.watermark_rect.GetBottomLeft(),
            self.watermark_rect.GetBottomRight(),
            wx.Point(self.watermark_rect.x + self.watermark_rect.width // 2, self.watermark_rect.y),
            wx.Point(self.watermark_rect.x + self.watermark_rect.width // 2, self.watermark_rect.Bottom),
            wx.Point(self.watermark_rect.x, self.watermark_rect.y + self.watermark_rect.height // 2),
            wx.Point(self.watermark_rect.Right, self.watermark_rect.y + self.watermark_rect.height // 2)
        ]
        
        for point in handles:
            dc.DrawRectangle(point.x - 4, point.y - 4, 8, 8)

    def get_drag_action(self, pos):
        if self.video_display_rect.IsEmpty():
            return None

        x, y = pos
        rect = self.watermark_rect
        threshold = self.resize_threshold

        near_left = abs(x - rect.x) <= threshold
        near_right = abs(x - rect.Right) <= threshold
        near_top = abs(y - rect.y) <= threshold
        near_bottom = abs(y - rect.Bottom) <= threshold

        if near_left and near_top:
            return "top_left"
        if near_right and near_top:
            return "top_right"
        if near_left and near_bottom:
            return "bottom_left"
        if near_right and near_bottom:
            return "bottom_right"
        if near_left:
            return "left"
        if near_right:
            return "right"
        if near_top:
            return "top"
        if near_bottom:
            return "bottom"
        if rect.Contains(pos):
            return "move"
        return None

    def update_cursor(self, action):
        if action in ("top_left", "bottom_right"):
            self.SetCursor(wx.Cursor(wx.CURSOR_SIZENWSE))
        elif action in ("top_right", "bottom_left"):
            self.SetCursor(wx.Cursor(wx.CURSOR_SIZENESW))
        elif action in ("left", "right"):
            self.SetCursor(wx.Cursor(wx.CURSOR_SIZEWE))
        elif action in ("top", "bottom"):
            self.SetCursor(wx.Cursor(wx.CURSOR_SIZENS))
        elif action == "move":
            self.SetCursor(wx.Cursor(wx.CURSOR_SIZING))
        else:
            self.SetCursor(wx.Cursor(wx.CURSOR_ARROW))

    def on_left_down(self, event):
        pos = event.GetPosition()
        action = self.get_drag_action(pos)
        if action:
            self.drag_action = action
            self.drag_start_position = pos
            self.drag_start_rect = wx.Rect(self.watermark_rect)
            if not self.HasCapture():
                try:
                    self.CaptureMouse()
                except Exception:
                    pass
        event.Skip()

    def on_left_up(self, event):
        if self.HasCapture():
            try:
                self.ReleaseMouse()
            except Exception:
                pass
        self.drag_action = None
        event.Skip()

    def on_motion(self, event):
        pos = event.GetPosition()
        if not event.Dragging() or not self.drag_action:
            action = self.get_drag_action(pos)
            self.update_cursor(action)
            event.Skip()
            return

        diff_x = pos.x - self.drag_start_position.x
        diff_y = pos.y - self.drag_start_position.y
        rect = wx.Rect(self.drag_start_rect)

        if self.drag_action == "move":
            rect.Offset(diff_x, diff_y)
        else:
            if self.drag_action == "left":
                rect.x += diff_x
                rect.width -= diff_x
            elif self.drag_action == "right":
                rect.width += diff_x
            elif self.drag_action == "top":
                rect.y += diff_y
                rect.height -= diff_y
            elif self.drag_action == "bottom":
                rect.height += diff_y
            elif self.drag_action == "top_left":
                rect.x += diff_x
                rect.width -= diff_x
                rect.y += diff_y
                rect.height -= diff_y
            elif self.drag_action == "top_right":
                rect.width += diff_x
                rect.y += diff_y
                rect.height -= diff_y
            elif self.drag_action == "bottom_left":
                rect.x += diff_x
                rect.width -= diff_x
                rect.height += diff_y
            elif self.drag_action == "bottom_right":
                rect.width += diff_x
                rect.height += diff_y

            if self.drag_action in ("right", "bottom_right", "bottom"):
                rect.height = int(rect.width / self.aspect_ratio)
            elif self.drag_action in ("left", "bottom_left"):
                old_right = self.drag_start_rect.Right
                rect.height = int(rect.width / self.aspect_ratio)
                rect.x = old_right - rect.width
            elif self.drag_action in ("top_right", "top"):
                old_bottom = self.drag_start_rect.Bottom
                rect.height = int(rect.width / self.aspect_ratio)
                rect.y = old_bottom - rect.height
            elif self.drag_action == "top_left":
                old_right = self.drag_start_rect.Right
                old_bottom = self.drag_start_rect.Bottom
                rect.height = int(rect.width / self.aspect_ratio)
                rect.x = old_right - rect.width
                rect.y = old_bottom - rect.height

        self.watermark_rect = rect
        self.clamp_watermark_rect()
        self.Refresh()
        event.Skip()
