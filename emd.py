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
    msg = \
'''
help ...
'''
    print(msg)

class PicEnc:
    def __init__(self, raw, filename, avatar='', text=None):
        self.raw = raw
        self.avatar = avatar
        self.filename = filename
        self.text = text
        self.qid = None
        self.enc = None
        self.info = None

class Embedor:
    MD_PIC_PATTERN = re.compile(r'''!\[.+\]\(.+\)''')
    APPEND0 = '<div id="encoded_data" style="display: none;">'
    APPEND1 = '</div>'
    MD_PREFIX = '[{qid}]:data:text/plain;base64,'
    PNG_PREFIX = '[{qid}]:data:image/png;base64,'

    def __init__(self, md_file):
        self.md_file = md_file
        try:
            with open(self.md_file, 'rb') as f:
                self.md = f.read()
                self.md = self.md.decode()
        except Exception as e:
            sys.stderr.write(e)
            sys.stderr.write('open "{}" failed.\n'.format(self.md_file))
            sys.exit(-1)
        self.eol = '\r\n' if '\r\n' in self.md else '\n'
        self.wp = Embedor.get_work_path(md_file)
        self.pic_data = deque()
        self.md_data = deque()

    @staticmethod
    def get_work_path(md_filename):
        ap = os.path.abspath(md_filename)
        wp = os.path.split(ap)[0]
        return wp

    @staticmethod
    def extract_pic_mark(md_pic_mark):
        assert Embedor.MD_PIC_PATTERN.match(md_pic_mark)
        i = md_pic_mark.find(']')
        assert i >= 2
        avatar = md_pic_mark[2 : i]
        i = md_pic_mark.find('(')
        assert i >= 3
        filename = md_pic_mark[i + 1 : -1].strip()
        q = filename[-1]
        _ = filename[:-1]
        text = None
        if q == '"' or q == "'":
            assert q in _
            i = _.find(q)
            text = filename[i + 1 : -1]
            filename = filename[:i].strip()
        ret = PicEnc(md_pic_mark, filename, avatar, text)
        return ret

    def encode_pic(self, pic_enc):
        if os.path.isabs(pic_enc.filename):
            f = pic_enc.filename
        else:
            f = os.path.join(self.wp, pic_enc.filename)
        if not os.path.isfile(f):
            msg = '"{}" not exists.'.format(pic_enc.filename)
            pic_enc.info = msg
            sys.stderr.write(msg + '\n')
        pic_byte = open(f, 'rb').read()
        if not pic_byte.startswith(b'\x89PNG'):
            msg = '"{}" is not in PNG format.'.format(pic_enc.filename)
            pic_enc.info = msg
            sys.stderr.write(msg + '\n')
        pic_enc.qid = base64.b32encode(hashlib.sha1(pic_byte).digest())[:8].decode()
        pic_enc.enc = base64.b64encode(pic_byte).decode()
    
    def encode_md(self):
        byte_md = self.md.encode()
        z = bz2.compress(byte_md, 9)
        return base64.b64encode(z).decode()


    def embed(self):
        idx = 0
        pic_data = deque()
        for m in Embedor.MD_PIC_PATTERN.finditer(self.md):
            self.md_data.append(self.md[idx: m.start()])
            pic_data.append(m.group(0))
            idx = m.end() + 1
        self.md_data.append(self.md[idx:])
        for pic_mark in pic_data:
            pic_enc = Embedor.extract_pic_mark(pic_mark)
            self.encode_pic(pic_enc)
            self.pic_data.append(pic_enc)

        buf = deque()
        refs = deque()
        refs.append(Embedor.APPEND0)
        refs.append(Embedor.MD_PREFIX.format(qid='markdown') + self.encode_md())
        for i, m in enumerate(self.pic_data):
            buf.append(self.md_data[i])
            if not m.info:
                buf.append('![{avatar}][{qid}]'.format(avatar=m.avatar, qid=m.qid))
                ref = Embedor.PNG_PREFIX.format(qid=m.qid) + m.enc
                if m.text:
                    ref += ' "{}"'.format(m.text)
                refs.append(ref)

            else:
                buf.append(m.raw)
        buf.append(self.md_data[-1])
        buf.append(self.eol * 2)
        refs.append(Embedor.APPEND1)
        buf.append((self.eol * 2).join(refs))

        md = ''.join(buf)
        os.rename(self.md_file, self.md_file + '.bak')
        open(self.md_file, 'w').write(md)


    def recover(self):
        pass


def main():
    # if len(sys.argv) == 2:
    #     Embedor(sys.argv[1]).embed()
    # else:
    #     usage()
    Embedor('C:\\Users\\WindowsX\\Desktop\\writeup\\whalectf\\web\\web.md').embed()


if __name__ == '__main__':
    main()
