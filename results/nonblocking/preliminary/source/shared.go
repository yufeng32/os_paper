package main

import (
	"context"
	"fmt"
	"math/rand"
	"runtime"
	"sync"
	"sync/atomic"
)

// Docker c1ad02cc: the producer reuses an input object after putting its
// pointer on a channel. Copy the input and its event slice before publishing.
func logEventOwnership(c config) finding {
	type input struct {
		events   []int
		sequence int
	}
	ch := make(chan *input, 1)
	done := make(chan bool, 1)
	go func() {
		bad := false
		for p := range ch {
			if p.sequence != 1 || p.events[0] != 1 {
				bad = true
			}
			runtime.Gosched()
		}
		done <- bad
	}()
	p := &input{[]int{1}, 1}
	for i := 0; i < 64; i++ {
		p.sequence = 1
		p.events[0] = 1
		published := p
		if c.fixed {
			published = &input{append([]int(nil), p.events...), p.sequence}
		}
		ch <- published
		p.sequence = 2
		p.events[0] = 2
		runtime.Gosched()
	}
	close(ch)
	return finding{<-done, "published event must retain the values present at publication"}
}

func closurePair(c config) finding {
	const n = 64
	var wg sync.WaitGroup
	values := make(chan int, n)
	gate := make(chan struct{})
	for _, pair := range [][2]int{{1, 10}, {2, 20}, {3, 30}, {4, 40}, {5, 50}, {6, 60}, {7, 70}, {8, 80}} {
		// Go 1.20 reuses pair across range iterations, as in the upstream test.
		for j := 0; j < n/8; j++ {
			wg.Add(1)
			if c.fixed {
				go func(x int) {
					defer wg.Done()
					if c.controlled {
						<-gate
					}
					values <- x
				}(pair[0])
			} else {
				go func() {
					defer wg.Done()
					if c.controlled {
						<-gate
					}
					values <- pair[0]
				}()
			}
		}
		runtime.Gosched()
	}
	close(gate)
	wg.Wait()
	close(values)
	counts := make(map[int]int)
	for v := range values {
		counts[v]++
	}
	bad := false
	for i := 1; i <= 8; i++ {
		if counts[i] != n/8 {
			bad = true
		}
	}
	return finding{bad, fmt.Sprintf("per-header counts=%v; expected eight of each", counts)}
}

func closureAPIVersion(c config) finding {
	var wg sync.WaitGroup
	versions := make(chan int, 5)
	gate := make(chan struct{})
	for i := 17; i <= 21; i++ {
		wg.Add(1)
		if c.fixed {
			go func(i int) {
				defer wg.Done()
				if c.controlled {
					<-gate
				}
				versions <- i
			}(i)
		} else {
			go func() {
				defer wg.Done()
				if c.controlled {
					<-gate
				}
				versions <- i
			}()
		}
		if !c.controlled {
			runtime.Gosched()
		}
	}
	close(gate)
	wg.Wait()
	close(versions)
	counts := make(map[int]int)
	for v := range versions {
		counts[v]++
	}
	bad := false
	for i := 17; i <= 21; i++ {
		if counts[i] != 1 {
			bad = true
		}
	}
	return finding{bad, fmt.Sprintf("API versions=%v; expected 17..21 once each", counts)}
}

// Kubernetes 345f875c: a test callback sets called while another goroutine
// examines it. The actual patch replaces the bool with an atomic counter.
func proxyCalled(c config) finding {
	var called bool
	var times int32
	seen := 0
	parallel(c, func(r *rand.Rand) {
		for i := 0; i < 256; i++ {
			if c.fixed {
				atomic.AddInt32(&times, 1)
			} else {
				called = true
			}
			yield(r)
		}
	}, func(r *rand.Rand) {
		for i := 0; i < 256; i++ {
			if c.fixed {
				if atomic.LoadInt32(&times) > 0 {
					seen++
				}
			} else {
				if called {
					seen++
				}
			}
			yield(r)
		}
	})
	return finding{false, fmt.Sprintf("callback state observed %d times; race reporting is separate from visible output", seen)}
}

// Kubernetes 647b826d: the informer store returns a shared object. Clone all
// mutable nested data before modifying it, while a store reader remains active.
func namespaceOwnership(c config) finding {
	type namespace struct{ labels []int }
	original := &namespace{[]int{7}}
	changed := false
	parallel(c, func(r *rand.Rand) {
		p := original
		if c.fixed {
			p = &namespace{append([]int(nil), original.labels...)}
		}
		for i := 0; i < 256; i++ {
			p.labels[0] = i
			yield(r)
		}
	}, func(r *rand.Rand) {
		for i := 0; i < 256; i++ {
			if original.labels[0] != 7 {
				changed = true
			}
			yield(r)
		}
	})
	return finding{changed, "shared informer object must not be modified by a reconciler"}
}

// Kubernetes 3c345aba: return a slice header under the same RWMutex used
// for append. The reconstruction only inspects immutable entries and length.
func pluginSlice(c config) finding {
	var mu sync.RWMutex
	items := make([]int, 0, 256)
	lengths := 0
	parallel(c, func(r *rand.Rand) {
		for i := 0; i < 256; i++ {
			mu.Lock()
			items = append(items, i)
			mu.Unlock()
			yield(r)
		}
	}, func(r *rand.Rand) {
		for i := 0; i < 256; i++ {
			var snapshot []int
			if c.fixed {
				mu.RLock()
				snapshot = items
				mu.RUnlock()
			} else {
				snapshot = items
			}
			lengths += len(snapshot)
			yield(r)
		}
	})
	return finding{false, fmt.Sprintf("sum of observed slice lengths=%d; entries remain immutable", lengths)}
}

func revisionCounter(c config) finding {
	var rev int64
	parallel(c, func(r *rand.Rand) {
		for i := 0; i < 256; i++ {
			if c.fixed {
				atomic.AddInt64(&rev, 1)
			} else {
				rev++
			}
			yield(r)
		}
	}, func(r *rand.Rand) {
		for i := 0; i < 256; i++ {
			if c.fixed {
				atomic.StoreInt64(&rev, int64(i))
			} else {
				rev = int64(i)
			}
			yield(r)
		}
	})
	return finding{false, "increment and SetRev exercised; no fixed final value is specified for concurrent stores"}
}

// etcd 91dc6b29 moves the interval update before cluster creation, in addition
// to using an atomic store. Keep that ordering: a plain read is NOT treated as
// safe merely because the writer was changed to an atomic store.
func progressInterval(c config) finding {
	var interval int32 = 600000
	total := int64(0)
	read := func(r *rand.Rand) {
		for i := 0; i < 256; i++ {
			total += int64(interval)
			yield(r)
		}
	}
	if c.fixed {
		atomic.StoreInt32(&interval, 3000)
		parallel(c, read)
	} else {
		parallel(c, read, func(r *rand.Rand) {
			for i := 0; i < 256; i++ {
				interval = 3000
				yield(r)
			}
		})
	}
	return finding{false, fmt.Sprintf("interval read sum=%d; fixed configuration precedes server startup", total)}
}

func reconnectLock(c config) finding {
	var mu sync.Mutex
	connection := 0
	update := func(r *rand.Rand) {
		for i := 0; i < 128; i++ {
			if c.fixed {
				mu.Lock()
			}
			next := connection + 1 // retryConnection reads the active connection
			yield(r)
			if !c.fixed {
				mu.Lock()
			}
			connection = next
			mu.Unlock()
		}
	}
	parallel(c, update, update)
	return finding{connection != 256, fmt.Sprintf("connection generations=%d; expected 256 serialized replacements", connection)}
}

type blankContext struct{ context.Context }

func (*blankContext) String() string { return "(blankCtx)" }

// Go 1.7 valueCtx.String used fmt to traverse its value. Go 1.20 instead
// prints <not Stringer> for this value. Reconstruct that historical library
// behavior explicitly; do not claim the current stdlib still has this path.
type historicalValueContext struct {
	context.Context
	value interface{}
}

func (h *historicalValueContext) String() string {
	return fmt.Sprintf("historical context value: %#v", h.value)
}

// etcd 3ce31acd: context formatting traverses a mutable value (as x/net/trace
// did). Fixed wraps the reconstructed historical context with a constant String.
func contextString(c config) finding {
	data := &struct{ Value int }{}
	var ctx context.Context = &historicalValueContext{context.Background(), data}
	var printable fmt.Stringer = ctx.(fmt.Stringer)
	if c.fixed {
		printable = &blankContext{ctx}
	}
	parallel(c, func(r *rand.Rand) {
		for i := 0; i < 128; i++ {
			data.Value = i
			yield(r)
		}
	}, func(r *rand.Rand) {
		for i := 0; i < 128; i++ {
			_ = printable.String()
			yield(r)
		}
	})
	return finding{false, "mutable context value formatted; no visible-output corruption oracle"}
}

func checkpointFiles(c config) finding {
	var mu sync.Mutex
	files := make([]int, 0, 512)
	var count int
	parallel(c, func(r *rand.Rand) {
		for i := 0; i < 256; i++ {
			mu.Lock()
			files = append(files, i)
			mu.Unlock()
			yield(r)
		}
	}, func(r *rand.Rand) {
		for i := 0; i < 128; i++ {
			mu.Lock()
			var checkpoint []int
			if c.fixed {
				checkpoint = append([]int(nil), files...)
			}
			mu.Unlock()
			if !c.fixed {
				checkpoint = append([]int(nil), files...)
			}
			count += len(checkpoint)
			yield(r)
		}
	})
	return finding{false, fmt.Sprintf("checkpoint copies read %d entries; snapshot must be taken under mu", count)}
}

func destroyStatus(c config) finding {
	var mu sync.Mutex
	errCode := 1
	observed := 0
	parallel(c, func(r *rand.Rand) {
		for i := 0; i < 256; i++ {
			mu.Lock()
			errCode = i + 1
			mu.Unlock()
			yield(r)
		}
	}, func(r *rand.Rand) {
		for i := 0; i < 256; i++ {
			mu.Lock()
			var local int
			if c.fixed {
				local = errCode
			}
			mu.Unlock()
			if !c.fixed {
				local = errCode
			}
			observed = local
			yield(r)
		}
	})
	return finding{false, fmt.Sprintf("error snapshot=%d; mutable error field must be copied before Unlock", observed)}
}

// gRPC b71aced4: after headerChan closes the receiver reads encoding without
// taking mu. A later header must not overwrite it, even while holding mu.
func headersAfterClose(c config) finding {
	var mu sync.Mutex
	headerDone := true
	encoding := "gzip"
	corrupted := false
	parallel(c, func(r *rand.Rand) {
		for i := 0; i < 128; i++ {
			mu.Lock()
			if !c.fixed || !headerDone {
				encoding = "late"
			}
			mu.Unlock()
			yield(r)
		}
	}, func(r *rand.Rand) {
		for i := 0; i < 128; i++ {
			if encoding != "gzip" {
				corrupted = true
			}
			yield(r)
		}
	})
	return finding{corrupted, "published header encoding must remain gzip after headerDone"}
}

func balancerMap(c config) finding {
	var mu sync.RWMutex
	subConns := map[int]bool{0: true}
	parallel(c, func(r *rand.Rand) {
		for i := 0; i < 128; i++ {
			if c.fixed {
				mu.Lock()
			}
			subConns[i] = true
			delete(subConns, i-1)
			if c.fixed {
				mu.Unlock()
			}
			yield(r)
		}
	}, func(r *rand.Rand) {
		for i := 0; i < 128; i++ {
			if c.fixed {
				mu.RLock()
			}
			for range subConns { /* removeAddrConn work omitted */
			}
			if c.fixed {
				mu.RUnlock()
			}
			yield(r)
		}
	})
	return finding{false, "balancer map mutation and watcher iteration exercised"}
}

func balancerPointer(c config) finding {
	var mu sync.Mutex
	pointer := new(int)
	observed := 0
	parallel(c, func(r *rand.Rand) {
		for i := 0; i < 128; i++ {
			if c.fixed {
				mu.Lock()
			}
			value := i
			pointer = &value
			if c.fixed {
				mu.Unlock()
			}
			yield(r)
		}
	}, func(r *rand.Rand) {
		for i := 0; i < 128; i++ {
			mu.Lock()
			observed += *pointer
			mu.Unlock()
			yield(r)
		}
	})
	return finding{false, fmt.Sprintf("wrapper values sum=%d; publication must use the reader's mutex", observed)}
}

// Bolt 7fb06fee: transactions must own a meta copy. This version retains
// transaction-open locking so copying does not itself race with a writer.
func transactionMetadata(c config) finding {
	var mu sync.Mutex
	type meta struct{ txnid int }
	shared := &meta{1}
	mu.Lock()
	snapshot := shared
	if c.fixed {
		local := *shared
		snapshot = &local
	}
	mu.Unlock()
	changed := false
	parallel(c, func(r *rand.Rand) {
		for i := 0; i < 128; i++ {
			mu.Lock()
			shared.txnid = i + 2
			mu.Unlock()
			yield(r)
		}
	}, func(r *rand.Rand) {
		for i := 0; i < 128; i++ {
			if snapshot.txnid != 1 {
				changed = true
			}
			yield(r)
		}
	})
	return finding{changed, "read transaction metadata must retain its opening transaction ID"}
}
