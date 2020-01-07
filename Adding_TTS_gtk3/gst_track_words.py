# gst_track_words.py
# Sample code for using the gstreamer espeak plugin.
# Copyright (C) 2010 Aleksey Lim
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along
# with this program; if not, write to the Free Software Foundation, Inc.,
# 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA
#

from gi.repository import Gtk
import gst

text = file(__file__, 'r').read()

def gstmessage_cb(bus, message, pipe):
    if message.type in (gst.MESSAGE_EOS, gst.MESSAGE_ERROR):
        pipe.set_state(gst.STATE_NULL)
    elif message.type == gst.MESSAGE_ELEMENT and \
            message.get_structure.get_name() == 'espeak-word':
        offset = message.get_structure['offset']
        len = message.get_structure['len']
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

Gtk.main()
