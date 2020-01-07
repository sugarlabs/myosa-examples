# speech.py

# Copyright (C) 2010 Aleksey Lim and James D. Simmons
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

import gst

voice = 'default'
pitch = 0

rate = -20
highlight_cb = None

def _create_pipe():
    pipeline = 'espeak name=source ! autoaudiosink'
    pipe = gst.parse_launch(pipeline)

    def stop_cb(bus, message):
        pipe.set_state(gst.STATE_NULL)

    def mark_cb(bus, message):
        if message.get_structure.get_name() == 'espeak-mark':
            mark = message.get_structure['mark']
            highlight_cb(int(mark))

    bus = pipe.get_bus()
    bus.add_signal_watch()
    bus.connect('message::eos', stop_cb)
    bus.connect('message::error', stop_cb)
    bus.connect('message::element', mark_cb)

    return (pipe.get_by_name('source'), pipe)

def _speech(source, pipe, words):
    source.props.pitch = pitch
    source.props.rate = rate
    source.props.voice = voice
    source.props.text = words;
    pipe.set_state(gst.STATE_PLAYING)

info_source, info_pipe = _create_pipe()
play_source, play_pipe = _create_pipe()

# track for marks
play_source.props.track = 2

def voices():
    return info_source.props.voices

def say(words):
    _speech(info_source, info_pipe, words)
    print words

def play(words):
    _speech(play_source, play_pipe, words)

def is_stopped():
    for i in play_pipe.get_state():
        if isinstance(i, gst.State) and i == gst.STATE_NULL:
             return True
    return False

def stop():
    play_pipe.set_state(gst.STATE_NULL)

def is_paused():
    for i in play_pipe.get_state():
        if isinstance(i, gst.State) and i == gst.STATE_PAUSED:
             return True
    return False

def pause():
    play_pipe.set_state(gst.STATE_PAUSED)

def rate_up():
    global rate
    rate = min(99, rate + 10)

def rate_down():
    global rate
    rate = max(-99, rate - 10)

def pitch_up():
    global pitch
    pitch = min(99, pitch + 10)

def pitch_down():
    global pitch
    pitch = max(-99, pitch - 10)

def prepare_highlighting(label_text):
    i = 0
    j = 0
    word_begin = 0
    word_end = 0
    current_word = 0
    word_tuples = []
    omitted = [' ', '\n', u'\r', '_', '[', '{', ']', '}', '|', '<',\
        '>', '*', '+', '/', '\\' ]
    omitted_chars = set(omitted)
    while i < len(label_text):
        if label_text[i] not in omitted_chars:
            word_begin = i
            j = i
            while j < len(label_text) and label_text[j] not in omitted_chars:
                 j = j + 1
                 word_end = j
                 i = j
            word_t = (word_begin, word_end, label_text[word_begin: word_end].strip())
            if word_t[2] != u'\r':
                 word_tuples.append(word_t)
        i = i + 1
    return word_tuples

def add_word_marks(word_tuples):
    "Adds a mark between each word of text."
    i = 0
    marked_up_text = '<speak> '
    while i < len(word_tuples):
        word_t = word_tuples[i]
        marked_up_text = marked_up_text + '<mark name="' + str(i) + '"/>' + word_t[2]
        i = i + 1
    return marked_up_text + '</speak>'
