package main

import (
	"fmt"
	"runtime"
	"sync"
	"sync/atomic"
	"time"
)

// Docker 4e262f63: both ready and cancellation can be selectable. The old
// select can discard a required stdin-close notification. Fixed rechecks ready.
func stdinNotification(c config) finding {
	missed := 0
	for i := 0; i < 64; i++ {
		ready, canceled := make(chan struct{}), make(chan struct{})
		close(ready)
		close(canceled)
		sent := false
		if c.fixed {
			select {
			case <-ready:
			case <-canceled:
			}
			select {
			case <-ready:
				sent = true
			default:
			}
		} else {
			select {
			case <-ready:
				sent = true
			case <-canceled:
			}
		}
		if !sent {
			missed++
		}
	}
	return finding{missed > 0, fmt.Sprintf("missed stdin-close notifications=%d/64 with both cases ready", missed)}
}

// gRPC c6b46087: reproduce the upstream regression test's sequential
// WriteStatus followed by Write. Do is the transport's enqueue operation.
// Buggy closes writes but leaves closedCh open; fixed shuts down first.
func statusThenWrite(c config) finding {
	writes := make(chan func(), 2)
	closedCh := make(chan struct{})
	var writeStatusMu sync.Mutex
	do := func() bool {
		select {
		case <-closedCh:
			return false
		default:
		}
		select {
		case writes <- func() {}:
			return true
		case <-closedCh:
			return false
		}
	}
	if c.fixed {
		writeStatusMu.Lock()
	}
	ok := do() // WriteStatus enqueues trailers
	if c.fixed && ok {
		close(closedCh)
	}
	close(writes)
	if c.fixed {
		writeStatusMu.Unlock()
	}
	do() // Write after WriteStatus must return, not send on a closed channel.
	return finding{false, "Write following WriteStatus was rejected without a panic"}
}

// etcd 4bdfc0a4: serveStream can close the request's buffered return channel
// before addStream has published the watch channel. Fixed publishes first.
func watchChannelReturn(c config) finding {
	retc := make(chan chan int, 1)
	ret := make(chan int)
	done := make(chan struct{})
	serveStream := func() { close(retc); close(done) }
	if c.fixed {
		retc <- ret
		go serveStream()
	} else {
		go serveStream()
		if c.controlled {
			<-done
		} else {
			runtime.Gosched()
		}
		// In natural mode the send and close are not synchronized.
		retc <- ret
	}
	<-done
	published, ok := <-retc
	return finding{!ok || published != ret, "subscriber channel is published before stream cleanup closes retc"}
}

// etcd 7f95780b: defer captures its channel argument at registration time.
// Registering it before raft start initializes done/stopped can capture nil.
func raftChannelInit(c config) finding {
	type raft struct{ stopped, done chan struct{} }
	r := &raft{}
	if c.fixed {
		r.stopped = make(chan struct{})
		r.done = make(chan struct{})
	}
	func() {
		defer close(r.done) // argument captured now, even if r.done changes later
		if !c.fixed {
			r.stopped = make(chan struct{})
			r.done = make(chan struct{})
		}
	}()
	return finding{false, "deferred shutdown captured an initialized channel"}
}

// etcd e129223d: owner goroutine advances lastRev while reconnect reads it.
// Fixed sends -1 on resumec to pause the owner before reading, then resumes.
func watcherResume(c config) finding {
	resume := make(chan int)
	done := make(chan bool, 1)
	ready := make(chan struct{})
	lastRev := 1
	go func() {
		close(ready)
		paused := false
		for {
			select {
			case revision := <-resume:
				if revision == -1 {
					paused = true
					continue
				}
				done <- revision != lastRev
				return
			default:
				if !paused {
					lastRev++
				}
				runtime.Gosched()
			}
		}
	}()
	<-ready
	if c.fixed {
		resume <- -1
	} else {
		runtime.Gosched()
	}
	revision := lastRev // resumeWatchers reads the owner-maintained revision
	if !c.fixed {
		runtime.Gosched()
	}
	resume <- revision
	return finding{<-done, "reconnect revision must equal the paused stream's lastRev"}
}

// Bolt c69cb102: Close must wait for an active write transaction before
// releasing resources. Atomic flags make this ordering violation observable
// without adding an unrelated data race to the reconstruction.
func closePendingTransaction(c config) finding {
	var rwlock sync.Mutex
	var active, closed int32
	rwlock.Lock()
	atomic.StoreInt32(&active, 1)
	started, done := make(chan struct{}), make(chan struct{})
	var early int32
	go func() {
		close(started)
		if c.fixed {
			rwlock.Lock()
			defer rwlock.Unlock()
		}
		if atomic.LoadInt32(&active) == 1 {
			atomic.StoreInt32(&early, 1)
		}
		atomic.StoreInt32(&closed, 1)
		close(done)
	}()
	<-started
	if c.controlled {
		// Give Close an opportunity to run while a transaction is definitely open.
		// This diagnostic wait is excluded from natural detector statistics.
		time.Sleep(time.Millisecond)
	} else {
		for i := 0; i < 16; i++ {
			runtime.Gosched()
		}
	}
	atomic.StoreInt32(&active, 0)
	rwlock.Unlock()
	<-done
	return finding{atomic.LoadInt32(&early) == 1, fmt.Sprintf("closed-before-transaction-end=%t; closed=%d", early == 1, closed)}
}

// etcd 5d033c22: keep the actual AfterFunc/Reset API pattern rather than
// inventing an unsafe user variable to force a race on a modern runtime.
// This candidate may remain unobserved: library internals have changed.
func timerReuse(c config) finding {
	var callbacks int32
	work := func() { time.Sleep(100 * time.Microsecond) }
	if c.fixed {
		for i := 0; i < 2; i++ {
			done := make(chan struct{})
			go func() { work(); close(done) }()
			select {
			case <-done:
			case <-time.After(100 * time.Millisecond):
				return finding{false, "simulated I/O exceeded diagnostic watchdog; target race not established"}
			}
		}
	} else {
		timer := time.AfterFunc(100*time.Millisecond, func() { atomic.AddInt32(&callbacks, 1) })
		work()
		timer.Reset(100 * time.Millisecond)
		work()
		timer.Stop()
	}
	return finding{false, fmt.Sprintf("AfterFunc/Reset historical library pattern exercised; callbacks=%d; no user-data race injected", atomic.LoadInt32(&callbacks))}
}
