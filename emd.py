#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
embed markdown
a script to embed png into markdown with base64 encode
a single markdown file is simple and avoids link failure
"""

from __future__ import absolute_import, division, print_function
import os
import sys
import re
import bz2
import base64
import hashlib
import getopt
from collections import deque
try:
    # for picture on network
    # only support local picture without this lib
    # TODO: not implemented
    import requests as _REQ
except:
    _REQ = None
try:
    # for picture not in PNG format
    # to convert the picture to PNG format
    # because some markdown editors only support PNG in base64
    # such as YOUDAO CLOUD NOTES
    # TODO: not implemented
    import PIL as _PIL
except:
    _PIL = None
if sys.version_info.major < 3:
    range = xrange
    input = raw_input


def usage():
    msg = '''
-u, --url       fetch picture using url (not implemented now)
-c, --convert   convert picture to PNG which is not in PNG format (not implemented now)
'''
    sys.stdout.write(msg)


def parse_args():
    try:
        opts, args = getopt.getopt(sys.argv[1:], 'huc', ('help', 'url', 'convert'))
    except getopt.GetoptError as _:
        usage()
        sys.exit(0)
    e = Embedor()
    for opt, _ in opts:
        if opt in ('-h', '--help'):
            usage()
            sys.exit(0)
        if opt in ('-u', '--url'):
            pass
        if opt in ('-c', '--convert'):
            pass
    for val in args:
        e.add_markdown(val)
    return e


class Picture:
    """
    raw: ![avatar](url "option title")
    enc: encode by base64
    log: encode (error) message
    """
    def __init__(self, raw=None, workplace=None):
        self.workplace = './'
        self.raw = ''
        self.avatar = ''
        self.url = ''
        self.opt = ''

        self.qid = ''
        self.enc = None
        self.log = None
        if workplace is not None:
            self.workplace = workplace
        if raw is not None:
            self.__split_raw(raw)

    def __split_raw(self, raw):
        """
        split raw into
            avatar
            url
            opt
        :param raw: ![avatar](url "option title")
        """
        assert Markdown.PIC_PATTERN.match(raw)
        self.raw = raw
        i = self.raw.find(']')
        assert i >= 2
        avatar = self.raw[2: i]
        i = self.raw.find('(')
        assert i >= 3
        url = self.raw[i + 1: -1].strip()
        q = url[-1]
        _ = url[:-1]
        opt = None
        if q == '"' or q == "'":
            assert q in _
            i = _.find(q)
            opt = url[i + 1: -1]
            url = url[:i].strip()
        self.url = url
        self.avatar = avatar
        self.opt = opt

    def encode(self):
        if os.path.isabs(self.url):
            f = self.url
        else:
            f = os.path.join(self.workplace, self.url)
        if not os.path.isfile(f):
            msg = '"{}" not exists.'.format(self.url)
            self.log = msg
            sys.stderr.write(msg + '\n')
        try:
            pic_byte = open(f, 'rb').read()
            if not pic_byte.startswith(b'\x89PNG'):
                msg = '"{}" is not in PNG format.'.format(self.url)
                self.log = msg
                sys.stderr.write(msg + '\n')
            self.qid = base64.b32encode(hashlib.md5(pic_byte).digest())[:8].decode()
            self.enc = base64.b64encode(pic_byte).decode()
        except IOError or OSError as _:
            msg = 'cannot open file: {}'.format(self.url)
            self.log = msg
            sys.stderr.write(msg + '\n')


class Markdown:
    PIC_PATTERN = re.compile(r'''!\[[^\[\]]+?\]\([^\(\)]+?\)''')
    APPEND_HEADER = '<div id="encoded_data" style="display: none;">'
    APPEND_FOOTER = '</div>'
    MD_PREFIX = '[{qid}]:data:text/plain;base64,'
    PNG_PREFIX = '[{qid}]:data:image/png;base64,'

    def __init__(self, md_file=''):
        if not os.path.isfile(md_file):
            raise IOError('No such file: {}'.format(md_file))
        self.md = md_file
        self.workplace = self.__get_workplace(self.md)
        self.byte_data = open(self.md, 'rb').read()
        if b'\r\n' in self.byte_data:
            self.eol = b'\r\n'
        elif b'\r' in self.byte_data:
            self.eol = b'\r'
        else:
            self.eol = b'\n'
        self.pictures = deque()
        self.tmp_md = deque()
        self.new_md = ''

    @staticmethod
    def __get_workplace(md_filename):
        ap = os.path.abspath(md_filename)
        wp = os.path.split(ap)[0]
        return wp

    def __encode_md(self):
        z = bz2.compress(self.byte_data, 9)
        return base64.b64encode(z).decode()

    def __split(self):
        text = self.byte_data.decode()
        idx = 0
        for m in Markdown.PIC_PATTERN.finditer(text):
            self.tmp_md.append(text[idx: m.start()])
            self.pictures.append(Picture(m.group(0), self.workplace))
            idx = m.end()
        self.tmp_md.append(text[idx:])
        for p in self.pictures:
            p.encode()


    def __makeup(self):
        buf = deque()
        refs = deque()
        refs.append(Markdown.APPEND_HEADER)
        refs.append(Markdown.MD_PREFIX.format(qid='markdown') + self.__encode_md())
        for i, p in enumerate(self.pictures):
            buf.append(self.tmp_md[i])
            if p.log is not None:
                buf.append(p.raw)
            else:
                buf.append('![{avatar}][{qid}]'.format(avatar=p.avatar, qid=p.qid))
                ref = Markdown.PNG_PREFIX.format(qid=p.qid) + p.enc
                if p.opt is not None and len(p.opt) > 0:
                    ref += ' "{}"'.format(p.opt)
                refs.append(ref)
        buf.append(self.tmp_md[-1])
        buf.append(self.eol.decode() * 2)
        refs.append(Markdown.APPEND_FOOTER)
        buf.append((self.eol.decode() * 2).join(refs))

        self.new_md = ''.join(buf)

    def output(self):
        self.__split()
        self.__makeup()
        n, e = os.path.splitext(os.path.join(self.workplace, self.md))
        f = n + '.emd' + e
        open(f, 'wb').write(self.new_md.encode())


class Embedor:

    def __init__(self):
        self.markdowns = deque()

    def add_markdown(self, markdown_path):
        try:
            self.markdowns.append(Markdown(markdown_path))
        except:
            pass

    def embed(self):
        for m in self.markdowns:
            m.output()


    def recover(self):
        # TODO:
        pass


def main():
    embedor = parse_args()
    embedor.embed()

# def test():
#     embedor = Embedor()
#     embedor.add_markdown('C:\\Users\\WindowsX\\Desktop\\7-31\\writeup\\writeup.md')
#     embedor.embed()

if __name__ == '__main__':
    main()
    # test()
