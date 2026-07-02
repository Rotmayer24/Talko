from kivy.config import Config
Config.set('graphics', 'width', '375')
Config.set('graphics', 'height', '400')
Config.set('graphics', 'resizable', '0')

from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.textinput import TextInput
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.widget import Widget
from kivy.graphics import Color, RoundedRectangle
from kivy.core.window import Window
from kivy.clock import Clock
import webview
import os
import sys

TN_BG      = (0.063, 0.067, 0.122, 1)
TN_SURFACE = (0.110, 0.118, 0.196, 1)
TN_BORDER  = (0.224, 0.235, 0.388, 1)
TN_FG      = (0.784, 0.804, 0.902, 1)
TN_CYAN    = (0.122, 0.812, 0.784, 1)
TN_PURPLE  = (0.612, 0.451, 0.996, 1)

Window.clearcolor = TN_BG[:3] + (1,)


class GlowButton(Button):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.background_normal = ''
        self.background_color  = (0, 0, 0, 0)
        self.color             = TN_FG
        self.font_size         = '13sp'
        self.bold              = True
        self.bind(pos=self._redraw, size=self._redraw)

    def _redraw(self, *_):
        self.canvas.before.clear()
        with self.canvas.before:
            Color(TN_PURPLE[0], TN_PURPLE[1], TN_PURPLE[2], 0.25)
            RoundedRectangle(pos=(self.x - 3, self.y - 3),
                             size=(self.width + 6, self.height + 6),
                             radius=[12])
            Color(*TN_PURPLE)
            RoundedRectangle(pos=self.pos, size=self.size, radius=[9])


class SurfaceBox(BoxLayout):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.bind(pos=self._redraw, size=self._redraw)

    def _redraw(self, *_):
        self.canvas.before.clear()
        with self.canvas.before:
            Color(*TN_BORDER)
            RoundedRectangle(pos=(self.x - 1, self.y - 1),
                             size=(self.width + 2, self.height + 2),
                             radius=[13])
            Color(*TN_SURFACE)
            RoundedRectangle(pos=self.pos, size=self.size, radius=[12])


def launch_webview(url):
    data_dir = os.path.join(os.path.expanduser('~'), '.talko', 'webview')
    os.makedirs(data_dir, exist_ok=True)
    webview.create_window('Talko', url, width=1200, height=800)
    webview.start(storage_path=data_dir)
    sys.exit(0)


class TalkoApp(App):

    def build(self):
        self._target_url = None

        root = BoxLayout(orientation='vertical', padding=[24, 32, 24, 28], spacing=0)

        header = BoxLayout(orientation='vertical', size_hint=(1, None), height=90)
        title = Label(
            text='[b]Talko[/b]',
            markup=True,
            font_size='28sp',
            color=TN_FG,
            halign='left',
            valign='middle',
            size_hint=(1, None),
            height=42,
        )
        header.add_widget(title)

        card = SurfaceBox(
            orientation='vertical',
            padding=[14, 12, 14, 12],
            spacing=6,
            size_hint=(1, None),
            height=86,
        )
        url_label = Label(
            text='[color=#666990]SERVER URL[/color]',
            markup=True,
            font_size='9sp',
            halign='left',
            size_hint=(1, None),
            height=16,
        )
        url_label.bind(size=lambda w, _: setattr(w, 'text_size', (w.width, None)))

        self.url_input = TextInput(
            text='http://127.0.0.1:8000',
            multiline=False,
            font_size='14sp',
            foreground_color=TN_FG,
            background_color=(0, 0, 0, 0),
            cursor_color=TN_CYAN,
            selection_color=(*TN_PURPLE[:3], 0.35),
            padding=[6, 6, 6, 6],
            size_hint=(1, None),
            height=38,
        )
        card.add_widget(url_label)
        card.add_widget(self.url_input)

        btn = GlowButton(text='Open in WebView', size_hint=(1, None), height=46)
        btn.bind(on_press=self.open_webview)

        root.add_widget(header)
        root.add_widget(Widget(size_hint=(1, None), height=38))
        root.add_widget(card)
        root.add_widget(Widget(size_hint=(1, None), height=20))
        root.add_widget(btn)
        root.add_widget(Widget(size_hint=(1, 1)))

        return root

    def open_webview(self, instance):
        self._target_url = self.url_input.text.strip()
        Window.hide()
        Clock.schedule_once(self._do_stop, 0.1)

    def _do_stop(self, dt):
        self.stop()

    def on_stop(self):
        url = self._target_url
        self._target_url = None
        if url:
            launch_webview(url)


if __name__ == '__main__':
    TalkoApp().run()
