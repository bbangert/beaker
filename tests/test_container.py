import os
import random
import time
import sys
import weakref
import test_base
from beaker.container import *
from beaker.synchronization import Synchronizer

# container test -
# tests the container's get_value() function mostly, to insure
# that items are recreated when expired, and that create function
# is called exactly once per expiration

try:
    import thread
except:
    raise "this test requires a thread-enabled python"
    
#import logging
#logging.basicConfig()
#logging.getLogger('beaker.container').setLevel(logging.DEBUG)

class Item(object):
    
    def __init__(self, id):
        self.id = id
        
    def __str__(self):
        return "item id %d" % self.id

    def test_item(self):
        return True


# keep running indicator
running = False

starttime = time.time()

# creation func entrance detector to detect non-synchronized access
# to the create function
baton = None

context = ContainerContext()

def create(id, delay = 0):
    global baton
    if baton is not None:
        raise "baton is not none , ident " + repr(baton) + " this thread " + repr(thread.get_ident())

    baton = thread.get_ident()
    try:    
        i = Item(id)

        time.sleep(delay)
        global totalcreates
        totalcreates += 1

        return i
    finally:
        baton = None
        
def threadtest(cclass, id, statusdict, expiretime, delay, threadlocal):
    print "create thread %d starting" % id
    statusdict[id] = True


    try:
        if threadlocal:
            container = cclass(context = context, namespace = 'test', key = 'test', createfunc = lambda: create(id, delay), expiretime = expiretime, data_dir='./cache', starttime = starttime)
        else:
            container = global_container
            
        global running
        global totalgets
        try:
            while running:
                item = container.get_value()
                if not item.test_item():
                    raise "item did not test"
                item = None
                totalgets += 1
                time.sleep(random.random() * .00001)
        except:
            
            e = sys.exc_info()[0]
            running = False
            print e
            raise
    finally:
        print "create thread %d exiting" % id
        statusdict[id] = False
    

def runtest(cclass, totaltime, expiretime, delay, threadlocal):

    statusdict = {}
    global totalcreates
    totalcreates = 0

    global totalgets
    totalgets = 0

    global global_container
    global_container = cclass(context = context, namespace = 'test', key = 'test', createfunc = lambda: create(id, delay), expiretime = expiretime, data_dir='./cache', starttime = starttime)
    global_container.clear_value()

    global running
    running = True    
    for t in range(1, 20):
        thread.start_new_thread(threadtest, (cclass, t, statusdict, expiretime, delay, threadlocal))
        
    time.sleep(totaltime)
    
    failed = not running

    running = False

    pause = True
    while pause:
        time.sleep(1)    
        pause = False
        for v in statusdict.values():
            if v:
                pause = True
                break

    if failed:
        raise "test failed"

    print "total object creates %d" % totalcreates
    print "total object gets %d" % totalgets

class ContainerTest(test_base.MyghtyTest):
    def _runtest(self, cclass, totaltime, expiretime, delay):
        print "\ntesting %s for %d secs with expiretime %s delay %d" % (
            cclass, totaltime, expiretime, delay)
        
        runtest(cclass, totaltime, expiretime, delay, threadlocal=False)

        if expiretime is None:
            self.assert_(totalcreates == 1)
        else:
            self.assert_(abs(totaltime / expiretime - totalcreates) <= 2)

    def testMemoryContainer(self, totaltime=10, expiretime=None, delay=0):
        self._runtest(container_registry('memory'),
                      totaltime, expiretime, delay)

    def testMemoryContainer2(self):
        self.testMemoryContainer(expiretime=2)

    def testMemoryContainer3(self):
        self.testMemoryContainer(expiretime=5, delay=2)

    def testDbmContainer(self, totaltime=10, expiretime=None, delay=0):
        self._runtest(container_registry('dbm'),
                      totaltime, expiretime, delay)
        
    def testDbmContainer2(self):
        self.testDbmContainer(expiretime=2)

    def testDbmContainer3(self):
        self.testDbmContainer(expiretime=5, delay=2)

    
    def test_file_open_bug(self):
        # 1. create container
        container = container_registry('file')(context=context, namespace='reentrant_test', key='test', data_dir='./cache')
        
        # 2. ensure its file doesnt exist.
        try:
            os.remove(container.namespacemanager.file)
        except OSError:
            pass
        
        # 3. set a value.
        container.set_value("x")

        # 4. open the file and corrupt its pickled data
        f = open(container.namespacemanager.file, 'w')
        f.write("BLAH BLAH BLAH")
        f.close()
        
        # 5. set another value.  namespace.acquire_lock() opens the file, the pickle raises an exception, the lock stays open (that was the bug)
        # comment out line 147 of container.py, self.do_release_write_lock() inside of acquire_write_lock(), to illustrate
        try:
            container.set_value("y")
            assert False
        except:
            pass
            
        # 6. clear file synchronziers, rebuild the namespace / context etc. so a new Synchchronizer gets built (alternatively, just
        # access the same container from a different thread)
        Synchronizer.conditions.clear()
        context.clear()
        container = container_registry('file')(context=context, namespace='reentrant_test', key='test', data_dir='./cache')
        
        # 7. acquire write lock hangs !
        try:
            container.set_value("z")
            assert False
        except:
            pass
