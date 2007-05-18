import unittest, os, sys

import beaker.util as util

class MyghtyTest(unittest.TestCase):
    def __init__(self, *args, **params):
        unittest.TestCase.__init__(self, *args, **params)
        
        # make ourselves a Myghty environment
        self.root = os.path.abspath(os.path.join(os.getcwd(), 'testroot'))
        
        # some templates
        self.htdocs = os.path.join(self.root, 'htdocs')
        
        # some more templates
        self.components = os.path.join(self.root, 'components')
        
        # data dir for cache, sessions, compiled
        self.cache = os.path.join(self.root, 'cache')
        
        # lib dir for some module components
        self.lib = os.path.join(self.root, 'lib')
        sys.path.insert(0, self.lib)
        
        for path in (self.htdocs, self.components, self.cache, self.lib):
            util.verify_directory(path)
        
        self.class_set_up()

    def class_set_up(self):
        pass

    def class_tear_down(self):
        pass
        
    def __del__(self):
        self.class_tear_down()
        
    def create_file(self, dir, name, contents):
        file = os.path.join(dir, name)
        f = open(file, 'w')
        f.write(contents)
        f.close()
        
    def create_directory(self, dir, path):
        util.verify_directory(os.path.join(dir, path))
        
    def remove_file(self, dir, name):
        if os.access(os.path.join(dir, name), os.F_OK):
            os.remove(os.path.join(dir, name))
