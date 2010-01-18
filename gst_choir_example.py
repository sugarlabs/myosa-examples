import gtk
import gst
import random
from gettext import gettext as _

def gstmessage_cb(bus, message, pipe):
    if message.type in (gst.MESSAGE_EOS, gst.MESSAGE_ERROR):
        pipe.set_state(gst.STATE_NULL)

def make_pipe():
    pipeline = 'espeak name=src ! autoaudiosink'
    pipe = gst.parse_launch(pipeline)

    src = pipe.get_by_name('src')
    src.props.text = _('Hello, World!')
    src.props.pitch = random.randint(-100, 100)
    src.props.rate = random.randint(-100, 100)

    voices = src.props.voices
    voice = voices[random.randint(0, len(voices)-1)]
    src.props.voice = voice[0]

    bus = pipe.get_bus()
    bus.add_signal_watch()
    bus.connect('message', gstmessage_cb, pipe)

    pipe.set_state(gst.STATE_PLAYING)

for i in range(10):
    make_pipe()

gtk.main()
