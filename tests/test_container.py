import os
import random
import time
import unittest
from beaker.container import *
from beaker.synchronization import synchronizers
import thread

def create(delay=0):
    global baton, totalcreates
    assert baton is None, "baton is not none , ident %r, this thread %r" % (baton, thread.get_ident())

    baton = thread.get_ident()
    try:    
        obj = object()
        time.sleep(delay)
        totalcreates += 1
        return obj
    finally:
        baton = None
        
def runthread(cclass, id, runningids, container, delay, kwargs):
    print "create thread %d starting" % id
    runningids.add(id)

    try:
        if not container:
            container = cclass(
                context=context, 
                namespace='test', 
                key='test', 
                createfunc=lambda: create(delay), 
                **kwargs
                )
            
        global running, totalgets
        try:
            while running:
                item = container.get_value()
                assert item is not None
                item = None
                totalgets += 1
                time.sleep(random.random() * .00001)
        except:
            running = False
            raise
    finally:
        print "create thread %d exiting" % id
        runningids.remove(id)

def _runtest(cclass, totaltime, expiretime, delay, threadlocal):
    print "\ntesting %s for %d secs with expiretime %s delay %d" % (
        cclass, totaltime, expiretime, delay)

    global running, starttime, baton, context, totalcreates, totalgets
    
    running = False
    starttime = time.time()
    baton = None
    context = ContainerContext()

    runningids = set()
    totalcreates = 0

    totalgets = 0
    
    kwargs = dict(
        expiretime=expiretime, 
        starttime = starttime)
    
    if cclass in (FileContainer, DBMContainer):
        kwargs['data_dir'] = './cache'

    if not threadlocal:
        container = cclass(
            context=context, 
            namespace='test', 
            key='test', 
            createfunc=lambda:create(delay), 
            **kwargs)
        container.clear_value()
    else:
        container = None
        
    running = True    
    for t in range(1, 20):
        thread.start_new_thread(runthread, (cclass, t, runningids, container, delay, kwargs))
        
    time.sleep(totaltime)
    
    failed = not running

    running = False

    while runningids:
        time.sleep(1)

    assert not failed

    print "total object creates %d" % totalcreates
    print "total object gets %d" % totalgets
    
    if expiretime is None:
        assert totalcreates == 1
    else:
        assert abs(totaltime / expiretime - totalcreates) <= 2

def test_memory_container(totaltime=10, expiretime=None, delay=0, threadlocal=False):
    _runtest(container_registry('memory'),
                  totaltime, expiretime, delay, threadlocal)

def test_dbm_container(totaltime=10, expiretime=None, delay=0):
    _runtest(container_registry('dbm'), totaltime, expiretime, delay, False)

def test_file_container(totaltime=10, expiretime=None, delay=0, threadlocal=False):
    _runtest(container_registry('file'), totaltime, expiretime, delay, threadlocal)

def test_memory_container_tlocal():
    test_memory_container(expiretime=5, delay=2, threadlocal=True)
    
def test_memory_container_2():
    test_memory_container(expiretime=2)

def test_memory_container_3():
    test_memory_container(expiretime=5, delay=2)

def test_dbm_container_2():
    test_dbm_container(expiretime=2)

def test_dbm_container_3():
    test_dbm_container(expiretime=5, delay=2)

def test_file_container_2():
    test_file_container(expiretime=2)
    
def test_file_container_3():
    test_file_container(expiretime=5, delay=2)

def test_file_container_tlocal():
    test_file_container(expiretime=5, delay=2, threadlocal=True)

def test_file_open_bug():
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
    # comment out line 147 of container.py, do_release_write_lock() inside of acquire_write_lock(), to illustrate
    try:
        container.set_value("y")
        assert False
    except:
        pass
        
    # 6. clear file synchronziers, rebuild the namespace / context etc. so a new Synchchronizer gets built (alternatively, just
    # access the same container from a different thread)
    synchronizers.clear()
    context.clear()
    container = container_registry('file')(context=context, namespace='reentrant_test', key='test', data_dir='./cache')
    
    # 7. acquire write lock hangs !
    try:
        container.set_value("z")
        assert False
    except:
        pass
