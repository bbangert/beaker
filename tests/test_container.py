from beaker.container import *
import random, time, weakref, sys
import test_base
import sys


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
        
def threadtest(cclass, id, statusdict, expiretime, delay, params):
    print "create thread %d starting" % id
    statusdict[id] = True


    try:
        container = cclass(context = context, namespace = 'test', key = 'test', createfunc = lambda: create(id, delay), expiretime = expiretime, data_dir='./cache', starttime = starttime, **params)

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
    

def runtest(cclass, totaltime, expiretime, delay, **params):

    statusdict = {}
    global totalcreates
    totalcreates = 0

    global totalgets
    totalgets = 0

    container = cclass(context = context, namespace = 'test', key = 'test', createfunc = lambda: create(id, delay), expiretime = expiretime, data_dir='./cache', starttime = starttime, **params)
    container.clear_value()

    global running
    running = True    
    for t in range(1, 20):
        thread.start_new_thread(threadtest, (cclass, t, statusdict, expiretime, delay, params))
        
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
    def _runtest(self, cclass, totaltime, expiretime, delay, **params):
        print "\ntesting %s for %d secs with expiretime %s delay %d" % (
            cclass, totaltime, expiretime, delay)
        
        runtest(cclass, totaltime, expiretime, delay, **params)

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
