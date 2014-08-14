#!/usr/bin/python
# -*- coding: utf-8 -*-

from fuse import FUSE, Operations
import os
import pwd
from stat import S_IFDIR, S_IFREG
from time import time
from sys import argv, exit
import re
import urllib
import threading
from BeautifulSoup import BeautifulSoup as Soup
from soupselect import select

# TODO
# use actual dates in readdir
# support folders


class UrlFetcher(threading.Thread):
    def __init__(self, url):
        threading.Thread.__init__(self)
        self.url = url

    def run(self):
        return urllib.urlopen(self.url).read()


class MeoParser(object):

    def __init__(self, url):
        self.url = url

    def files_info(self):
        html = Soup(urllib.urlopen(self.url))
        urls = select(html, 'li.file')
        files_info = {}
        for f in urls:
            fileinfo = {
                'url': self.get_url(f),
                'name': self.get_name(f),
                'size': self.get_size(f),
                'modified': self.get_modified(f),
            }
            files_info[fileinfo['name']] = fileinfo
        return files_info

    def get_size(self, html):
        # TODO does not exist for folders
        size_desc = select(html, 'span.file_size')
        if not size_desc:
            return 0
        size_desc = size_desc[0].text
        size = int(re.search('([\d]+)', size_desc).groups()[0])
        if "gb" in size_desc.lower():
            size = int(float(size) * 1024 * 1024 * 1024)
        elif "mb" in size_desc.lower():
            size = int(float(size) * 1024 * 1024)
        elif "kb" in size_desc.lower():
            size = int(float(size) * 1024)
        return size

    def get_modified(self, html):
        modified = select(html, 'span.file_timestamp')[0].text
        return modified

    def get_name(self, html):
        url = self.get_url(html)
        return url.split('/')[-1:][0]

    def get_url(self, html):
        link = select(html, 'a')
        url = re.search('href="([^"]*)"', str(link[0])).groups()[0]
        return url


class FileLoader(object):

    def __init__(self, files_info):
        self.files_info = files_info
        self.files = {}

    def fetch(self):
        for fname, f in self.files_info.iteritems():
            th = UrlFetcher(f['url'])
            self.files[fname] = th.run()
        return self.files


class MeoCloudFuse(Operations):

    def __init__(self, url, path):
        self.fetcher = MeoParser(url)
        self.files_info = self.fetcher.files_info()
        self.loader = FileLoader(self.files_info)
        self.files = self.loader.fetch()

    def _exists(self, path):
        for fl in self.files_info:
            if path == '/%s' % urllib.unquote(os.path.basename(fl)):
                return fl
        return False

    def getattr(self, path, fh=None):
        uid = pwd.getpwuid(os.getuid()).pw_uid
        gid = pwd.getpwuid(os.getuid()).pw_gid
        now = time()
        our_path = self._exists(path)
        if our_path:
            return dict(
                st_mode=S_IFREG | 0444,
                st_size=self.files_info[our_path]['size'],
                st_ctime=now,
                st_mtime=now,
                st_atime=now,
                st_nlink=1,
                st_guid=gid,
                st_uid=uid
            )
        if path == '/':
            return dict(st_mode=S_IFDIR | 0755, st_ctime=now,
                        st_mtime=now, st_atime=now, st_nlink=3)
        else:
            # defaults
            return dict(
                st_mode=S_IFREG | 0444,
                st_size=0,
                st_ctime=now,
                st_mtime=now,
                st_atime=now,
                st_nlink=1,
            )

    def readdir(self, path, fh):
        defaults = ['.', '..']
        if path == '/':
            defaults.extend(self.files_info.keys())
        return defaults

    def read(self, path, size, offset, fh):
        our_path = self._exists(path)
        filedata = self.files[our_path]
        if filedata is None:
            return 0
        if offset + size > len(filedata):
            size = len(filedata) - offset

        return filedata[offset:offset + size]

if __name__ == '__main__':
    if len(argv) != 3:
        print 'usage: %s <meocloud link url> <mount point>' % argv[0]
        print 'eg: python meocloudfuse.py https://meocloud.pt/link/7f065f06-175b-466e-80d3-560c27b538/posters/ /mnt/meo'
        exit(1)

    FUSE(MeoCloudFuse(argv[1], argv[2]), argv[2], foreground=True, nothreads=False)
