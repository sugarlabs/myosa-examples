import gtk
import gst

def gstmessage_cb(bus, message, pipe):
    if message.type in (gst.MESSAGE_EOS, gst.MESSAGE_ERROR):
        pipe.set_state(gst.STATE_NULL)

pipeline = 'espeak text="Hello, World!" ! autoaudiosink'
pipe = gst.parse_launch(pipeline)

bus = pipe.get_bus()
bus.add_signal_watch()
bus.connect('message', gstmessage_cb, pipe)

pipe.set_state(gst.STATE_PLAYING)

gtk.main()
