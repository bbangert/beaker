import os
import random
import time
from beaker.container import *
from beaker.synchronization import _synchronizers
from beaker.cache import clsmap
from threading import Thread

class CachedWidget(object):
    totalcreates = 0
    delay = 0

    def __init__(self):
        CachedWidget.totalcreates += 1
        time.sleep(CachedWidget.delay)
        self.time = time.time()

def _run_container_test(cls, totaltime, expiretime, delay, threadlocal):
    print "\ntesting %s for %d secs with expiretime %s delay %d" % (
        cls, totaltime, expiretime, delay)

    CachedWidget.totalcreates = 0
    CachedWidget.delay = delay

    # allow for python overhead when checking current time against expire times
    fudge = 10

    starttime = time.time()

    running = [True]
    class RunThread(Thread):
        def run(self):
            print "%s starting" % self

            if threadlocal:
                localvalue = Value(
                                'test', 
                                cls('test', data_dir='./cache'), 
                                createfunc=CachedWidget, 
                                expiretime=expiretime, 
                                starttime=starttime)
                localvalue.clear_value()
            else:
                localvalue = value

            try:
                while running[0]:
                    item = localvalue.get_value()
                    if expiretime is not None:
                        currenttime = time.time()
                        itemtime = item.time
                        assert itemtime + expiretime + delay + fudge >= currenttime, \
                            "created: %f expire: %f delay: %f currenttime: %f" % \
                            (itemtime, expiretime, delay, currenttime)
                    time.sleep(random.random() * .00001)
            except:
                running[0] = False
                raise
            print "%s finishing" % self

    if not threadlocal:
        value = Value(
                    'test', 
                    cls('test', data_dir='./cache'), 
                    createfunc=CachedWidget, 
                    expiretime=expiretime, 
                    starttime=starttime)
        value.clear_value()
    else:
        value = None

    threads = [RunThread() for i in range(1, 8)]

    for t in threads:
        t.start()

    time.sleep(totaltime)

    failed = not running[0]
    running[0] = False

    for t in threads:
        t.join()

    assert not failed, "One or more threads failed"
    if expiretime is None:
        expected = 1
    else:
        expected = totaltime / expiretime + 1
    assert CachedWidget.totalcreates <= expected, \
            "Number of creates %d exceeds expected max %d" % (CachedWidget.totalcreates, expected)

def test_memory_container(totaltime=10, expiretime=None, delay=0, threadlocal=False):
    _run_container_test(clsmap['memory'],
                  totaltime, expiretime, delay, threadlocal)

def test_dbm_container(totaltime=10, expiretime=None, delay=0):
    _run_container_test(clsmap['dbm'], totaltime, expiretime, delay, False)

def test_file_container(totaltime=10, expiretime=None, delay=0, threadlocal=False):
    _run_container_test(clsmap['file'], totaltime, expiretime, delay, threadlocal)

def test_memory_container_tlocal():
    test_memory_container(expiretime=15, delay=2, threadlocal=True)

def test_memory_container_2():
    test_memory_container(expiretime=12)

def test_memory_container_3():
    test_memory_container(expiretime=15, delay=2)

def test_dbm_container_2():
    test_dbm_container(expiretime=12)

def test_dbm_container_3():
    test_dbm_container(expiretime=15, delay=2)

def test_file_container_2():
    test_file_container(expiretime=12)

def test_file_container_3():
    test_file_container(expiretime=15, delay=2)

def test_file_container_tlocal():
    test_file_container(expiretime=15, delay=2, threadlocal=True)

def test_file_open_bug():
    """ensure errors raised during reads or writes don't lock the namespace open."""

    value = Value('test', clsmap['file']('reentrant_test', data_dir='./cache'))
    if os.path.exists(value.namespace.file):
        os.remove(value.namespace.file)

    value.set_value("x")

    f = open(value.namespace.file, 'w')
    f.write("BLAH BLAH BLAH")
    f.close()

    # TODO: do we have an assertRaises() in nose to use here ?
    try:
        value.set_value("y")
        assert False
    except:
        pass

    _synchronizers.clear()

    value = Value('test', clsmap['file']('reentrant_test', data_dir='./cache'))

    # TODO: do we have an assertRaises() in nose to use here ?
    try:
        value.set_value("z")
        assert False
    except:
        pass


def test_removing_file_refreshes():
    """test that the cache doesn't ignore file removals"""

    x = [0]
    def create():
        x[0] += 1
        return x[0]

    value = Value('test', 
                    clsmap['file']('refresh_test', data_dir='./cache'), 
                    createfunc=create, starttime=time.time()
                    )
    if os.path.exists(value.namespace.file):
        os.remove(value.namespace.file)
    assert value.get_value() == 1
    assert value.get_value() == 1
    os.remove(value.namespace.file)
    assert value.get_value() == 2


def teardown():
    import shutil
    shutil.rmtree('./cache', True)
