import gtk
import gst

text = file(__file__, 'r').read()

def gstmessage_cb(bus, message, pipe):
    if message.type in (gst.MESSAGE_EOS, gst.MESSAGE_ERROR):
        pipe.set_state(gst.STATE_NULL)
    elif message.type == gst.MESSAGE_ELEMENT and \
            message.structure.get_name() == 'espeak-word':
        offset = message.structure['offset']
        len = message.structure['len']
        print text[offset:offset+len]

pipe = gst.Pipeline('pipeline')

src = gst.element_factory_make('espeak', 'src')
src.props.text = text
src.props.track = 1
pipe.add(src)

sink = gst.element_factory_make('autoaudiosink', 'sink')
pipe.add(sink)
src.link(sink)

bus = pipe.get_bus()
bus.add_signal_watch()
bus.connect('message', gstmessage_cb, pipe)

pipe.set_state(gst.STATE_PLAYING)

gtk.main()
