import os
import wx
from utils import get_asset_path

class TimelineWidget(wx.Panel):
    def __init__(self, parent, maximum_value=10000):
        super().__init__(parent)
        self.maximum_value = maximum_value
        self.start_value = 0
        self.end_value = maximum_value
        self.playback_value = maximum_value // 2
        self.freeplay_mode = False
        self.dragging_slider = None
        self.slider_width = 20
        self.slider_height = 20
        self.line_height = 4

        self.on_start_changed = None
        self.on_end_changed = None
        self.on_playback_changed = None
        self.on_start_drag_started = None
        self.on_start_drag_finished = None
        self.on_end_drag_started = None
        self.on_end_drag_finished = None
        self.on_playback_drag_started = None
        self.on_playback_drag_finished = None

        script_directory = os.path.dirname(os.path.abspath(__file__))
        start_image_path = get_asset_path(os.path.join(script_directory, "resources", "images", "startSliderImage.png"))
        playback_image_path = get_asset_path(os.path.join(script_directory, "resources", "images", "playbackSliderImage.png"))
        end_image_path = get_asset_path(os.path.join(script_directory, "resources", "images", "endSliderImage.png"))

        try:
            self.start_bitmap = wx.Bitmap(start_image_path, wx.BITMAP_TYPE_PNG)
            self.playback_bitmap = wx.Bitmap(playback_image_path, wx.BITMAP_TYPE_PNG)
            self.end_bitmap = wx.Bitmap(end_image_path, wx.BITMAP_TYPE_PNG)
        except Exception:
            self.start_bitmap = None
            self.playback_bitmap = None
            self.end_bitmap = None

        self.SetMinSize((100, 30))
        self.SetBackgroundStyle(wx.BG_STYLE_PAINT)

        self.Bind(wx.EVT_PAINT, self.on_paint)
        self.Bind(wx.EVT_SIZE, self.on_size)
        self.Bind(wx.EVT_LEFT_DOWN, self.on_left_down)
        self.Bind(wx.EVT_LEFT_UP, self.on_left_up)
        self.Bind(wx.EVT_MOTION, self.on_motion)

    def on_size(self, event):
        self.Refresh()
        event.Skip()

    def get_thumb_x(self, value):
        width, height = self.GetSize()
        track_width = width - 2 * self.slider_width
        if self.maximum_value > 0:
            return self.slider_width + int((value / self.maximum_value) * track_width)
        return self.slider_width

    def x_to_value(self, coordinate_x):
        width, height = self.GetSize()
        track_width = width - 2 * self.slider_width
        if track_width <= 0:
            return 0
        ratio = (coordinate_x - self.slider_width) / track_width
        ratio = max(0.0, min(1.0, ratio))
        return int(ratio * self.maximum_value)

    def hit_test_start(self, coordinate_x, coordinate_y):
        thumb_x = self.get_thumb_x(self.start_value)
        y_center = self.GetSize().height // 2
        return (thumb_x - self.slider_width <= coordinate_x <= thumb_x and
                y_center - 15 <= coordinate_y <= y_center + 15)

    def hit_test_playback(self, coordinate_x, coordinate_y):
        thumb_x = self.get_thumb_x(self.playback_value)
        y_center = self.GetSize().height // 2
        return (thumb_x - self.slider_width // 2 <= coordinate_x <= thumb_x + self.slider_width // 2 and
                y_center - 15 <= coordinate_y <= y_center + 15)

    def hit_test_end(self, coordinate_x, coordinate_y):
        thumb_x = self.get_thumb_x(self.end_value)
        y_center = self.GetSize().height // 2
        return (thumb_x <= coordinate_x <= thumb_x + self.slider_width and
                y_center - 15 <= coordinate_y <= y_center + 15)

    def on_left_down(self, event):
        coordinate_x, coordinate_y = event.GetPosition()
        if not self.freeplay_mode and self.hit_test_start(coordinate_x, coordinate_y):
            self.dragging_slider = 'start'
            self.CaptureMouse()
            if self.on_start_drag_started:
                self.on_start_drag_started()
        elif not self.freeplay_mode and self.hit_test_end(coordinate_x, coordinate_y):
            self.dragging_slider = 'end'
            self.CaptureMouse()
            if self.on_end_drag_started:
                self.on_end_drag_started()
        elif self.hit_test_playback(coordinate_x, coordinate_y):
            self.dragging_slider = 'playback'
            self.CaptureMouse()
            if self.on_playback_drag_started:
                self.on_playback_drag_started()

    def on_left_up(self, event):
        if self.dragging_slider:
            if self.dragging_slider == 'start' and self.on_start_drag_finished:
                self.on_start_drag_finished()
            elif self.dragging_slider == 'end' and self.on_end_drag_finished:
                self.on_end_drag_finished()
            elif self.dragging_slider == 'playback' and self.on_playback_drag_finished:
                self.on_playback_drag_finished()
            self.dragging_slider = None
            if self.HasCapture():
                self.ReleaseMouse()
        self.Refresh()

    def on_motion(self, event):
        if self.dragging_slider and event.Dragging() and event.LeftIsDown():
            coordinate_x, coordinate_y = event.GetPosition()
            new_value = self.x_to_value(coordinate_x)
            if self.dragging_slider == 'start':
                if new_value <= self.end_value:
                    self.start_value = new_value
                    if self.on_start_changed:
                        self.on_start_changed(new_value)
            elif self.dragging_slider == 'end':
                if new_value >= self.start_value:
                    self.end_value = new_value
                    if self.on_end_changed:
                        self.on_end_changed(new_value)
            elif self.dragging_slider == 'playback':
                self.playback_value = new_value
                if self.on_playback_changed:
                    self.on_playback_changed(new_value)
            self.Refresh()

    def draw_thumb(self, dc, value, alignment, bitmap, fallback_color):
        width, height = self.GetSize()
        y_center = height // 2
        thumb_x = self.get_thumb_x(value)
        if alignment == 'left':
            left_x = thumb_x - self.slider_width
        elif alignment == 'center':
            left_x = thumb_x - self.slider_width // 2
        else:
            left_x = thumb_x
        top_y = y_center - self.slider_height // 2

        if bitmap and bitmap.IsOk():
            dc.DrawBitmap(bitmap, left_x, top_y, useMask=True)
        else:
            dc.SetPen(wx.Pen(wx.Colour(255, 255, 255), 1, wx.PENSTYLE_SOLID))
            dc.SetBrush(wx.Brush(fallback_color))
            if alignment == 'center':
                dc.DrawCircle(thumb_x, y_center, self.slider_width // 2)
            else:
                dc.DrawRoundedRectangle(left_x, top_y, self.slider_width, self.slider_height, 3)

    def on_paint(self, event):
        dc = wx.AutoBufferedPaintDC(self)
        dc.SetBackground(wx.Brush(wx.Colour(30, 30, 30)))
        dc.Clear()

        width, height = self.GetSize()
        y_center = height // 2

        dc.SetPen(wx.Pen(wx.Colour(214, 214, 214), self.line_height, wx.PENSTYLE_SOLID))
        dc.DrawLine(self.slider_width, y_center, width - self.slider_width, y_center)

        if not self.freeplay_mode:
            start_x = self.get_thumb_x(self.start_value)
            end_x = self.get_thumb_x(self.end_value)
            dc.SetPen(wx.Pen(wx.Colour(0, 122, 217), self.line_height + 2, wx.PENSTYLE_SOLID))
            dc.DrawLine(start_x, y_center, end_x, y_center)

        if not self.freeplay_mode:
            self.draw_thumb(dc, self.start_value, 'left', self.start_bitmap, wx.Colour(255, 255, 255))
            self.draw_thumb(dc, self.end_value, 'right', self.end_bitmap, wx.Colour(255, 255, 255))
        self.draw_thumb(dc, self.playback_value, 'center', self.playback_bitmap, wx.Colour(255, 255, 255))
