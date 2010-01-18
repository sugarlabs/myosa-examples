import gtk
import gst

text = '<mark name="mark to Hello"/>Hello, <mark name="mark for World"/>World!'

def gstmessage_cb(bus, message, pipe):
    if message.type in (gst.MESSAGE_EOS, gst.MESSAGE_ERROR):
        pipe.set_state(gst.STATE_NULL)
    elif message.type == gst.MESSAGE_ELEMENT and \
            message.structure.get_name() == 'espeak-mark':
        offset = message.structure['offset']
        mark = message.structure['mark']
        print '%d:%s' % (offset, mark)

pipe = gst.Pipeline('pipeline')

src = gst.element_factory_make('espeak', 'src')
src.props.text = text
src.props.track = 2
src.props.gap = 100
pipe.add(src)

sink = gst.element_factory_make('autoaudiosink', 'sink')
pipe.add(sink)
src.link(sink)

bus = pipe.get_bus()
bus.add_signal_watch()
bus.connect('message', gstmessage_cb, pipe)

pipe.set_state(gst.STATE_PLAYING)

gtk.main()
