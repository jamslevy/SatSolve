# Copyright 2008 Thomas Quemard
#
# Paste-It is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License as published
# by the Free Software Foundation; either version 3.0, or (at your option)
# any later version.
#
# Paste-It is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY
# or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public
# License for more details.

import cgi
import datetime
import paste_app.paste
import paste_app.paste.lang
import paste_app.paste.model
import paste_app.paste.web

from utils.utils import admin_only

class Pasty(paste_app.paste.web.RequestHandler):

    def __init__(self):
        paste_app.paste.web.RequestHandler.__init__(self)
        self.set_module(__name__)
        self.highlights = set([])
        self.has_edited_lines = False
        self.has_highlights = False
        self.edited_lines = {}
        self.lines = []
        self.line_count = 0
        self.parent = None

    def update_highlights(self, hl_string):
        line_max = self.line_count + 1
        if hl_string != "":
            hl_items = hl_string.split(",")
            for item in hl_items:
                if item.isdigit():
                    self.highlights.add(int(item))

                # Line range
                elif ":" in item != -1:
                    part = item.partition(":")
                    if part[0].isdigit() and part[2].isdigit():
                        r_start = int(part[0])
                        r_end = int(part[2]) + 1
                        if r_start > r_end :
                            t_end = r_end
                            r_end = t_end
                            r_start = t_end
                        if r_start > line_max : r_start = line_max
                        if r_end > line_max : r_end = line_max

                        if r_start != r_end and not (r_start == 1 and r_end == line_max):
                            for i in range(r_start, r_end):
                                if not i in self.highlights:
                                    self.highlights.add(i)

                # Reset
                elif item == "-":
                    self.highlights = []

                # Reverse
                elif item == "!":
                    rhl = [hl_string]
                    for i in range(1, line_max):
                        if not i in hl:
                            rhl.add(i)
                    self.highlights = rhl
        return self.highlights

    def format_code(self):
        r_code = ""
        r_lines = ""
        i = 1
        for line in self.lines:
            r_lines += "<tr><td class=\"line\">"
            r_lines += "<a href=\"#l" + str(i) + "\" name=\"l" + str(i) + "\">" + str(i) + "</a>"
            r_lines += "</td></tr>\n"

            r_code += "<tr>"
            if i in self.highlights: r_code += "<td class=\"hl\">"
            else: r_code += "<td>"

            if self.has_edited_lines and self.edited_lines.has_key(str(i)):
                r_code += self.format_line_start(cgi.escape(self.request.get("e" + str(i))))
            else:
                if line == "": r_code += "<br/>"
                else: r_code += self.format_line_start(line)

            r_code += "</td></tr>\n"
            i += 1

        return (r_lines, r_code)

    def format_simple_code(self):
        r_lines = ""
        r_code = ""
        i = 1
        for line in self.lines:
            r_lines += "<tr><td class=\"line\"><a href=\"#l" + str(i) + "\" name=\"l" + str(i) + "\">" + str(i) + "</a></td></tr>"
            r_code += "<tr><td>"
            if line == "": r_code += "<br />"
            else: r_code += self.format_line_start(line)
            r_code += "</td></tr>\n"
            i += 1
        return (r_lines, r_code)

    def format_line_start(self, line):
        result = ""
        i = 0
        for c in line:
            if c == " ":
                result += "&nbsp;"
            elif c == "\t":
                result += "&nbsp;&nbsp;&nbsp;"
            else:
                result += line[i:]
                break;
            i += 1
        return result

    def get(self, pasty_slug):
        pasties = paste_app.paste.model.Pasty.all()
        pasties.filter("slug =", pasty_slug)
        self.pasty = pasties.get()
        if self.pasty.is_private:
          self.get_authentication()
        self.pasty_slug = pasty_slug
        self.get_parent_paste()

        if self.pasty == None:
            self.get_404()
        else:
            self.get_200()

    @admin_only
    def get_authentication(self):
      return
      
    def get_200(self):

        self.lines = self.pasty.code_colored.splitlines()
        self.line_count = len(self.lines)
        lines = ""
        code = ""

        complex_formating = self.request.get("h") != ""

        if self.request.get("h"):
            self.update_highlights(self.request.get("h"))

        for arg in self.request.arguments():
            if arg[0:1] == "e" and arg[1:].isdigit():
                self.edited_lines[arg[1:]] = True
                self.has_edited_lines = True
                complex_formating = True

        if complex_formating:
            (lines, code) = self.format_code()
        else:
            (lines, code) = self.format_simple_code()


        if self.pasty.language != "":
            lang = paste_app.paste.lang.get_by_tag(self.pasty.language)
            if lang != None:
                self.content["language"] = lang.name
                self.content["u_language"] = lang.url

        tc = paste_app.paste.tag.TagCollection()
        tc.import_string(self.pasty.tags)
        replies = self.get_replies()

        self.content["reply_count"] = len(replies)
        self.content["has_replies"] = len(replies) > 0
        self.content["replies"] = replies
        self.content["h1"] = "p" + self.pasty_slug
        self.content["page-title"] =  cgi.escape(self.pasty.title)
        self.content["pasty_slug"] = cgi.escape(self.pasty.title)
        self.content["pasty_lines"] = lines
        self.content["pasty_code"] = code
        self.content["pasty_tags"] = ", ".join(tc.tags)
        self.content["user_name"] = self.pasty.posted_by_user_name
        self.content["posted_at"] = self.pasty.posted_at.strftime("%b, %d %Y at %H:%M")
        self.content["u"] = paste_app.paste.url("%s", self.pasty_slug)
        self.content["u_edit"] = paste_app.paste.url("?edit=%s", self.pasty_slug)
        self.content["u_raw_text"] = paste_app.paste.url("%s.txt", self.pasty_slug)

        self.write_out("page/pasties/pasty/200.html")

        #self.update_expiration_time()

    def get_404(self):
        self.error(404)
        self.content["pasty_slug"] = cgi.escape(self.pasty_slug)
        self.write_out("page/pasties/pasty/404.html")

    def get_parent_paste(self):
        if self.pasty != None and self.pasty.parent_paste != "":
            qparent = paste_app.paste.model.Pasty.all()
            qparent.filter("slug =", self.pasty.parent_paste)
            self.parent = qparent.get()
            if self.parent != None:
                self.content["u_parent"] = paste_app.paste.url("%s", self.parent.slug)
                self.content["parent_title"] = cgi.escape(self.parent.title)

            # Datastore is not up to date, removing <parent_paste> slug
            # because the parent has been deleted
            else:
                self.pasty.parent_paste = ""
                self.pasty.put()

    def get_replies(self):
        replies = []
        if self.pasty.replies > 0:
            qrel = paste_app.paste.model.PasteReply.all()
            qrel.filter("parent_paste =", self.pasty.slug)
            rels = qrel.fetch(self.pasty.replies)
            for rel in rels:
                tp = {}
                tp["title"] = rel.title
                tp["u"] = paste_app.paste.url("%s", rel.reply)
                replies.append(tp)
        return replies

    def update_expiration_time(self):
        if self.pasty != None:
            self.pasty.expired_at = datetime.datetime.now() + paste_app.paste.config["pasty_expiration_delta"]
            self.put()

