"""Multi-directory template loader for Ibis."""

import os

from pyview.vendor.ibis import Template
from pyview.vendor.ibis.errors import TemplateLoadError


class MultiDirReloader:
    """Template loader that searches multiple directories in order."""

    def __init__(self, dirs):
        self.dirs = dirs
        self.cache = {}

    def __call__(self, filename):
        for base_dir in self.dirs:
            path = os.path.join(base_dir, filename)
            if os.path.isfile(path):
                mtime = os.path.getmtime(path)
                if path in self.cache:
                    if mtime == self.cache[path][0]:
                        return self.cache[path][1]

                with open(path, encoding="utf-8") as file:
                    template_string = file.read()

                template = Template(template_string, filename)
                self.cache[path] = (mtime, template)
                return template

        msg = f"MultiDirReloader cannot locate the template file '{filename}' in dirs: {self.dirs}"
        raise TemplateLoadError(msg)
