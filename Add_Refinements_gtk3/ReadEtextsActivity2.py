#
# ReadEtextsActivity2.py  A version of ReadEtextsActivity with better 
# toolbars and other refinements.
# Copyright (C) 2010  James D. Simmons
# Copyright (C) 2012  Aneesh Dogra <lionaneesh@gmail.com>
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
# You should have received a copy of the GNU General Public License along
# with this program; if not, write to the Free Software Foundation, Inc.,
# 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA

import os
import zipfile
import re
from gi.repository import Gtk
from gi.repository import Gdk
from gi.repository import Pango
from sugar3.activity import activity
from sugar3.graphics import style
from sugar3.graphics.toolbutton import ToolButton
from sugar3.graphics.toolbarbox import ToolbarButton
from sugar3.graphics.toolbarbox import ToolbarBox
from sugar3.activity.widgets import StopButton
from sugar3.activity.widgets import EditToolbar
from sugar3.activity.widgets import ActivityToolbar
from sugar3.activity.widgets import _create_activity_icon
from toolbar import ViewToolbar
from gettext import gettext as _

page=0
PAGE_SIZE = 45
TOOLBAR_READ = 2

class CustomActivityToolbarButton(ToolbarButton):
    """
        Custom Activity Toolbar button, adds the functionality to disable or
        enable the share button.
    """
    def __init__(self, activity, shared=False, **kwargs):
        toolbar = ActivityToolbar(activity, orientation_left=True)

        if not shared:
            toolbar.share.props.visible = False

        ToolbarButton.__init__(self, page=toolbar, **kwargs)

        icon = _create_activity_icon(activity.metadata)
        self.set_icon_widget(icon)
        icon.show()

class ReadEtextsActivity(activity.Activity):
    def __init__(self, handle):
        "The entry point to the Activity"
        global page
        activity.Activity.__init__(self, handle)

        toolbar_box = ToolbarBox()

        activity_button = CustomActivityToolbarButton(self)
        toolbar_box.toolbar.insert(activity_button, 0)
        activity_button.show()

        self.edit_toolbar = EditToolbar()
        self.edit_toolbar.undo.props.visible = False
        self.edit_toolbar.redo.props.visible = False
        self.edit_toolbar.separator.props.visible = False
        self.edit_toolbar.copy.set_sensitive(False)
        self.edit_toolbar.copy.connect('clicked', self.edit_toolbar_copy_cb)
        self.edit_toolbar.paste.props.visible = False
        edit_toolbar_button = ToolbarButton(
            page=self.edit_toolbar,
            icon_name='toolbar-edit')
        self.edit_toolbar.show()
        toolbar_box.toolbar.insert(edit_toolbar_button, -1)
        edit_toolbar_button.show()
        
        view_toolbar = ViewToolbar()
        view_toolbar.connect('go-fullscreen',
                self.view_toolbar_go_fullscreen_cb)
        view_toolbar.zoom_in.connect('clicked', self.zoom_in_cb)
        view_toolbar.zoom_out.connect('clicked', self.zoom_out_cb)
        view_toolbar.show()
        view_toolbar_button = ToolbarButton(
            page=view_toolbar,
            icon_name='toolbar-view')
        toolbar_box.toolbar.insert(view_toolbar_button, -1)
        view_toolbar_button.show()

        self.back = ToolButton('go-previous')
        self.back.set_tooltip(_('Back'))
        self.back.props.sensitive = False
        self.back.connect('clicked', self.go_back_cb)
        toolbar_box.toolbar.insert(self.back, -1)
        self.back.show()

        self.forward = ToolButton('go-next')
        self.forward.set_tooltip(_('Forward'))
        self.forward.props.sensitive = False
        self.forward.connect('clicked', self.go_forward_cb)
        toolbar_box.toolbar.insert(self.forward, -1)
        self.forward.show()

        num_page_item = Gtk.ToolItem()
        self.num_page_entry = Gtk.Entry()
        self.num_page_entry.set_text('0')
        self.num_page_entry.set_alignment(1)
        self.num_page_entry.connect('insert-text',
                               self.__new_num_page_entry_insert_text_cb)
        self.num_page_entry.connect('activate',
                               self.__new_num_page_entry_activate_cb)
        self.num_page_entry.set_width_chars(4)
        num_page_item.add(self.num_page_entry)
        self.num_page_entry.show()
        toolbar_box.toolbar.insert(num_page_item, -1)
        num_page_item.show()

        total_page_item = Gtk.ToolItem()
        self.total_page_label = Gtk.Label()

        self.total_page_label.set_markup("<span foreground='#FFF'" \
                                         " size='14000'></span>")

        self.total_page_label.set_text(' / 0')
        total_page_item.add(self.total_page_label)
        self.total_page_label.show()
        toolbar_box.toolbar.insert(total_page_item, -1)
        total_page_item.show()

        separator = Gtk.SeparatorToolItem()
        separator.props.draw = False
        separator.set_expand(True)
        toolbar_box.toolbar.insert(separator, -1)
        separator.show()

        stop_button = StopButton(self)
        stop_button.props.accelerator = '<Ctrl><Shift>Q'
        toolbar_box.toolbar.insert(stop_button, -1)
        stop_button.show()

        self.set_toolbar_box(toolbar_box)
        toolbar_box.show()

        self.scrolled_window = Gtk.ScrolledWindow()
        self.scrolled_window.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)

        self.textview = Gtk.TextView()
        self.textview.set_editable(False)
        self.textview.set_cursor_visible(False)
        self.textview.set_left_margin(50)
        self.textview.connect("key_press_event", self.keypress_cb)

        self.scrolled_window.add(self.textview)
        self.set_canvas(self.scrolled_window)
        self.textview.show()
        self.scrolled_window.show()
        page = 0
        self.clipboard = Gtk.Clipboard()
        self.textview.grab_focus()
        self.font_desc = Pango.FontDescription("sans %d" % style.zoom(10))
        self.textview.modify_font(self.font_desc)

        buffer = self.textview.get_buffer()
        self.markset_id = buffer.connect("mark-set", self.mark_set_cb)

    def __new_num_page_entry_insert_text_cb(self, entry, text, length, position):
        if not re.match('[0-9]', text):
            entry.emit_stop_by_name('insert-text')
            return True
        return False

    def __new_num_page_entry_activate_cb(self, entry):
        global page
        if entry.props.text:
            new_page = int(entry.props.text) - 1
        else:
            new_page = 0

        if new_page >= self.total_pages:
            new_page = self.total_pages - 1
        elif new_page < 0:
            new_page = 0

        self.current_page = new_page
        self.set_current_page(new_page)
        self.show_page(new_page)
        entry.props.text = str(new_page + 1)
        self.update_nav_buttons()
        page = new_page

    def update_nav_buttons(self):
        current_page = self.current_page
        self.back.props.sensitive = current_page > 0
        self.forward.props.sensitive = \
            current_page < self.total_pages - 1
        
        self.num_page_entry.props.text = str(current_page + 1)
        self.total_page_label.props.label = \
            ' / ' + str(self.total_pages)

    def set_total_pages(self, pages):
        self.total_pages = pages
        
    def set_current_page(self, page):
        self.current_page = page
        self.update_nav_buttons()

    def keypress_cb(self, widget, event):
        "Respond when the user presses one of the arrow keys"
        keyname = Gdk.keyval_name(event.keyval)
        print keyname
        if keyname == 'plus':
            self.font_increase()
            return True
        if keyname == 'minus':
            self.font_decrease()
            return True
        if keyname == 'Page_Up' :
            self.page_previous()
            return True
        if keyname == 'Page_Down':
            self.page_next()
            return True
        if keyname == 'Up' or keyname == 'KP_Up' \
                or keyname == 'KP_Left':
            self.scroll_up()
            return True
        if keyname == 'Down' or keyname == 'KP_Down' \
                or keyname == 'KP_Right':
            self.scroll_down()
            return True
        return False

    def num_page_entry_activate_cb(self, entry):
        global page
        if entry.props.text:
            new_page = int(entry.props.text) - 1
        else:
            new_page = 0

        if new_page >= self.total_pages:
            new_page = self.total_pages - 1
        elif new_page < 0:
            new_page = 0

        self.current_page = new_page
        self.set_current_page(new_page)
        self.show_page(new_page)
        entry.props.text = str(new_page + 1)
        self.update_nav_buttons()
        page = new_page
        
    def go_back_cb(self, button):
        self.page_previous()
    
    def go_forward_cb(self, button):
        self.page_next()

    def page_previous(self):
        global page
        page=page-1
        if page < 0: page=0
        self.set_current_page(page)
        self.show_page(page)
        v_adjustment = self.scrolled_window.get_vadjustment()
        v_adjustment.set_value(v_adjustment.get_upper() - \
                               v_adjustment.get_page_size())

    def page_next(self):
        global page
        page=page+1
        if page >= len(self.page_index): page=0
        self.set_current_page(page)
        self.show_page(page)
        v_adjustment = self.scrolled_window.get_vadjustment()
        v_adjustment.set_value(v_adjustment.get_lower())

    def zoom_in_cb(self,  button):
        self.font_increase()
        
    def zoom_out_cb(self,  button):
        self.font_decrease()

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

    def mark_set_cb(self, textbuffer, iter, textmark):
 
        if textbuffer.get_has_selection():
            begin, end = textbuffer.get_selection_bounds()
            self.edit_toolbar.copy.set_sensitive(True)
        else:
            self.edit_toolbar.copy.set_sensitive(False)

    def edit_toolbar_copy_cb(self, button):
        textbuffer = self.textview.get_buffer()
        begin, end = textbuffer.get_selection_bounds()
        copy_text = textbuffer.get_text(begin, end,  False)
        self.clipboard.set_text(copy_text)

    def view_toolbar_go_fullscreen_cb(self, view_toolbar):
        self.fullscreen()

    def scroll_down(self):
        v_adjustment = self.scrolled_window.get_vadjustment()
        if v_adjustment.get_value() == v_adjustment.get_upper() - \
                v_adjustment.get_page_size():
            self.page_next()
            return
        if v_adjustment.get_value() < v_adjustment.get_upper() - \
                v_adjustment.get_page_size():
            new_value = v_adjustment.get_value() + v_adjustment.step_increment
            if new_value > v_adjustment.get_upper() - v_adjustment.get_page_size():
                new_value = v_adjustment.get_upper() - v_adjustment.get_page_size()
            v_adjustment.set_value(new_value)

    def scroll_up(self):
        v_adjustment = self.scrolled_window.get_vadjustment()
        if v_adjustment.get_value() == v_adjustment.get_lower():
            self.page_previous()
            return
        if v_adjustment.get_value() > v_adjustment.get_lower():
            new_value = v_adjustment.get_value() - \
                v_adjustment.step_increment
            if new_value < v_adjustment.get_lower():
                new_value = v_adjustment.get_lower()
            v_adjustment.set_value(new_value)

    def show_page(self, page_number):
        global PAGE_SIZE, current_word
        position = self.page_index[page_number]
        self.etext_file.seek(position)
        linecount = 0
        label_text = '\n\n\n'
        textbuffer = self.textview.get_buffer()
        while linecount < PAGE_SIZE:
            line = self.etext_file.readline()
            label_text = label_text + unicode(line, 'iso-8859-1')
            linecount = linecount + 1
        label_text = label_text + '\n\n\n'
        textbuffer.set_text(label_text)
        self.textview.set_buffer(textbuffer)

    def save_extracted_file(self, zipfile, filename):
        "Extract the file to a temp directory for viewing"
        filebytes = zipfile.read(filename)
        outfn = self.make_new_filename(filename)
        if (outfn == ''):
            return False
        f = open(os.path.join(self.get_activity_root(), 'tmp',  outfn),  'w')
        try:
            f.write(filebytes)
        finally:
            f.close()

    def get_saved_page_number(self):
        global page
        title = self.metadata.get('title', '')
        if title == ''  or not title[len(title)- 1].isdigit():
            page = 0
        else:
            i = len(title) - 1
            newPage = ''
            while (title[i].isdigit() and i > 0):
                newPage = title[i] + newPage
                i = i - 1
            if title[i] == 'P':
                page = int(newPage) - 1
            else:
                # not a page number; maybe a volume number.
                page = 0
        
    def save_page_number(self):
        global page
        title = self.metadata.get('title', '')
        if title == ''  or not title[len(title)- 1].isdigit():
            title = title + ' P' +  str(page + 1)
        else:
            i = len(title) - 1
            while (title[i].isdigit() and i > 0):
                i = i - 1
            if title[i] == 'P':
                title = title[0:i] + 'P' + str(page + 1)
            else:
                title = title + ' P' + str(page + 1)
        self.metadata['title'] = title

    def read_file(self, filename):
        "Read the Etext file"
        global PAGE_SIZE,  page
        
        if zipfile.is_zipfile(filename):
            self.zf = zipfile.ZipFile(filename, 'r')
            self.book_files = self.zf.namelist()
            self.save_extracted_file(self.zf, self.book_files[0])
            currentFileName = os.path.join(self.get_activity_root(), \
                    'tmp',  self.book_files[0])
        else:
            currentFileName = filename
            
        self.etext_file = open(currentFileName,"r")
        self.page_index = [ 0 ]
        pagecount = 0
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
                pagecount = pagecount + 1
        if filename.endswith(".zip"):
            os.remove(currentFileName)
        self.get_saved_page_number()
        self.show_page(page)
        self.set_total_pages(pagecount + 1)
        self.set_current_page(page)
 
    def make_new_filename(self, filename):
        partition_tuple = filename.rpartition('/')
        return partition_tuple[2]

    def write_file(self, filename):
        "Save meta data for the file."
        self.metadata['activity'] = self.get_bundle_id()
        self.save_page_number()
