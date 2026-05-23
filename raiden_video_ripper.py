import os
import sys
import subprocess
import threading
import wx
import wx.media
import wx.adv

APPLICATION_NAME = "Raiden Video Ripper"
APPLICATION_VERSION = "1.0.3.0"
COMPANY_NAME = "DemensDeum"
COMPANY_DOMAIN = "demensdeum.com"
OUTPUT_FILE_SUFFIX = "_RaidenVideoRipper_"

class OutputFormat:
    def __init__(self, identifier, title, extension, custom_arguments, is_selected):
        self.identifier = identifier
        self.title = title
        self.extension = extension
        self.custom_arguments = custom_arguments
        self.is_selected = is_selected

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
        start_image_path = os.path.join(script_directory, "resources", "images", "startSliderImage.png")
        playback_image_path = os.path.join(script_directory, "resources", "images", "playbackSliderImage.png")
        end_image_path = os.path.join(script_directory, "resources", "images", "endSliderImage.png")

        try:
            self.start_bitmap = wx.Bitmap(start_image_path, wx.BITMAP_TYPE_PNG)
            self.playback_bitmap = wx.Bitmap(playback_image_path, wx.BITMAP_TYPE_PNG)
            self.end_bitmap = wx.Bitmap(end_image_path, wx.BITMAP_TYPE_PNG)
        except Exception:
            self.start_bitmap = None
            self.playback_bitmap = None
            self.end_bitmap = None

        self.SetMinSize((100, 30))

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
            self.draw_thumb(dc, self.start_value, 'left', self.start_bitmap, wx.Colour(46, 204, 113))
            self.draw_thumb(dc, self.end_value, 'right', self.end_bitmap, wx.Colour(231, 76, 60))
        self.draw_thumb(dc, self.playback_value, 'center', self.playback_bitmap, wx.Colour(0, 122, 217))

class ProgressBarWindow(wx.Dialog):
    def __init__(self, parent, title, status_text):
        super().__init__(parent, title=title, style=wx.DEFAULT_DIALOG_STYLE)
        self.parent = parent
        self.status_label = wx.StaticText(self, label=status_text)
        self.gauge = wx.Gauge(self, range=100, size=(250, 25))
        self.cancel_button = wx.Button(self, label="Cancel")
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

class SuccessWindow(wx.Dialog):
    def __init__(self, parent, file_path):
        super().__init__(parent, title="Success", style=wx.DEFAULT_DIALOG_STYLE)
        self.file_path = file_path

        emoji_font = wx.Font(36, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL)
        emoji_label = wx.StaticText(self, label="✅")
        emoji_label.SetFont(emoji_font)

        message_label = wx.StaticText(self, label="All files were successfully cut.")
        link_button = wx.Button(self, label="Click here to open the location.")
        link_button.Bind(wx.EVT_BUTTON, self.on_link_clicked)

        ok_button = wx.Button(self, label="OK")
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

class VideoProcessingThread(threading.Thread):
    def __init__(self, start_position, end_position, video_path, output_formats, callback_progress, callback_finished):
        super().__init__()
        self.start_position = start_position
        self.end_position = end_position
        self.video_path = video_path
        self.output_formats = output_formats
        self.callback_progress = callback_progress
        self.callback_finished = callback_finished
        self.current_process = None
        self.is_cancelled = False

    def run(self):
        for output_format in self.output_formats:
            if self.is_cancelled:
                break
            output_path = self.video_path + OUTPUT_FILE_SUFFIX + "." + output_format.extension
            arguments = [
                "ffmpeg",
                "-y",
                "-i", self.video_path,
                "-ss", f"{self.start_position}ms",
                "-to", f"{self.end_position}ms"
            ]
            arguments.extend(output_format.custom_arguments)
            arguments.append(output_path)

            success = self.run_ffmpeg(arguments, output_format.title)
            if not success or self.is_cancelled:
                self.callback_finished(False, self.is_cancelled)
                return
        self.callback_finished(True, False)

    def run_ffmpeg(self, arguments, format_title):
        command = [arguments[0], "-progress", "-"] + arguments[1:]
        startup_info = None
        if sys.platform == "win32":
            startup_info = subprocess.STARTUPINFO()
            startup_info.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            startup_info.wShowWindow = subprocess.SW_HIDE

        try:
            self.current_process = subprocess.Popen(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                startupinfo=startup_info,
                text=True,
                bufsize=1
            )
        except Exception:
            return False

        duration_milliseconds = self.end_position - self.start_position
        if duration_milliseconds <= 0:
            duration_milliseconds = 1

        while True:
            line = self.current_process.stdout.readline()
            if not line:
                break
            line = line.strip()
            if line.startswith("out_time_us="):
                try:
                    microseconds = int(line.split("=")[1])
                    milliseconds = microseconds // 1000
                    percentage = int((milliseconds / duration_milliseconds) * 100)
                    percentage = max(0, min(100, percentage))
                    self.callback_progress(format_title, percentage)
                except ValueError:
                    pass
            elif line.startswith("progress=end"):
                break

        self.current_process.wait()
        return self.current_process.returncode == 0

    def cancel(self):
        self.is_cancelled = True
        if self.current_process:
            try:
                self.current_process.terminate()
            except Exception:
                pass

class VideoFileDropTarget(wx.FileDropTarget):
    def __init__(self, callback_open_file):
        super().__init__()
        self.callback_open_file = callback_open_file

    def OnDropFiles(self, coordinate_x, coordinate_y, filenames):
        if filenames:
            self.callback_open_file(filenames[0])
            return True
        return False

class EditorWindow(wx.Frame):
    def __init__(self):
        super().__init__(None, title=APPLICATION_NAME)
        configuration_path = wx.StandardPaths.Get().GetUserConfigDir()
        configuration_file_path = os.path.join(configuration_path, "raiden_video_ripper_config.ini")
        self.config = wx.FileConfig(localFilename=configuration_file_path)
        self.file_path = ""
        self.file_duration = 0
        self.is_processing = False
        self.worker_thread = None
        self.progress_window = None

        self.output_formats = [
            OutputFormat("outputFormatMp4", "Video (mp4)", "mp4", [], True),
            OutputFormat("outputFormatGif", "Animation (Gif)", "gif", [], False),
            OutputFormat("outputFormatWebp", "Animation (webp)", "webp", [], False),
            OutputFormat("outputFormatWebm", "Video (WebM)", "webm", [], False),
            OutputFormat("outputFormatOgv", "Video (ogv)", "ogv", [], False),
            OutputFormat("outputFormatMp3", "Audio (mp3)", "mp3", [], False),
            OutputFormat("outputFormatWav", "Audio (wav)", "wav", [], False),
            OutputFormat("outputFormatOgg", "Audio (ogg)", "ogg", ["-vn", "-c:a", "libvorbis"], False)
        ]

        self.SetBackgroundColour(wx.Colour(30, 30, 30))

        main_panel = wx.Panel(self)
        main_panel.SetBackgroundColour(wx.Colour(30, 30, 30))

        self.media_ctrl = wx.media.MediaCtrl(main_panel, style=wx.SIMPLE_BORDER)
        self.media_ctrl.SetBackgroundColour(wx.Colour(0, 0, 0))

        self.timeline_widget = TimelineWidget(main_panel)
        self.timeline_widget.on_start_changed = self.on_start_changed
        self.timeline_widget.on_end_changed = self.on_end_changed
        self.timeline_widget.on_playback_changed = self.on_playback_changed
        self.timeline_widget.on_start_drag_started = self.on_slider_drag_started
        self.timeline_widget.on_start_drag_finished = self.on_slider_drag_finished
        self.timeline_widget.on_end_drag_started = self.on_slider_drag_started
        self.timeline_widget.on_end_drag_finished = self.on_slider_drag_finished
        self.timeline_widget.on_playback_drag_started = self.on_slider_drag_started
        self.timeline_widget.on_playback_drag_finished = self.on_slider_drag_finished

        controls_panel = wx.Panel(main_panel)
        controls_panel.SetBackgroundColour(wx.Colour(30, 30, 30))

        self.play_button = wx.Button(controls_panel, label="▶", size=(40, 30))
        self.stop_button = wx.Button(controls_panel, label="⏹", size=(40, 30))
        self.volume_slider = wx.Slider(controls_panel, value=100, minValue=0, maxValue=100, size=(80, -1), style=wx.SL_HORIZONTAL)
        self.duration_label = wx.StaticText(controls_panel, label="00:00:00.000 - 00:00:00.000 - 00:00:00.000", style=wx.ALIGN_CENTER)
        self.start_button = wx.Button(controls_panel, label="START", size=(160, 30))

        button_font = wx.Font(11, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD)
        self.play_button.SetFont(button_font)
        self.stop_button.SetFont(button_font)
        self.start_button.SetFont(button_font)

        self.play_button.SetBackgroundColour(wx.Colour(45, 45, 45))
        self.play_button.SetForegroundColour(wx.Colour(255, 255, 255))
        self.stop_button.SetBackgroundColour(wx.Colour(45, 45, 45))
        self.stop_button.SetForegroundColour(wx.Colour(255, 255, 255))
        self.start_button.SetBackgroundColour(wx.Colour(0, 122, 217))
        self.start_button.SetForegroundColour(wx.Colour(255, 255, 255))
        self.duration_label.SetForegroundColour(wx.Colour(220, 220, 220))

        self.play_button.Bind(wx.EVT_BUTTON, self.on_play_toggle)
        self.stop_button.Bind(wx.EVT_BUTTON, self.on_stop)
        self.volume_slider.Bind(wx.EVT_SLIDER, self.on_volume_changed)
        self.start_button.Bind(wx.EVT_BUTTON, self.on_start)

        controls_sizer = wx.BoxSizer(wx.HORIZONTAL)
        controls_sizer.Add(self.play_button, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 5)
        controls_sizer.Add(self.stop_button, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 10)
        controls_sizer.Add(self.volume_slider, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 15)
        controls_sizer.Add(self.duration_label, 1, wx.ALIGN_CENTER_VERTICAL | wx.ALIGN_CENTER_HORIZONTAL)
        controls_sizer.Add(self.start_button, 0, wx.ALIGN_CENTER_VERTICAL | wx.LEFT, 15)
        controls_panel.SetSizer(controls_sizer)

        panel_sizer = wx.BoxSizer(wx.VERTICAL)
        panel_sizer.Add(self.media_ctrl, 1, wx.EXPAND | wx.ALL, 5)
        panel_sizer.Add(self.timeline_widget, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)
        panel_sizer.Add(controls_panel, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)
        main_panel.SetSizer(panel_sizer)

        frame_sizer = wx.BoxSizer(wx.VERTICAL)
        frame_sizer.Add(main_panel, 1, wx.EXPAND)
        self.SetSizer(frame_sizer)

        self.create_menu()

        self.media_ctrl.Bind(wx.media.EVT_MEDIA_LOADED, self.on_media_loaded)

        self.timer = wx.Timer(self)
        self.Bind(wx.EVT_TIMER, self.on_timer_tick, self.timer)
        self.timer.Start(50)

        self.Bind(wx.EVT_CLOSE, self.on_close)
        self.Bind(wx.EVT_KEY_DOWN, self.on_key_down)

        self.SetDropTarget(VideoFileDropTarget(self.open_file))
        self.media_ctrl.SetDropTarget(VideoFileDropTarget(self.open_file))

        saved_volume = self.config.ReadInt("Volume", 100)
        self.volume_slider.SetValue(saved_volume)

        saved_width = self.config.ReadInt("window_width", 800)
        saved_height = self.config.ReadInt("window_height", 600)
        self.SetSize((saved_width, saved_height))

        if len(sys.argv) == 2:
            self.open_file(sys.argv[1])

    def create_menu(self):
        menubar = wx.MenuBar()
        file_menu = wx.Menu()
        open_item = file_menu.Append(wx.ID_OPEN, "&Open...\tCtrl+O")
        exit_item = file_menu.Append(wx.ID_EXIT, "E&xit")
        menubar.Append(file_menu, "&File")
        self.Bind(wx.EVT_MENU, self.on_open, open_item)
        self.Bind(wx.EVT_MENU, self.on_exit, exit_item)

        options_menu = wx.Menu()
        self.preview_item = options_menu.AppendCheckItem(wx.ID_ANY, "Preview")
        preview_checked = self.config.ReadBool("previewCheckboxState", True)
        self.preview_item.Check(preview_checked)
        self.timeline_widget.freeplay_mode = not preview_checked
        self.Bind(wx.EVT_MENU, self.on_preview_toggle, self.preview_item)
        options_menu.AppendSeparator()

        self.format_menu_items = {}
        for output_format in self.output_formats:
            key = f"{output_format.identifier}_isSelected"
            is_checked = self.config.ReadBool(key, output_format.is_selected)
            output_format.is_selected = is_checked
            menu_item = options_menu.AppendCheckItem(wx.ID_ANY, output_format.title)
            menu_item.Check(is_checked)
            self.format_menu_items[menu_item.GetId()] = output_format
            self.Bind(wx.EVT_MENU, self.on_format_toggle, menu_item)
        menubar.Append(options_menu, "&Options")

        about_menu = wx.Menu()
        about_app_item = about_menu.Append(wx.ID_ANY, "About Raiden Video Ripper")
        about_wx_item = about_menu.Append(wx.ID_ANY, "About wxWidgets")
        menubar.Append(about_menu, "&About")
        self.Bind(wx.EVT_MENU, self.on_about_app, about_app_item)
        self.Bind(wx.EVT_MENU, self.on_about_wx, about_wx_item)

        self.SetMenuBar(menubar)

    def on_open(self, event):
        movies_dir = wx.StandardPaths.Get().GetDocumentsDir()
        last_path = self.config.Read("previousWorkingPathKey", movies_dir)
        with wx.FileDialog(self, "Open Video File", defaultDir=last_path,
                           wildcard="Video Files|*.mp4;*.avi;*.mkv;*.mov;*.wmv;*.flv;*.webm;*.ogv|All Files|*.*",
                           style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST) as file_dialog:
            if file_dialog.ShowModal() == wx.ID_OK:
                self.open_file(file_dialog.GetPath())

    def open_file(self, path):
        if self.is_processing:
            if self.progress_window:
                self.progress_window.Raise()
            return
        if path == self.file_path:
            return
        self.file_path = path
        directory = os.path.dirname(path)
        self.config.Write("previousWorkingPathKey", directory)
        self.config.Flush()
        self.file_duration = 0
        if not self.media_ctrl.Load(path):
            wx.MessageBox("Failed to load video file.", "Error", wx.ICON_ERROR)
            self.file_path = ""
            self.update_window_title()

    def on_media_loaded(self, event):
        self.file_duration = self.media_ctrl.Length()
        self.timeline_widget.maximum_value = self.file_duration
        self.timeline_widget.start_value = 0
        self.timeline_widget.playback_value = 0
        self.timeline_widget.end_value = self.file_duration
        self.timeline_widget.Refresh()
        self.media_ctrl.Play()
        volume = self.volume_slider.GetValue()
        self.media_ctrl.SetVolume(volume / 100.0)
        self.update_duration_label()
        self.update_window_title()

    def on_exit(self, event):
        self.Close()

    def on_preview_toggle(self, event):
        is_checked = self.preview_item.IsChecked()
        self.timeline_widget.freeplay_mode = not is_checked
        self.config.WriteBool("previewCheckboxState", is_checked)
        self.config.Flush()
        self.timeline_widget.Refresh()

    def on_format_toggle(self, event):
        item_id = event.GetId()
        menu_item = self.GetMenuBar().FindItemById(item_id)
        output_format = self.format_menu_items[item_id]
        output_format.is_selected = menu_item.IsChecked()
        key = f"{output_format.identifier}_isSelected"
        self.config.WriteBool(key, output_format.is_selected)
        self.config.Flush()

    def on_about_app(self, event):
        info = wx.adv.AboutDialogInfo()
        info.SetName(APPLICATION_NAME)
        info.SetVersion(APPLICATION_VERSION)
        info.SetCopyright("Copyright © 2025 I/E Ilia Prokhorov")
        info.SetWebSite("https://github.com/demensdeum/RaidenVideoRipper")
        info.SetDescription(
            "Raiden Video Ripper is an open-source project designed for video editing and format conversion.\n"
            "It is built using wxPython and allows you to trim and convert videos to various formats."
        )
        wx.adv.AboutBox(info)

    def on_about_wx(self, event):
        wx.MessageBox(f"This application uses wxWidgets version {wx.__version__}.", "About wxWidgets", wx.OK | wx.ICON_INFORMATION)

    def format_milliseconds(self, milliseconds):
        seconds, milliseconds = divmod(milliseconds, 1000)
        minutes, seconds = divmod(seconds, 60)
        hours, minutes = divmod(minutes, 60)
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}.{milliseconds:03d}"

    def update_duration_label(self):
        start_position = self.timeline_widget.start_value
        playback_position = self.timeline_widget.playback_value
        end_position = self.timeline_widget.end_value
        start_time_text = self.format_milliseconds(start_position)
        playback_time_text = self.format_milliseconds(playback_position)
        end_time_text = self.format_milliseconds(end_position)
        label_text = f"{start_time_text} - {playback_time_text} - {end_time_text}"
        self.duration_label.SetLabel(label_text)

    def update_window_title(self):
        application_title = f"{APPLICATION_NAME} {APPLICATION_VERSION}"
        if self.file_path:
            filename = os.path.basename(self.file_path)
            self.SetTitle(f"{filename} - {application_title}")
        else:
            self.SetTitle(application_title)

    def on_start_changed(self, value):
        if self.preview_item.IsChecked():
            self.media_ctrl.Seek(value)
        self.update_duration_label()

    def on_end_changed(self, value):
        if self.preview_item.IsChecked():
            self.media_ctrl.Seek(value)
        self.update_duration_label()

    def on_playback_changed(self, value):
        self.media_ctrl.Seek(value)
        self.update_duration_label()

    def on_slider_drag_started(self):
        self.saved_media_state = self.media_ctrl.GetState()
        if self.saved_media_state == wx.media.MEDIASTATE_PLAYING:
            self.media_ctrl.Pause()

    def on_slider_drag_finished(self):
        if hasattr(self, "saved_media_state") and self.saved_media_state == wx.media.MEDIASTATE_PLAYING:
            self.media_ctrl.Play()

    def on_play_toggle(self, event):
        state = self.media_ctrl.GetState()
        if state == wx.media.MEDIASTATE_PLAYING:
            self.media_ctrl.Pause()
        else:
            self.media_ctrl.Play()

    def on_stop(self, event):
        self.media_ctrl.Stop()

    def on_volume_changed(self, event):
        volume = self.volume_slider.GetValue()
        self.media_ctrl.SetVolume(volume / 100.0)
        self.config.WriteInt("Volume", volume)
        self.config.Flush()

    def on_timer_tick(self, event):
        state = self.media_ctrl.GetState()
        if state == wx.media.MEDIASTATE_PLAYING:
            self.play_button.SetLabel("⏸")
            self.stop_button.Enable(True)
        else:
            self.play_button.SetLabel("▶")
            self.stop_button.Enable(state == wx.media.MEDIASTATE_PAUSED)

        if not self.file_duration or state != wx.media.MEDIASTATE_PLAYING:
            return

        position = self.media_ctrl.Tell()
        start_val = self.timeline_widget.start_value
        end_val = self.timeline_widget.end_value

        if self.preview_item.IsChecked():
            if position > end_val or position < start_val:
                self.media_ctrl.Seek(start_val)
                position = start_val
        elif position >= self.file_duration - 100:
            self.media_ctrl.Seek(0)
            self.media_ctrl.Stop()
            position = 0

        self.timeline_widget.playback_value = position
        self.timeline_widget.Refresh()
        self.update_duration_label()

    def on_key_down(self, event):
        keycode = event.GetKeyCode()
        if keycode == wx.WXK_LEFT:
            self.move_playback_by_offset(-4)
        elif keycode == wx.WXK_RIGHT:
            self.move_playback_by_offset(4)
        else:
            event.Skip()

    def move_playback_by_offset(self, pixel_offset):
        if not self.file_duration:
            return
        current_x = self.timeline_widget.get_thumb_x(self.timeline_widget.playback_value)
        new_x = current_x + pixel_offset
        new_value = self.timeline_widget.x_to_value(new_x)
        self.timeline_widget.playback_value = new_value
        self.timeline_widget.Refresh()
        self.media_ctrl.Seek(new_value)
        self.update_duration_label()

    def on_start(self, event):
        if not self.file_path:
            wx.MessageBox("Open file first!", "WUT!", wx.OK | wx.ICON_INFORMATION)
            return
        selected_formats = [f for f in self.output_formats if f.is_selected]
        if not selected_formats:
            wx.MessageBox("Select output formats checkboxes first!", "WUT!", wx.OK | wx.ICON_INFORMATION)
            return
        start_pos = self.timeline_widget.start_value
        end_pos = self.timeline_widget.end_value
        if end_pos < start_pos:
            return

        self.media_ctrl.Pause()
        self.is_processing = True

        self.progress_window = ProgressBarWindow(self, "Processing", "Preparing...")

        self.worker_thread = VideoProcessingThread(
            start_pos,
            end_pos,
            self.file_path,
            selected_formats,
            self.on_worker_progress,
            self.on_worker_finished
        )
        self.worker_thread.start()
        self.progress_window.ShowModal()

    def on_worker_progress(self, format_title, percentage):
        wx.CallAfter(self.update_progress_ui, format_title, percentage)

    def update_progress_ui(self, format_title, percentage):
        if self.progress_window:
            self.progress_window.set_status(f"Cutting {format_title}... {percentage}%")
            self.progress_window.set_progress(percentage)

    def on_worker_finished(self, success, cancelled):
        wx.CallAfter(self.handle_worker_finished, success, cancelled)

    def handle_worker_finished(self, success, cancelled):
        self.is_processing = False
        if self.progress_window:
            self.progress_window.EndModal(wx.ID_OK if success else wx.ID_CANCEL)
            self.progress_window.Destroy()
            self.progress_window = None

        if success and not cancelled:
            runs = self.config.ReadInt("successfulRunsCount", 0) + 1
            self.config.WriteInt("successfulRunsCount", runs)
            self.config.Flush()

            success_window = SuccessWindow(self, self.file_path)
            success_window.ShowModal()
            success_window.Destroy()
        elif not success and not cancelled:
            wx.MessageBox("Error while cutting!", "Uhh!", wx.OK | wx.ICON_ERROR)

    def cancel_in_progress(self):
        if self.worker_thread:
            self.worker_thread.cancel()

    def on_close(self, event):
        width, height = self.GetSize()
        self.config.WriteInt("window_width", width)
        self.config.WriteInt("window_height", height)
        self.config.Flush()
        self.timer.Stop()
        if self.is_processing:
            self.cancel_in_progress()
        event.Skip()

if __name__ == "__main__":
    app = wx.App()
    window = EditorWindow()
    window.Show()
    app.MainLoop()
