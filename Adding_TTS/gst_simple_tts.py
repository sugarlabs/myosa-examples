# gst_simple_tts.py
# Copyright (C) 2010 Aleksey Lim
#
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
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA

import gtk
import gst
import pango

window = gtk.Window()
window.connect('destroy',
        lambda sender: gtk.main_quit())

workspace = gtk.VBox()
window.add(workspace)

# text widget

scrolled = gtk.ScrolledWindow()
workspace.pack_start(scrolled)

text = gtk.TextView()
text.set_left_margin(50)
text.set_right_margin(50)
text.set_wrap_mode(gtk.WRAP_WORD)
scrolled.add(text)

buffer = text.props.buffer
buffer.props.text = file("testtts.txt").read()

tag = buffer.create_tag()
tag.props.weight = pango.WEIGHT_BOLD

# play controls

toolbar = gtk.HBox()
workspace.pack_end(toolbar, False)

play = gtk.Button('Play/Resume')
play.connect('clicked',
        lambda sender: pipe.set_state(gst.STATE_PLAYING))
toolbar.add(play)

pause = gtk.Button('Pause')
pause.connect('clicked',
        lambda sender: pipe.set_state(gst.STATE_PAUSED))
toolbar.add(pause)

stop = gtk.Button('Stop')
stop.connect('clicked',
        lambda sender: pipe.set_state(gst.STATE_NULL))
toolbar.add(stop)

# gst code

pipe = gst.parse_launch('espeak name=src ! autoaudiosink')

src = pipe.get_by_name('src')
src.props.text = buffer.props.text
src.props.track = 1 # track for words

def tts_cb(bus, message):
    if message.get_structure.get_name() != 'espeak-word':
        return

    offset = message.get_structure['offset']
    len = message.get_structure['len']

    buffer.remove_tag(tag, buffer.get_start_iter(), buffer.get_end_iter())
    start = buffer.get_iter_at_offset(offset)
    end = buffer.get_iter_at_offset(offset + len)
    buffer.apply_tag(tag, start, end)

bus = pipe.get_bus()
bus.add_signal_watch()
bus.connect('message::element', tts_cb)

# gtk start

window.show_all()
gtk.main()
