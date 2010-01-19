# Copyright (C) 2009 Aleksey S. Lim
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

def _message_cb(bus, message, pipe):
    if message.type in (gst.MESSAGE_EOS, gst.MESSAGE_ERROR):
        pipe.set_state(gst.STATE_NULL)
    elif message.type == gst.MESSAGE_ELEMENT and \
            message.structure.get_name() == 'espeak-mark':
        mark = message.structure['mark']
        highlight_cb(int(mark))

def _create_pipe():
    pipe = gst.Pipeline('pipeline')

    source = gst.element_factory_make('espeak', 'source')
    pipe.add(source)

    sink = gst.element_factory_make('autoaudiosink', 'sink')
    pipe.add(sink)
    source.link(sink)

    bus = pipe.get_bus()
    bus.add_signal_watch()
    bus.connect('message', _message_cb, pipe)	

    return (source, pipe)

def _speech(speaker, words):
    speaker[0].props.pitch = pitch
    speaker[0].props.rate = rate
    speaker[0].props.voice = voice[1]
    speaker[0].props.text = words;
    speaker[1].set_state(gst.STATE_PLAYING)

info_speaker = _create_pipe()
play_speaker = _create_pipe()
play_speaker[0].props.track = 2

def voices():
    return info_speaker[0].props.voices

def say(words):
    _speech(info_speaker, words)
    print words

def play(words):
    _speech(play_speaker, words)

def is_stopped():
    for i in play_speaker[1].get_state():
        if isinstance(i, gst.State) and i == gst.STATE_NULL:
            return True
    return False

def stop():
    play_speaker[1].set_state(gst.STATE_NULL)

def is_paused():
    for i in play_speaker[1].get_state():
        if isinstance(i, gst.State) and i == gst.STATE_PAUSED:
            return True
    return False

def pause():
    play_speaker[1].set_state(gst.STATE_PAUSED)

def rate_up():
    global rate
    rate = rate + 10
    if rate > 99:
        rate = 99

def rate_down():
    global rate
    rate = rate - 10
    if rate < -99:
        rate = -99

def pitch_up():
    global pitch
    pitch = pitch + 10
    if pitch > 99:
        pitch = 99

def pitch_down(): 
    global pitch
    pitch = pitch - 10
    if pitch < -99:
        pitch = -99

def prepare_highlighting(label_text):
    i = 0
    j = 0
    word_begin = 0
    word_end = 0
    current_word = 0
    word_tuples = []
    omitted = [' ',  '\n',  u'\r',  '_',  '[', '{', ']', '}', '|',  '<',  '>',  '*',  '+',  '/',  '\\' ]
    omitted_chars = set(omitted)
    while i < len(label_text):
        if label_text[i] not in omitted_chars:
            word_begin = i
            j = i
            while  j < len(label_text) and label_text[j] not in omitted_chars:
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
    marked_up_text  = '<speak> '
    while i < len(word_tuples):
        word_t = word_tuples[i]
        marked_up_text = marked_up_text + '<mark name="' + str(i) + '"/>' + word_t[2]
        i = i + 1
    return marked_up_text + '</speak>'
