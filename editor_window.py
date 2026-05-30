import os
import sys
import vlc
import wx
import wx.adv
from crop_overlay import CropOverlay
from translation import translate_text as _
from constants import APPLICATION_NAME, APPLICATION_VERSION, COMPANY_NAME, COMPANY_DOMAIN, OUTPUT_FILE_SUFFIX
from utils import get_asset_path
from output_format import OutputFormat
from timeline_widget import TimelineWidget
from progress_bar_window import ProgressBarWindow
from success_window import SuccessWindow
from about_dialog import AboutDialog
from video_processing_thread import VideoProcessingThread
from video_file_drop_target import VideoFileDropTarget
from watermark_overlay import WatermarkOverlay

class EditorWindow(wx.Frame):
    def __init__(self):
        super().__init__(None, title=APPLICATION_NAME)
        self.last_play_state = None
        configuration_path = wx.StandardPaths.Get().GetUserConfigDir()
        configuration_file_path = os.path.join(configuration_path, "raiden_video_ripper_config.ini")
        self.config = wx.FileConfig(localFilename=configuration_file_path)
        self.file_path = ""
        self.file_duration = 0
        self.is_processing = False
        self.worker_thread = None
        self.progress_window = None
        self.media_loaded = False

        script_directory = os.path.dirname(os.path.abspath(__file__))
        icon_path = get_asset_path(os.path.join(script_directory, "resources", "icons", "applicationIcon.ico"))
        if os.path.exists(icon_path):
            self.SetIcon(wx.Icon(icon_path, wx.BITMAP_TYPE_ICO))

        play_image_path = get_asset_path(os.path.join(script_directory, "resources", "images", "playIcon.png"))
        pause_image_path = get_asset_path(os.path.join(script_directory, "resources", "images", "pauseIcon.png"))
        stop_image_path = get_asset_path(os.path.join(script_directory, "resources", "images", "stopIcon.png"))

        try:
            self.play_bitmap = wx.Bitmap(play_image_path, wx.BITMAP_TYPE_PNG)
            self.pause_bitmap = wx.Bitmap(pause_image_path, wx.BITMAP_TYPE_PNG)
            self.stop_bitmap = wx.Bitmap(stop_image_path, wx.BITMAP_TYPE_PNG)
        except Exception:
            self.play_bitmap = None
            self.pause_bitmap = None
            self.stop_bitmap = None

        self.vlc_instance = vlc.Instance()
        self.vlc_player = self.vlc_instance.media_player_new()

        self.output_formats = [
            OutputFormat("outputFormatMp4", _("Video (mp4)"), "mp4", [], True),
            OutputFormat("outputFormatGif", _("Animation (Gif)"), "gif", [], False),
            OutputFormat("outputFormatWebp", _("Animation (webp)"), "webp", [], False),
            OutputFormat("outputFormatWebm", _("Video (WebM)"), "webm", [], False),
            OutputFormat("outputFormatOgv", _("Video (ogv)"), "ogv", ["-q:v", "9", "-q:a", "9"], False),
            OutputFormat("outputFormatMp3", _("Audio (mp3)"), "mp3", [], False),
            OutputFormat("outputFormatWav", _("Audio (wav)"), "wav", [], False),
            OutputFormat("outputFormatOgg", _("Audio (ogg)"), "ogg", ["-vn", "-c:a", "libvorbis"], False)
        ]

        self.SetBackgroundColour(wx.Colour(30, 30, 30))

        self.video_panel = wx.Panel(self, style=wx.SIMPLE_BORDER)
        self.video_panel.SetBackgroundColour(wx.Colour(0, 0, 0))
        self.vlc_player.set_hwnd(self.video_panel.GetHandle())
        self.vlc_player.video_set_mouse_input(False)
        self.vlc_player.video_set_key_input(False)
        self.video_panel.Bind(wx.EVT_LEFT_DOWN, self.on_video_panel_left_down)
        self.video_panel.Bind(wx.EVT_LEFT_UP, self.on_video_panel_left_up)
        self.video_panel.Bind(wx.EVT_MOTION, self.on_video_panel_motion)

        bottom_panel = wx.Panel(self)
        bottom_panel.SetBackgroundColour(wx.Colour(30, 30, 30))

        self.timeline_widget = TimelineWidget(bottom_panel)
        self.timeline_widget.on_start_changed = self.on_start_changed
        self.timeline_widget.on_end_changed = self.on_end_changed
        self.timeline_widget.on_playback_changed = self.on_playback_changed
        self.timeline_widget.on_start_drag_started = self.on_slider_drag_started
        self.timeline_widget.on_start_drag_finished = self.on_slider_drag_finished
        self.timeline_widget.on_end_drag_started = self.on_slider_drag_started
        self.timeline_widget.on_end_drag_finished = self.on_slider_drag_finished
        self.timeline_widget.on_playback_drag_started = self.on_slider_drag_started
        self.timeline_widget.on_playback_drag_finished = self.on_slider_drag_finished

        controls_panel = wx.Panel(bottom_panel)
        controls_panel.SetBackgroundColour(wx.Colour(30, 30, 30))

        self.play_button = wx.Button(controls_panel, size=(40, 30))
        self.stop_button = wx.Button(controls_panel, size=(40, 30))

        if self.play_bitmap and self.play_bitmap.IsOk():
            self.play_button.SetBitmap(self.play_bitmap)
        else:
            self.play_button.SetLabel("▶")

        if self.stop_bitmap and self.stop_bitmap.IsOk():
            self.stop_button.SetBitmap(self.stop_bitmap)
        else:
            self.stop_button.SetLabel("⏹")
        self.volume_slider = wx.Slider(controls_panel, value=100, minValue=0, maxValue=100, size=(80, -1), style=wx.SL_HORIZONTAL)
        self.duration_label = wx.StaticText(controls_panel, label="00:00:00.000 - 00:00:00.000 - 00:00:00.000", style=wx.ALIGN_CENTER)
        self.start_button = wx.Button(controls_panel, label=_("START"), size=(160, 30))

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

        bottom_sizer = wx.BoxSizer(wx.VERTICAL)
        bottom_sizer.Add(self.timeline_widget, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, 10)
        bottom_sizer.Add(controls_panel, 0, wx.EXPAND | wx.ALL, 10)
        bottom_panel.SetSizer(bottom_sizer)

        frame_sizer = wx.BoxSizer(wx.VERTICAL)
        frame_sizer.Add(self.video_panel, 1, wx.EXPAND | wx.ALL, 5)
        frame_sizer.Add(bottom_panel, 0, wx.EXPAND)
        self.SetSizer(frame_sizer)

        self.crop_overlay = None
        self.watermark_overlay = None

        self.create_menu()

        self.SetDropTarget(VideoFileDropTarget(self.open_file))
        self.video_panel.SetDropTarget(VideoFileDropTarget(self.open_file))

        vlc_event_manager = self.vlc_player.event_manager()
        vlc_event_manager.event_attach(vlc.EventType.MediaPlayerLengthChanged, self.on_vlc_length_changed)
        vlc_event_manager.event_attach(vlc.EventType.MediaPlayerEndReached, self.on_vlc_end_reached)

        self.timer = wx.Timer(self)
        self.Bind(wx.EVT_TIMER, self.on_timer_tick, self.timer)
        self.timer.Start(50)

        self.Bind(wx.EVT_CLOSE, self.on_close)
        self.Bind(wx.EVT_KEY_DOWN, self.on_key_down)
        self.Bind(wx.EVT_SIZE, self.on_frame_size)
        self.Bind(wx.EVT_MOVE, self.on_frame_move)

        saved_volume = self.config.ReadInt("Volume", 100)
        self.volume_slider.SetValue(saved_volume)
        self.vlc_player.audio_set_volume(saved_volume)

        saved_width = self.config.ReadInt("window_width", 800)
        saved_height = self.config.ReadInt("window_height", 600)
        self.SetSize((saved_width, saved_height))

        crop_checked = self.config.ReadBool("cropCheckboxState", False)
        if crop_checked:
            self.crop_overlay = CropOverlay(self)
            self.crop_overlay.Show()

        self.watermark_path = self.config.Read("watermarkPath", "")
        watermark_checked = self.config.ReadBool("watermarkCheckboxState", False)
        if watermark_checked and self.watermark_path and os.path.exists(self.watermark_path):
            keep_aspect = self.config.ReadBool("watermarkKeepAspectCheckboxState", True)
            self.watermark_overlay = WatermarkOverlay(self, self.watermark_path, keep_aspect=keep_aspect)
            self.watermark_overlay.Show()

        if len(sys.argv) == 2:
            self.open_file(sys.argv[1])

    def create_menu(self):
        menubar = wx.MenuBar()
        file_menu = wx.Menu()
        open_item = file_menu.Append(wx.ID_OPEN, _("&Open...\tCtrl+O"))
        exit_item = file_menu.Append(wx.ID_EXIT, _("E&xit"))
        menubar.Append(file_menu, _("&File"))
        self.Bind(wx.EVT_MENU, self.on_open, open_item)
        self.Bind(wx.EVT_MENU, self.on_exit, exit_item)

        options_menu = wx.Menu()
        self.preview_item = options_menu.AppendCheckItem(wx.ID_ANY, _("Preview"))
        preview_checked = self.config.ReadBool("previewCheckboxState", True)
        self.preview_item.Check(preview_checked)
        self.timeline_widget.freeplay_mode = not preview_checked
        self.Bind(wx.EVT_MENU, self.on_preview_toggle, self.preview_item)
        
        self.stabilize_item = options_menu.AppendCheckItem(wx.ID_ANY, _("Stabilize Video"))
        stabilize_checked = self.config.ReadBool("stabilizeCheckboxState", False)
        self.stabilize_item.Check(stabilize_checked)
        self.Bind(wx.EVT_MENU, self.on_stabilize_toggle, self.stabilize_item)

        self.crop_item = options_menu.AppendCheckItem(wx.ID_ANY, _("Crop"))
        crop_checked = self.config.ReadBool("cropCheckboxState", False)
        self.crop_item.Check(crop_checked)
        self.Bind(wx.EVT_MENU, self.on_crop_toggle, self.crop_item)

        watermark_menu = wx.Menu()
        self.watermark_item = watermark_menu.AppendCheckItem(wx.ID_ANY, _("Enable"))
        watermark_checked = self.config.ReadBool("watermarkCheckboxState", False)
        self.watermark_item.Check(watermark_checked)
        self.Bind(wx.EVT_MENU, self.on_watermark_toggle, self.watermark_item)

        self.select_watermark_item = watermark_menu.Append(wx.ID_ANY, _("Select Image..."))
        self.Bind(wx.EVT_MENU, self.on_select_watermark, self.select_watermark_item)

        self.watermark_keep_aspect_item = watermark_menu.AppendCheckItem(wx.ID_ANY, _("Keep Aspect"))
        keep_aspect_checked = self.config.ReadBool("watermarkKeepAspectCheckboxState", True)
        self.watermark_keep_aspect_item.Check(keep_aspect_checked)
        self.Bind(wx.EVT_MENU, self.on_watermark_keep_aspect_toggle, self.watermark_keep_aspect_item)

        options_menu.AppendSubMenu(watermark_menu, _("Watermark"))

        self.random_name_item = options_menu.AppendCheckItem(wx.ID_ANY, _("Random name for output file"))
        random_name_checked = self.config.ReadBool("randomizeNameCheckboxState", False)
        self.random_name_item.Check(random_name_checked)
        self.Bind(wx.EVT_MENU, self.on_randomize_name_toggle, self.random_name_item)
        
        options_menu.AppendSeparator()

        formats_menu = wx.Menu()
        self.format_menu_items = {}
        for output_format in self.output_formats:
            key = f"{output_format.identifier}_isSelected"
            is_checked = self.config.ReadBool(key, output_format.is_selected)
            output_format.is_selected = is_checked
            menu_item = formats_menu.AppendCheckItem(wx.ID_ANY, output_format.title)
            menu_item.Check(is_checked)
            self.format_menu_items[menu_item.GetId()] = output_format
            self.Bind(wx.EVT_MENU, self.on_format_toggle, menu_item)
        options_menu.AppendSubMenu(formats_menu, _("Formats"))
        menubar.Append(options_menu, _("&Options"))

        about_menu = wx.Menu()
        about_app_item = about_menu.Append(wx.ID_ANY, _("About Raiden Video Ripper"))
        about_wx_item = about_menu.Append(wx.ID_ANY, _("About wxWidgets"))
        menubar.Append(about_menu, _("&About"))
        self.Bind(wx.EVT_MENU, self.on_about_app, about_app_item)
        self.Bind(wx.EVT_MENU, self.on_about_wx, about_wx_item)

        self.SetMenuBar(menubar)

    def on_open(self, event):
        movies_dir = wx.StandardPaths.Get().GetDocumentsDir()
        last_path = self.config.Read("previousWorkingPathKey", movies_dir)
        with wx.FileDialog(self, _("Open Video File"), defaultDir=last_path,
                           wildcard=f"{_('Video Files')}|*.mp4;*.avi;*.mkv;*.mov;*.wmv;*.flv;*.webm;*.ogv|{_('All Files')}|*.*",
                           style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST) as file_dialog:
            if file_dialog.ShowModal() == wx.ID_OK:
                self.open_file(file_dialog.GetPath())

    def open_file(self, path):
        if self.is_processing:
            if self.progress_window:
                self.progress_window.Raise()
            return
        self.file_path = path
        self.file_duration = 0
        self.media_loaded = False
        directory = os.path.dirname(path)
        self.config.Write("previousWorkingPathKey", directory)
        self.config.Flush()
        media = self.vlc_instance.media_new_path(path)
        self.vlc_player.set_media(media)
        self.vlc_player.play()

    def on_vlc_length_changed(self, event):
        wx.CallAfter(self.on_media_loaded)

    def on_vlc_end_reached(self, event):
        wx.CallAfter(self.on_media_finished)

    def on_media_loaded(self):
        if self.media_loaded:
            return
        duration = self.vlc_player.get_length()
        if duration <= 0:
            return
        self.media_loaded = True
        self.file_duration = duration
        self.timeline_widget.maximum_value = self.file_duration
        self.timeline_widget.start_value = 0
        self.timeline_widget.playback_value = 0
        self.timeline_widget.end_value = self.file_duration
        self.timeline_widget.Refresh()
        volume = self.volume_slider.GetValue()
        self.vlc_player.audio_set_volume(volume)
        self.update_duration_label()
        self.update_window_title()
        self.update_overlay_layout()

    def on_media_finished(self):
        self.vlc_player.stop()
        self.timeline_widget.playback_value = 0
        self.timeline_widget.Refresh()
        self.update_duration_label()

    def on_exit(self, event):
        self.Close()

    def on_preview_toggle(self, event):
        is_checked = self.preview_item.IsChecked()
        self.timeline_widget.freeplay_mode = not is_checked
        self.config.WriteBool("previewCheckboxState", is_checked)
        self.config.Flush()
        self.timeline_widget.Refresh()

    def on_stabilize_toggle(self, event):
        is_checked = self.stabilize_item.IsChecked()
        self.config.WriteBool("stabilizeCheckboxState", is_checked)
        self.config.Flush()

    def on_randomize_name_toggle(self, event):
        is_checked = self.random_name_item.IsChecked()
        self.config.WriteBool("randomizeNameCheckboxState", is_checked)
        self.config.Flush()

    def on_crop_toggle(self, event):
        is_checked = self.crop_item.IsChecked()
        self.config.WriteBool("cropCheckboxState", is_checked)
        self.config.Flush()
        if is_checked:
            if not self.crop_overlay:
                self.crop_overlay = CropOverlay(self)
            self.crop_overlay.Show()
            self.update_overlay_layout()
        else:
            if self.crop_overlay:
                self.crop_overlay.Hide()

    def on_watermark_toggle(self, event):
        is_checked = self.watermark_item.IsChecked()
        if is_checked and not self.watermark_path:
            is_checked = self.select_watermark_image_dialog()
            self.watermark_item.Check(is_checked)
        
        self.config.WriteBool("watermarkCheckboxState", is_checked)
        self.config.Flush()
        
        if is_checked:
            if not self.watermark_overlay:
                keep_aspect = self.config.ReadBool("watermarkKeepAspectCheckboxState", True)
                self.watermark_overlay = WatermarkOverlay(self, self.watermark_path, keep_aspect=keep_aspect)
            self.watermark_overlay.Show()
            self.update_overlay_layout()
        else:
            if self.watermark_overlay:
                self.watermark_overlay.Hide()

    def on_watermark_keep_aspect_toggle(self, event):
        is_checked = self.watermark_keep_aspect_item.IsChecked()
        self.config.WriteBool("watermarkKeepAspectCheckboxState", is_checked)
        self.config.Flush()
        if self.watermark_overlay:
            self.watermark_overlay.keep_aspect = is_checked

    def on_select_watermark(self, event):
        self.select_watermark_image_dialog()

    def select_watermark_image_dialog(self):
        last_path = os.path.dirname(self.watermark_path) if self.watermark_path else wx.StandardPaths.Get().GetDocumentsDir()
        with wx.FileDialog(self, _("Select Watermark Image"), defaultDir=last_path,
                           wildcard=f"{_('Image Files')}|*.png;*.jpg;*.jpeg;*.bmp|{_('All Files')}|*.*",
                           style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST) as file_dialog:
            if file_dialog.ShowModal() == wx.ID_OK:
                self.watermark_path = file_dialog.GetPath()
                self.config.Write("watermarkPath", self.watermark_path)
                self.config.Flush()
                if self.watermark_overlay:
                    self.watermark_overlay.update_watermark_image_path(self.watermark_path)
                elif self.watermark_item.IsChecked():
                    keep_aspect = self.config.ReadBool("watermarkKeepAspectCheckboxState", True)
                    self.watermark_overlay = WatermarkOverlay(self, self.watermark_path, keep_aspect=keep_aspect)
                    self.watermark_overlay.Show()
                    self.update_overlay_layout()
                return True
        return False

    def on_frame_size(self, event):
        self.Layout()
        self.update_overlay_layout()
        event.Skip()

    def on_frame_move(self, event):
        self.update_overlay_layout()
        event.Skip()

    def on_video_panel_left_down(self, event):
        pos = event.GetPosition()
        if hasattr(self, "watermark_overlay") and self.watermark_overlay and self.watermark_overlay.IsShown():
            if self.watermark_overlay.get_drag_action(pos):
                self.watermark_overlay.on_left_down(event)
                return
        if hasattr(self, "crop_overlay") and self.crop_overlay and self.crop_overlay.IsShown():
            if self.crop_overlay.get_drag_action(pos):
                self.crop_overlay.on_left_down(event)
                return
        event.Skip()

    def on_video_panel_left_up(self, event):
        if hasattr(self, "watermark_overlay") and self.watermark_overlay and self.watermark_overlay.IsShown():
            if self.watermark_overlay.drag_action:
                self.watermark_overlay.on_left_up(event)
                return
        if hasattr(self, "crop_overlay") and self.crop_overlay and self.crop_overlay.IsShown():
            if self.crop_overlay.drag_action:
                self.crop_overlay.on_left_up(event)
                return
        event.Skip()

    def on_video_panel_motion(self, event):
        pos = event.GetPosition()
        if hasattr(self, "watermark_overlay") and self.watermark_overlay and self.watermark_overlay.IsShown():
            if self.watermark_overlay.drag_action or self.watermark_overlay.get_drag_action(pos):
                self.watermark_overlay.on_motion(event)
                return
        if hasattr(self, "crop_overlay") and self.crop_overlay and self.crop_overlay.IsShown():
            if self.crop_overlay.drag_action or self.crop_overlay.get_drag_action(pos):
                self.crop_overlay.on_motion(event)
                return
        event.Skip()

    def update_overlay_layout(self):
        position = self.video_panel.GetScreenPosition()
        size = self.video_panel.GetSize()
        display_rect = wx.Rect(0, 0, size.width, size.height)
        if self.media_loaded:
            video_size = self.vlc_player.video_get_size(0)
            if video_size and video_size[0] > 0 and video_size[1] > 0:
                video_width, video_height = video_size[0], video_size[1]
                video_aspect = video_width / video_height
                panel_aspect = size.width / size.height
                
                if video_aspect > panel_aspect:
                    display_width = size.width
                    display_height = int(size.width / video_aspect)
                    display_x = 0
                    display_y = (size.height - display_height) // 2
                else:
                    display_height = size.height
                    display_width = int(size.height * video_aspect)
                    display_x = (size.width - display_width) // 2
                    display_y = 0
                    
                display_rect = wx.Rect(display_x, display_y, display_width, display_height)

        if hasattr(self, "crop_overlay") and self.crop_overlay and self.crop_overlay.IsShown():
            self.crop_overlay.SetPosition(position)
            self.crop_overlay.SetSize(size)
            self.crop_overlay.set_video_display_rect(display_rect)
            self.crop_overlay.Raise()

        if hasattr(self, "watermark_overlay") and self.watermark_overlay and self.watermark_overlay.IsShown():
            self.watermark_overlay.SetPosition(position)
            self.watermark_overlay.SetSize(size)
            self.watermark_overlay.set_video_display_rect(display_rect)
            self.watermark_overlay.Raise()

    def on_format_toggle(self, event):
        item_id = event.GetId()
        menu_item = self.GetMenuBar().FindItemById(item_id)
        output_format = self.format_menu_items[item_id]
        output_format.is_selected = menu_item.IsChecked()
        key = f"{output_format.identifier}_isSelected"
        self.config.WriteBool(key, output_format.is_selected)
        self.config.Flush()

    def on_about_app(self, event):
        about_window = AboutDialog(self)
        about_window.ShowModal()
        about_window.Destroy()

    def on_about_wx(self, event):
        wx.MessageBox(_("This application uses wxWidgets version {}.").format(wx.__version__), _("About wxWidgets"), wx.OK | wx.ICON_INFORMATION)

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
            self.vlc_player.set_time(value)
        self.update_duration_label()

    def on_end_changed(self, value):
        if self.preview_item.IsChecked():
            self.vlc_player.set_time(value)
        self.update_duration_label()

    def on_playback_changed(self, value):
        self.vlc_player.set_time(value)
        self.update_duration_label()

    def on_slider_drag_started(self):
        self.saved_media_state = self.vlc_player.get_state()
        if self.saved_media_state == vlc.State.Playing:
            self.vlc_player.set_pause(1)

    def on_slider_drag_finished(self):
        if hasattr(self, "saved_media_state") and self.saved_media_state == vlc.State.Playing:
            self.vlc_player.play()

    def on_play_toggle(self, event):
        state = self.vlc_player.get_state()
        if state == vlc.State.Playing:
            self.vlc_player.set_pause(1)
        else:
            self.vlc_player.play()

    def on_stop(self, event):
        self.vlc_player.stop()
        self.timeline_widget.playback_value = 0
        self.timeline_widget.Refresh()
        self.update_duration_label()

    def on_volume_changed(self, event):
        volume = self.volume_slider.GetValue()
        self.vlc_player.audio_set_volume(volume)
        self.config.WriteInt("Volume", volume)
        self.config.Flush()

    def on_timer_tick(self, event):
        state = self.vlc_player.get_state()
        is_playing = state == vlc.State.Playing
        is_paused = state == vlc.State.Paused

        if is_playing != self.last_play_state:
            self.last_play_state = is_playing

            if is_playing:
                if self.pause_bitmap and self.pause_bitmap.IsOk():
                    self.play_button.SetBitmap(self.pause_bitmap)
                    self.play_button.SetLabel("")
                else:
                    self.play_button.SetLabel("⏸")
            else:
                if self.play_bitmap and self.play_bitmap.IsOk():
                    self.play_button.SetBitmap(self.play_bitmap)
                    self.play_button.SetLabel("")
                else:
                    self.play_button.SetLabel("▶")
            self.stop_button.Enable(is_paused)

        if not self.file_duration or not is_playing:
            return

        position = self.vlc_player.get_time()
        if position < 0:
            return

        start_val = self.timeline_widget.start_value
        end_val = self.timeline_widget.end_value

        if self.preview_item.IsChecked():
            if position > end_val or position < start_val:
                self.vlc_player.set_time(start_val)
                position = start_val
        elif position >= self.file_duration - 100:
            self.vlc_player.set_time(0)
            self.vlc_player.stop()
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
        self.vlc_player.set_time(new_value)
        self.update_duration_label()

    def on_start(self, event):
        if not self.file_path:
            wx.MessageBox(_("Open file first!"), _("WUT!"), wx.OK | wx.ICON_INFORMATION)
            return
        selected_formats = [f for f in self.output_formats if f.is_selected]
        if not selected_formats:
            wx.MessageBox(_("Select output formats checkboxes first!"), _("WUT!"), wx.OK | wx.ICON_INFORMATION)
            return
        start_pos = self.timeline_widget.start_value
        end_pos = self.timeline_widget.end_value
        if end_pos < start_pos:
            return

        self.vlc_player.set_pause(1)
        self.is_processing = True

        self.progress_window = ProgressBarWindow(self, _("Processing"), _("Preparing..."))

        crop_arguments = None
        if self.crop_item.IsChecked() and self.crop_overlay:
            video_size = self.vlc_player.video_get_size(0)
            if video_size and video_size[0] > 0 and video_size[1] > 0:
                video_width, video_height = video_size[0], video_size[1]
                display_rect = self.crop_overlay.video_display_rect
                if not display_rect.IsEmpty():
                    scale_factor = video_width / display_rect.width
                    rel_x = self.crop_overlay.crop_rect.x - display_rect.x
                    rel_y = self.crop_overlay.crop_rect.y - display_rect.y
                    crop_w = self.crop_overlay.crop_rect.width
                    crop_h = self.crop_overlay.crop_rect.height
                    
                    clamped_left = max(0, rel_x)
                    clamped_top = max(0, rel_y)
                    clamped_right = min(display_rect.width, rel_x + crop_w)
                    clamped_bottom = min(display_rect.height, rel_y + crop_h)
                    
                    video_crop_x = int(clamped_left * scale_factor)
                    video_crop_y = int(clamped_top * scale_factor)
                    video_crop_w = int((clamped_right - clamped_left) * scale_factor)
                    video_crop_h = int((clamped_bottom - clamped_top) * scale_factor)
                    
                    crop_arguments = [video_crop_w, video_crop_h, video_crop_x, video_crop_y]

        watermark_arguments = None
        if self.watermark_item.IsChecked():
            if not self.watermark_path or not os.path.exists(self.watermark_path):
                wx.MessageBox(_("Error: Select watermark image first!"), _("WUT!"), wx.OK | wx.ICON_ERROR)
                return
            if self.watermark_overlay:
                video_size = self.vlc_player.video_get_size(0)
                if video_size and video_size[0] > 0 and video_size[1] > 0:
                    video_width, video_height = video_size[0], video_size[1]
                    display_rect = self.watermark_overlay.video_display_rect
                    if not display_rect.IsEmpty():
                        scale_factor = video_width / display_rect.width
                        rel_x = self.watermark_overlay.watermark_rect.x - display_rect.x
                        rel_y = self.watermark_overlay.watermark_rect.y - display_rect.y
                        watermark_w = self.watermark_overlay.watermark_rect.width
                        watermark_h = self.watermark_overlay.watermark_rect.height
                        
                        video_watermark_x = int(rel_x * scale_factor)
                        video_watermark_y = int(rel_y * scale_factor)
                        video_watermark_w = int(watermark_w * scale_factor)
                        video_watermark_h = int(watermark_h * scale_factor)

                        if crop_arguments:
                            crop_w, crop_h, crop_x, crop_y = crop_arguments
                            video_watermark_x = video_watermark_x - crop_x
                            video_watermark_y = video_watermark_y - crop_y

                        watermark_arguments = [self.watermark_path, video_watermark_w, video_watermark_h, video_watermark_x, video_watermark_y]

        self.worker_thread = VideoProcessingThread(
            start_pos,
            end_pos,
            self.file_path,
            selected_formats,
            self.on_worker_progress,
            self.on_worker_finished,
            self.stabilize_item.IsChecked(),
            crop_arguments=crop_arguments,
            watermark_arguments=watermark_arguments,
            use_random_name=self.random_name_item.IsChecked()
        )
        self.worker_thread.start()
        self.progress_window.ShowModal()

    def on_worker_progress(self, format_title, percentage):
        wx.CallAfter(self.update_progress_ui, format_title, percentage)

    def update_progress_ui(self, format_title, percentage):
        if self.progress_window:
            self.progress_window.set_status(f"{_('Cutting')} {format_title}... {percentage}%")
            self.progress_window.set_progress(percentage)

    def on_worker_finished(self, success, cancelled):
        wx.CallAfter(self.handle_worker_finished, success, cancelled)

    def handle_worker_finished(self, success, cancelled):
        self.is_processing = False
        if self.progress_window:
            if self.progress_window.IsModal():
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
            wx.MessageBox(_("Error while cutting!"), _("Uhh!"), wx.OK | wx.ICON_ERROR)

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
        self.vlc_player.stop()
        self.vlc_player.release()
        self.vlc_instance.release()
        event.Skip()
