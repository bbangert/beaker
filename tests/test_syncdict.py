from beaker.util import SyncDict, WeakValuedRegistry
import random, time, weakref
import threading

class Value(object):
    values = {}

    def do_something(self, id):
        Value.values[id] = self

    def stop_doing_something(self, id):
        del Value.values[id]

mutex = threading.Lock()

def create(id):
    assert not Value.values, "values still remain"
    global totalcreates
    totalcreates += 1
    return Value()

def threadtest(s, id):
    print "create thread %d starting" % id

    global running
    global totalgets
    while running:
        try:
            value = s.get('test', lambda: create(id))
            value.do_something(id)
        except Exception, e:
            print "Error", e
            running = False
            break
        else:
            totalgets += 1
            time.sleep(random.random() * .01)
            value.stop_doing_something(id)
            del value
            time.sleep(random.random() * .01)

def runtest(s):

    global values
    values = {}

    global totalcreates
    totalcreates = 0

    global totalgets
    totalgets = 0

    global running
    running = True

    threads = []
    for id_ in range(1, 20):
        t = threading.Thread(target=threadtest, args=(s, id_))
        t.start()
        threads.append(t)

    for i in range(0, 10):
        if not running:
            break
        time.sleep(1)

    failed = not running

    running = False

    for t in threads:
        t.join()

    assert not failed, "test failed"

    print "total object creates %d" % totalcreates
    print "total object gets %d" % totalgets


def test_dict():
    # normal dictionary test, where we will remove the value
    # periodically. the number of creates should be equal to
    # the number of removes plus one.
    print "\ntesting with normal dict"
    runtest(SyncDict())


def test_weakdict():
    print "\ntesting with weak dict"
    runtest(WeakValuedRegistry())
