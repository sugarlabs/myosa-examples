#! /usr/bin/env python

# Copyright (C) 2010 James D. Simmons
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

import sys
import os
import zipfile
import pygtk
import gtk
import getopt
import pango
import gobject
import time
import speech

speech_supported = True

try:
    import gst
    gst.element_factory_make('espeak')
    print 'speech supported!'
except Exception, e:
    speech_supported = False
    print 'speech not supported!'

page=0
PAGE_SIZE = 45

class ReadEtextsActivity():
    def __init__(self):
        "The entry point to the Activity"
        speech.highlight_cb = self.highlight_next_word
        # print speech.voices()
    
    def highlight_next_word(self, word_count):
        if word_count < len(self.word_tuples):
            word_tuple = self.word_tuples[word_count]
            textbuffer = self.textview.get_buffer()
            tag = textbuffer.create_tag()
            tag.set_property('weight', pango.WEIGHT_BOLD)
            tag.set_property( 'foreground', "white")
            tag.set_property( 'background', "black")
            iterStart = textbuffer.get_iter_at_offset(word_tuple[0])
            iterEnd = textbuffer.get_iter_at_offset(word_tuple[1])
            bounds = textbuffer.get_bounds()
            textbuffer.remove_all_tags(bounds[0], bounds[1])
            textbuffer.apply_tag(tag, iterStart, iterEnd)
            v_adjustment = self.scrolled_window.get_vadjustment()
            max = v_adjustment.upper - v_adjustment.page_size
            max = max * word_count
            max = max / len(self.word_tuples)
            v_adjustment.value = max
        return True
    
    def keypress_cb(self, widget, event):
        "Respond when the user presses one of the arrow keys"
        global done
        global speech_supported
        keyname = gtk.gdk.keyval_name(event.keyval)
        if keyname == 'KP_End' and speech_supported:
            if speech.is_paused() or speech.is_stopped():
                speech.play(self.words_on_page)
            else:
                speech.pause()
            return True
        if keyname == 'plus':
            self.font_increase()
            return True
        if keyname == 'minus':
            self.font_decrease()
            return True
        if speech_supported and speech.is_stopped() == False and speech.is_paused == False:
            # If speech is in progress, ignore other keys.
            return True
        if keyname == '7':
            speech.pitch_down()
            speech.say('Pitch Adjusted')
            return True
        if keyname == '8':
            speech.pitch_up()
            speech.say('Pitch Adjusted')
            return True
        if keyname == '9':
            speech.rate_down()
            speech.say('Rate Adjusted')
            return True
        if keyname == '0':
            speech.rate_up()
            speech.say('Rate Adjusted')
            return True
        if keyname == 'KP_Right':
            self.page_next()
            return True
        if keyname == 'Page_Up' or keyname == 'KP_Up':
            self.page_previous()
            return True
        if keyname == 'KP_Left':
            self.page_previous()
            return True
        if keyname == 'Page_Down' or keyname == 'KP_Down':
            self.page_next()
            return True
        if keyname == 'Up':
            self.scroll_up()
            return True
        if keyname == 'Down':
            self.scroll_down()
            return True
        return False

    def page_previous(self):
        global page
        page=page-1
        if page < 0: page=0
        self.show_page(page)
        v_adjustment = self.scrolled_window.get_vadjustment()
        v_adjustment.value = v_adjustment.upper - v_adjustment.page_size

    def page_next(self):
        global page
        page=page+1
        if page >= len(self.page_index): page=0
        self.show_page(page)
        v_adjustment = self.scrolled_window.get_vadjustment()
        v_adjustment.value = v_adjustment.lower

    def font_decrease(self):
        font_size = self.font_desc.get_size() / 1024
        font_size = font_size - 1
        if font_size < 1:
            font_size = 1
        self.font_desc.set_size(font_size * 1024)
        self.textview.modify_font(self.font_desc)

    def font_increase(self):
        font_size = self.font_desc.get_size() / 1024
        font_size = font_size + 1
        self.font_desc.set_size(font_size * 1024)
        self.textview.modify_font(self.font_desc)

    def scroll_down(self):
        v_adjustment = self.scrolled_window.get_vadjustment()
        if v_adjustment.value == v_adjustment.upper - v_adjustment.page_size:
            self.page_next()
            return
        if v_adjustment.value < v_adjustment.upper - v_adjustment.page_size:
            new_value = v_adjustment.value + v_adjustment.step_increment
            if new_value > v_adjustment.upper - v_adjustment.page_size:
                new_value = v_adjustment.upper - v_adjustment.page_size
            v_adjustment.value = new_value

    def scroll_up(self):
        v_adjustment = self.scrolled_window.get_vadjustment()
        if v_adjustment.value == v_adjustment.lower:
            self.page_previous()
            return
        if v_adjustment.value > v_adjustment.lower:
            new_value = v_adjustment.value - v_adjustment.step_increment
            if new_value < v_adjustment.lower:
                new_value = v_adjustment.lower
            v_adjustment.value = new_value

    def show_page(self, page_number):
        global PAGE_SIZE, current_word
        position = self.page_index[page_number]
        self.etext_file.seek(position)
        linecount = 0
        label_text = ''
        textbuffer = self.textview.get_buffer()
        while linecount < PAGE_SIZE:
            line = self.etext_file.readline()
            label_text = label_text + unicode(line, 'iso-8859-1')
            linecount = linecount + 1
        textbuffer.set_text(label_text)
        self.textview.set_buffer(textbuffer)
        self.word_tuples = speech.prepare_highlighting(label_text)
        self.words_on_page = speech.add_word_marks(self.word_tuples)

    def save_extracted_file(self, zipfile, filename):
        "Extract the file to a temp directory for viewing"
        filebytes = zipfile.read(filename)
        f = open("/tmp/" + filename, 'w')
        try:
            f.write(filebytes)
        finally:
            f.close

    def read_file(self, filename):
        "Read the Etext file"
        global PAGE_SIZE
        
        if zipfile.is_zipfile(filename):
            self.zf = zipfile.ZipFile(filename, 'r')
            self.book_files = self.zf.namelist()
            self.save_extracted_file(self.zf, self.book_files[0])
            currentFileName = "/tmp/" + self.book_files[0]
        else:
            currentFileName = filename
            
        self.etext_file = open(currentFileName,"r")
        self.page_index = [ 0 ]
        linecount = 0
        while self.etext_file:
            line = self.etext_file.readline()
            if not line:
                break
            linecount = linecount + 1
            if linecount >= PAGE_SIZE:
                position = self.etext_file.tell()
                self.page_index.append(position)
                linecount = 0
        if filename.endswith(".zip"):
            os.remove(currentFileName)

    def delete_cb(self, widget, event, data=None):
        speech.stop()
        return False
    
    def destroy_cb(self, widget, data=None):
        speech.stop()
        gtk.main_quit()

    def main(self, file_path):
        self.window = gtk.Window(gtk.WINDOW_TOPLEVEL)
        self.window.connect("delete_event", self.delete_cb)
        self.window.connect("destroy", self.destroy_cb)
        self.window.set_title("Read Etexts Activity")
        self.window.set_size_request(800, 600)
        self.window.set_border_width(0)
        self.read_file(file_path)
        self.scrolled_window = gtk.ScrolledWindow(hadjustment=None, vadjustment=None)
        self.textview = gtk.TextView()
        self.textview.set_editable(False)
        self.textview.set_left_margin(50)
        self.textview.set_cursor_visible(False)
        self.textview.connect("key_press_event", self.keypress_cb)
        buffer = self.textview.get_buffer()
        self.font_desc = pango.FontDescription("sans 12")
        font_size = self.font_desc.get_size()
        self.textview.modify_font(self.font_desc)
        self.show_page(0)
        self.scrolled_window.add(self.textview)
        self.window.add(self.scrolled_window)
        self.textview.show()
        self.scrolled_window.show()
        v_adjustment = self.scrolled_window.get_vadjustment()
        self.window.show()
        gtk.main()
      
if __name__ == "__main__":
    try:
        opts, args = getopt.getopt(sys.argv[1:], "")
        ReadEtextsActivity().main(args[0])
    except getopt.error, msg:
        print msg
        print "This program has no options"
        sys.exit(2)
