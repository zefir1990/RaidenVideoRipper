import locale
import ctypes

TRANSLATIONS = {
    "ru": {
        "&Open...\tCtrl+O": "&Открыть...\tCtrl+O",
        "E&xit": "Вы&ход",
        "&File": "&Файл",
        "Preview": "Предосмотр",
        "Stabilize Video": "Стабилизация видео",
        "Crop": "Обрезка кадра",
        "Random name for output file": "Случайное имя для выходного файла",
        "&Options": "&Опции",
        "About Raiden Video Ripper": "О Raiden Video Ripper",
        "About wxWidgets": "О wxWidgets",
        "&About": "&Справка",
        "Open Video File": "Открыть видеофайл",
        "Video Files": "Видеофайлы",
        "All Files": "Все файлы",
        "Cancel": "Отмена",
        "Success": "Успех",
        "All files were successfully cut.": "Все файлы были успешно обработаны.",
        "Click here to open the location.": "Нажмите для открытия папки.",
        "OK": "ОК",
        "Open file first!": "Откройте файл сначала!",
        "WUT!": "Что??!",
        "Select output formats checkboxes first!": "Выберите выходные форматы в опциях!",
        "Processing": "Обработка",
        "Preparing...": "Подготовка...",
        "Error while cutting!": "Ошибка во время обрезки!",
        "Uhh!": "Ой!",
        "START": "НАЧАТЬ",
        "Video (mp4)": "Видео (mp4)",
        "Animation (Gif)": "Анимация (Gif)",
        "Animation (webp)": "Анимация (webp)",
        "Video (WebM)": "Видео (WebM)",
        "Video (ogv)": "Видео (ogv)",
        "Audio (mp3)": "Аудио (mp3)",
        "Audio (wav)": "Аудио (wav)",
        "Audio (ogg)": "Аудио (ogg)",
        "Cutting": "Монтаж",
        "This application uses wxWidgets version {}.": "Это приложение использует wxWidgets версии {}.",
        "Raiden Video Ripper is an open-source project designed for video editing and format conversion.\nIt is built using FFmpeg, VLC, wxPython and allows you to trim and convert videos to various formats.":
            "Raiden Video Ripper - это проект с открытым исходным кодом, разработанный для видеомонтажа и конвертации форматов.\nОн создан с использованием FFmpeg, VLC, wxPython и позволяет обрезать и конвертировать видео в различные форматы.",
        "Watermark": "Водяной знак",
        "Select Watermark Image...": "Выбрать изображение водяного знака...",
        "Select Watermark Image": "Выбрать изображение водяного знака",
        "Image Files": "Файлы изображений",
        "Error: Select watermark image first!": "Ошибка: Выберите изображение водяного знака сначала!",
        "Watermark keep aspect": "Сохранять пропорции водяного знака",
        "Enable Watermark": "Включить водяной знак",
        "Output Formats": "Форматы вывода",
        "Enable": "Включить",
        "Select Image...": "Выбрать изображение...",
        "Keep Aspect": "Сохранять пропорции",
        "Formats": "Форматы",
    }
}

class Translator:
    def __init__(self):
        self.language = self.detect_language()

    def detect_language(self):
        try:
            language_id = ctypes.windll.kernel32.GetUserDefaultUILanguage()
            if language_id == 1049:
                return "ru"
        except Exception:
            pass
        try:
            default_locale = locale.getdefaultlocale()[0]
            if default_locale and default_locale.startswith("ru"):
                return "ru"
        except Exception:
            pass
        return "en"

    def translate(self, text):
        if self.language in TRANSLATIONS:
            return TRANSLATIONS[self.language].get(text, text)
        return text

translator = Translator()

def translate_text(text):
    return translator.translate(text)
