"""
    TakeNote
    Copyright Matt Rasmussen 2008
    
    Editor widget in main window
"""



# python imports
import sys, os

# pygtk imports
import pygtk
pygtk.require('2.0')
from gtk import gdk
import gtk.glade
import gobject

# takenote imports
import takenote
from takenote.notebook import \
     NoteBookError, \
     NoteBookVersionError
from takenote import notebook as notebooklib
from takenote.gui import richtext
from takenote.gui.richtext import RichTextView, RichTextIO, RichTextError
from takenote.gui import \
     get_resource, \
     get_resource_image, \
     get_resource_pixbuf
from takenote.gui.font_selector import FontSelector
from takenote.gui.colortool import FgColorTool, BgColorTool
from takenote.gui.richtext.richtext_tags import color_tuple_to_string



# TODO: may need to update fonts on page change


class TakeNoteEditor (gtk.VBox):

    def __init__(self):
        gtk.VBox.__init__(self, False, 0)
        self._notebook = None
        
        # state
        self._textview = RichTextView()    # textview
        self._page = None                  # current NoteBookPage
        self._page_scrolls = {}            # remember scroll in each page
        self._queued_scroll = None
        self._textview_io = RichTextIO()

        
        self._sw = gtk.ScrolledWindow()
        self._sw.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
        self._sw.set_shadow_type(gtk.SHADOW_IN)       
        self._sw.add(self._textview)
        self.pack_start(self._sw)
        
        self._textview.connect("font-change", self._on_font_callback)
        self._textview.connect("modified", self._on_modified_callback)
        self._textview.connect("child-activated", self._on_child_activated)
        self._textview.connect("loaded", self._on_loaded)
        self._textview.disable()
        self._sw.get_vadjustment().connect("value-changed", self._on_scroll)
        #self._sw.get_vadjustment().connect("changed", self._on_scroll_setup)
        #self._textviews[-1].connect("show", self._on_scroll_init)
        self.show_all()


    def set_notebook(self, notebook):
        """Set notebook for editor"""

        # remove listener for old notebook
        if self._notebook:
            self._notebook.node_changed.remove(self._on_notebook_changed)

        # set new notebook
        self._notebook = notebook

        if self._notebook:
            # add listener and read default font
            self._notebook.node_changed.add(self._on_notebook_changed)
            self._textview.set_default_font(self._notebook.pref.default_font)
        else:
            # no new notebook, clear the view
            self.clear_view()

    def _on_notebook_changed(self, node, recurse):
        self._textview.set_default_font(self._notebook.pref.default_font)
    
    def _on_font_callback(self, textview, font):
        self.emit("font-change", font)
    
    def _on_modified_callback(self, textview, modified):
        self.emit("modified", self._page, modified)

    def _on_child_activated(self, textview, child):
        self.emit("child-activated", textview, child)

    def _on_loaded(self, textview):
        return
        #if self._queued_scroll is not None:
        #    print "set", self._queued_scroll
        #    self._sw.get_vadjustment().set_value(self._queued_scroll)
        #    #self._queued_scroll = None

                            
    
    def get_textview(self):
        return self._textview
    

    def _on_scroll(self, adjust):
        if self._page:
            self._page_scrolls[self._page] = adjust.get_value()


    def _on_scroll_setup(self, adjust):
        print "setup"


    def _on_scroll_init(self, widget):
        print "init"

        
    def is_focus(self):
        return self._textview.is_focus()


    def clear_view(self):
        self._page = None
        self._textview.disable()
    
    def view_pages(self, pages):
        """View a page"""
        
        # TODO: generalize to multiple pages
        assert len(pages) <= 1

        # save current page before changing pages
        self.save()

        pages = [node for node in pages
                 if node.is_page()]
        
        if len(pages) == 0:            
            self.clear_view()
                
        else:
            page = pages[0]
            self._page = page
            self._textview.enable()

            try:
                self._queued_scroll = self._page_scrolls.get(
                    self._page, None)
                #print self._queued_scroll

                #print "loading"
                self._textview_io.load(self._textview,
                                       self._textview.get_buffer(),
                                       self._page.get_data_file())
                #print "done loading"

            except RichTextError, e:
                self.clear_view()                
                self.emit("error", e.msg, e)
            except Exception, e:
                self.clear_view()
                self.emit("error", "Unknown error", e)
                
    
    def save(self):
        """Save the loaded page"""
        
        if self._page is not None and \
           self._page.is_valid() and \
           self._textview.is_modified():

            try:
                self._textview_io.save(self._textview.get_buffer(),
                                       self._page.get_data_file(),
                                       self._page.get_title())
            except RichTextError, e:
                self.emit("error", e.msg, e)
                return
            
            self._page.set_attr_timestamp("modified")
            
            try:
                self._page.save()
            except NoteBookError, e:
                self.emit("error", e.msg, e)
    
    def save_needed(self):
        """Returns True if textview is modified"""
        return self._textview.is_modified()


# add new signals to TakeNoteEditor
gobject.type_register(TakeNoteEditor)
gobject.signal_new("modified", TakeNoteEditor, gobject.SIGNAL_RUN_LAST, 
    gobject.TYPE_NONE, (object, bool))
gobject.signal_new("font-change", TakeNoteEditor, gobject.SIGNAL_RUN_LAST, 
    gobject.TYPE_NONE, (object,))
gobject.signal_new("error", TakeNoteEditor, gobject.SIGNAL_RUN_LAST, 
    gobject.TYPE_NONE, (str, object))
gobject.signal_new("child-activated", TakeNoteEditor, gobject.SIGNAL_RUN_LAST, 
    gobject.TYPE_NONE, (object, object))




class FontUI (object):

    def __init__(self, widget, signal):
        self.widget = widget
        self.signal = signal



class EditorMenus (object):

    def __init__(self, editor):
        self._editor = editor
        self._font_ui_signals = []     # list of font ui widgets


    #=============================================================
    # Update UI (menubar) from font under cursor
    
    def on_font_change(self, editor, font):
        """Update the toolbar reflect the font under the cursor"""
        
        # block toolbar handlers
        for ui in self._font_ui_signals:
            ui.widget.handler_block(ui.signal)

        # update font mods
        self.bold.widget.set_active(font.mods["bold"])
        self.italic.widget.set_active(font.mods["italic"])
        self.underline.widget.set_active(font.mods["underline"])
        self.fixed_width.widget.set_active(font.mods["tt"])
        self.no_wrap.widget.set_active(font.mods["nowrap"])
        
        # update text justification
        self.left_align.widget.set_active(font.justify == "left")
        self.center_align.widget.set_active(font.justify == "center")
        self.right_align.widget.set_active(font.justify == "right")
        self.fill_align.widget.set_active(font.justify == "fill")

        # update bullet list
        self.bullet.widget.set_active(font.par_type == "bullet")
        
        # update family/size buttons        
        self.font_family_combo.set_family(font.family)
        self.font_size_button.set_value(font.size)
        
        # unblock toolbar handlers
        for ui in self._font_ui_signals:
            ui.widget.handler_unblock(ui.signal)


    #==================================================
    # changing font handlers

    def on_mod(self, mod):
        """Toggle a font modification"""
        self._editor.get_textview().toggle_font_mod(mod)

        #font = self._editor.get_textview().get_font()        
        #mod_button.handler_block(mod_id)
        #mod_button.set_active(font.mods[mod])
        #mod_button.handler_unblock(mod_id)

    def on_justify(self, justify):
        """Set font justification"""
        self._editor.get_textview().set_justify(justify)
        font = self._editor.get_textview().get_font()
        self.on_font_change(self._editor, font)
        
    def on_bullet_list(self):
        """Toggle bullet list"""
        self._editor.get_textview().toggle_bullet()
        font = self._editor.get_textview().get_font()
        self.on_font_change(self._editor, font)
        
    def on_indent(self):
        """Indent current paragraph"""
        self._editor.get_textview().indent()

    def on_unindent(self):
        """Unindent current paragraph"""
        self._editor.get_textview().unindent()


    
    def on_family_set(self):
        """Set the font family"""
        self._editor.get_textview().set_font_family(
            self.font_family_combo.get_family())
        self._editor.get_textview().grab_focus()
        

    def on_font_size_change(self, size):
        """Set the font size"""
        self._editor.get_textview().set_font_size(size)
        self._editor.get_textview().grab_focus()
    
    def on_font_size_inc(self):
        """Increase font size"""
        font = self._editor.get_textview().get_font()
        font.size += 2        
        self._editor.get_textview().set_font_size(font.size)
        self.on_font_change(self._editor, font)
    
    
    def on_font_size_dec(self):
        """Decrease font size"""
        font = self._editor.get_textview().get_font()
        if font.size > 4:
            font.size -= 2
        self._editor.get_textview().set_font_size(font.size)
        self.on_font_change(self._editor, font)


    def on_color_set(self, kind, color=0):
        """Set text/background color"""
        
        if color == 0:
            if kind == "fg":
                color = self.fg_color_button.color
            elif kind == "bg":
                color = self.bg_color_button.color
            else:
                color = None

        if color is not None:
            colorstr = color_tuple_to_string(color)
        else:
            colorstr = None

        if kind == "fg":
            self._editor.get_textview().set_font_fg_color(colorstr)
        elif kind == "bg":
            self._editor.get_textview().set_font_bg_color(colorstr)
        else:
            raise Exception("unknown color type '%s'" % str(kind))
        

    def on_choose_font(self):
        """Callback for opening Choose Font Dialog"""
        
        font = self._editor.get_textview().get_font()

        dialog = gtk.FontSelectionDialog("Choose Font")
        dialog.set_font_name("%s %d" % (font.family, font.size))
        response = dialog.run()

        if response == gtk.RESPONSE_OK:
            self._editor.get_textview().set_font(dialog.get_font_name())
            self._editor.get_textview().grab_focus()

        dialog.destroy()


    def _make_toggle_button(self, toolbar, tips, tip_text, icon, 
                            stock_id=None, 
                            func=lambda: None,
                            use_stock_icons=False):

        button = gtk.ToggleToolButton()
        if use_stock_icons and stock_id:
            button.set_stock_id(stock_id)
        else:
            button.set_icon_widget(get_resource_image(icon))
        signal = button.connect("toggled", lambda w: func())
        font_ui = FontUI(button, signal)
        self._font_ui_signals.append(font_ui)
        
        toolbar.insert(button, -1)
        tips.set_tip(button, tip_text)

        return font_ui


    def make_toolbar(self, toolbar, tips, use_stock_icons):
        
        # bold tool
        self.bold = self._make_toggle_button(
            toolbar, tips,
            "Bold", "bold.png", gtk.STOCK_BOLD,
            lambda: self._editor.get_textview().toggle_font_mod("bold"),
            use_stock_icons)
        
        # italic tool
        self.italic = self._make_toggle_button(
            toolbar, tips,
            "Italic", "italic.png", gtk.STOCK_ITALIC,
            lambda: self._editor.get_textview().toggle_font_mod("italic"),
            use_stock_icons)

        # underline tool
        self.underline = self._make_toggle_button(
            toolbar, tips,
            "Underline", "underline.png", gtk.STOCK_UNDERLINE,
            lambda: self._editor.get_textview().toggle_font_mod("underline"),
            use_stock_icons)
        
        # fixed-width tool
        self.fixed_width = self._make_toggle_button(
            toolbar, tips,
            "Monospace", "fixed-width.png", gtk.STOCK_UNDERLINE,
            lambda: self._editor.get_textview().toggle_font_mod("tt"),
            use_stock_icons)

        # no wrap tool
        self.no_wrap = self._make_toggle_button(
            toolbar, tips,
            "No Wrapping", "no-wrap.png", gtk.STOCK_UNDERLINE,
            lambda: self._editor.get_textview().toggle_font_mod("nowrap"),
            use_stock_icons)


        # family combo
        self.font_family_combo = FontSelector()
        self.font_family_combo.set_size_request(150, 25)
        item = gtk.ToolItem()
        item.add(self.font_family_combo)
        tips.set_tip(item, "Font Family")
        toolbar.insert(item, -1)
        self.font_family_id = self.font_family_combo.connect("changed",
            lambda w: self.on_family_set())
        self._font_ui_signals.append(FontUI(self.font_family_combo,
                                           self.font_family_id))
                
        # font size
        DEFAULT_FONT_SIZE = 10
        self.font_size_button = gtk.SpinButton(
          gtk.Adjustment(value=DEFAULT_FONT_SIZE, lower=2, upper=500, 
                         step_incr=1))
        self.font_size_button.set_size_request(-1, 25)
        #self.font_size_button.set_range(2, 100)
        self.font_size_button.set_value(DEFAULT_FONT_SIZE)
        self.font_size_button.set_editable(False)
        item = gtk.ToolItem()
        item.add(self.font_size_button)
        tips.set_tip(item, "Font Size")
        toolbar.insert(item, -1)
        self.font_size_id = self.font_size_button.connect("value-changed",
            lambda w: 
            self.on_font_size_change(self.font_size_button.get_value()))
        self._font_ui_signals.append(FontUI(self.font_size_button,
                                           self.font_size_id))


        # font fg color
        # TODO: code in proper default color
        self.fg_color_button = FgColorTool(14, 15, (0, 0, 0))
        self.fg_color_button.connect("set-color",
                                     lambda w, color: self.on_color_set("fg",
                                                                     color))
        tips.set_tip(self.fg_color_button, "Set Text Color")
        toolbar.insert(self.fg_color_button, -1)
        

        # font bg color
        self.bg_color_button = BgColorTool(14, 15, (65535, 65535, 65535))
        self.bg_color_button.connect("set-color",
                                     lambda w, color: self.on_color_set("bg",
                                                                     color))
        tips.set_tip(self.bg_color_button, "Set Background Color")
        toolbar.insert(self.bg_color_button, -1)

                
        
        # separator
        toolbar.insert(gtk.SeparatorToolItem(), -1)
        
                
        # left tool
        self.left_align = self._make_toggle_button(
            toolbar, tips,
            "Left Align", "alignleft.png", gtk.STOCK_JUSTIFY_LEFT,
            lambda: self.on_justify("left"),
            use_stock_icons)

        # center tool
        self.center_align = self._make_toggle_button(
            toolbar, tips,
            "Center Align", "aligncenter.png", gtk.STOCK_JUSTIFY_CENTER,
            lambda: self.on_justify("center"),
            use_stock_icons)

        # right tool
        self.right_align = self._make_toggle_button(
            toolbar, tips,
            "Right Align", "alignright.png", gtk.STOCK_JUSTIFY_RIGHT,
            lambda: self.on_justify("right"),
            use_stock_icons)

        # justify tool
        self.fill_align = self._make_toggle_button(
            toolbar, tips,
            "Justify Align", "alignjustify.png", gtk.STOCK_JUSTIFY_FILL,
            lambda: self.on_justify("fill"),
            use_stock_icons)
        
        
        # bullet list tool
        self.bullet = self._make_toggle_button(
            toolbar, tips,
            "Bullet List", "bullet.png", None,
            lambda: self.on_bullet_list(),
            use_stock_icons)
        
        
    def get_format_menu(self):

        return [
            ("/Fo_rmat", 
             None, None, 0, "<Branch>"),

            ("/Format/_Bold", 
             "<control>B", lambda w,e: self.on_mod("bold"), 0, 
             "<ImageItem>", 
             get_resource_pixbuf("bold.png")),
            ("/Format/_Italic", 
             "<control>I", lambda w,e: self.on_mod("italic"), 0, 
             "<ImageItem>", 
             get_resource_pixbuf("italic.png")),
            ("/Format/_Underline", 
             "<control>U", lambda w,e: self.on_mod("underline"), 0, 
             "<ImageItem>", 
             get_resource_pixbuf("underline.png")),
            ("/Format/_Monospace",
             "<control>M", lambda w,e: self.on_mod("tt"), 0,
             "<ImageItem>",
             get_resource_pixbuf("fixed-width.png")),
            ("/Format/No _Wrapping",
             None, lambda w, e: self.on_mod("nowrap"), 0,
             "<ImageItem>",
             get_resource_pixbuf("no-wrap.png")),
            
            ("/Format/sep1",
             None, None, 0, "<Separator>" ),            
            
            ("/Format/_Left Align", 
             "<control>L", lambda w,e: self.on_justify("left"), 0, 
             "<ImageItem>", 
             get_resource_pixbuf("alignleft.png")),
            ("/Format/C_enter Align", 
             "<control>E", lambda w,e: self.on_justify("center"), 0, 
             "<ImageItem>", 
             get_resource_pixbuf("aligncenter.png")),
            ("/Format/_Right Align", 
             "<control>R", lambda w,e: self.on_justify("right"), 0, 
             "<ImageItem>", 
             get_resource_pixbuf("alignright.png")),
            ("/Format/_Justify Align", 
             "<control>J", lambda w,e: self.on_justify("fill"), 0, 
             "<ImageItem>", 
             get_resource_pixbuf("alignjustify.png")),
            ("/Format/sep2",
             None, None, 0, "<Separator>" ),

            ("/Format/_Bullet List", 
             "<control>asterisk", lambda w,e: self.on_bullet_list(), 0, 
             "<ImageItem>", 
             get_resource_pixbuf("bullet.png")),
            ("/Format/Indent M_ore", 
             "<control>parenright", lambda w,e: self.on_indent(), 0, 
             "<ImageItem>", 
             get_resource_pixbuf("indent-more.png")),     
            ("/Format/Indent Le_ss", 
             "<control>parenleft", lambda w,e: self.on_unindent(), 0, 
             "<ImageItem>", 
             get_resource_pixbuf("indent-less.png")),
            
            ("/Format/sep4", 
                None, None, 0, "<Separator>" ),
            ("/Format/Increase Font _Size", 
                "<control>equal", lambda w, e: self.on_font_size_inc(), 0, 
                "<ImageItem>", 
                get_resource_pixbuf("font-inc.png")),
            ("/Format/_Decrease Font Size", 
                "<control>minus", lambda w, e: self.on_font_size_dec(), 0, 
                "<ImageItem>", 
                get_resource_pixbuf("font-dec.png")),

            ("/Format/sep5", 
                None, None, 0, "<Separator>" ),
            ("/Format/_Apply Text Color", 
                "", lambda w, e: self.on_color_set("fg"), 0),
            ("/Format/A_pply Background Color", 
                "", lambda w, e: self.on_color_set("bg"), 0),
            
            
            ("/Format/sep6", 
                None, None, 0, "<Separator>" ),
            ("/Format/Choose _Font", 
                "<control><shift>F", lambda w, e: self.on_choose_font(), 0, 
                "<ImageItem>", 
                get_resource_pixbuf("font.png"))
        ]



