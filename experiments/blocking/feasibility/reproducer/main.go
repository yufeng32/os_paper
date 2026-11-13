// Minimal reconstruction (pattern level) of the Kubernetes blocking bug
// fixed by commit 991674380b7773d73afaeafeac6242bf3b6e6001
// ("Fix resync goroutine leak in ListAndWatch", pkg/client/cache/reflector.go).
//
// This file does NOT contain the original Kubernetes source. It re-implements
// only the control flow of the buggy / fixed resync goroutine, using plain
// standard-library code, so that the blocking behaviour can be observed on a
// modern machine without building the 2016 Kubernetes tree.
//
// Mode "buggy"  : resync goroutine can only leave the select loop through
//                 stopCh or through a Resync error. When ListAndWatch returns
//                 and cleanup() stops the resync timer, neither channel ever
//                 delivers again -> the goroutine is blocked forever.
// Mode "fixed"  : the fix adds cancelCh, closed by defer when ListAndWatch
//                 returns, and the goroutine selects on it -> it exits.

package main

import (
	"flag"
	"fmt"
	"runtime"
	"strings"
	"time"
)

// neverClosed simulates the reflector's root stopCh: during the scenario it
// stays open, so it cannot unblock the resync goroutine.
var neverClosed = make(chan struct{})

// resyncChan mirrors (*Reflector).resyncChan: it returns a channel that fires
// once after the (shortened) resync period, plus a cleanup func.
func resyncChan(d time.Duration) (<-chan time.Time, func()) {
	ch := make(chan time.Time, 1)
	timer := time.NewTimer(d)
	stop := make(chan struct{})
	go func() {
		select {
		case t := <-timer.C:
			select {
			case ch <- t:
			default:
			}
		case <-stop:
		}
	}()
	cleanup := func() {
		timer.Stop()
		close(stop)
	}
	return ch, cleanup
}

// storeResyncSuccess stands in for r.store.Resync() when it succeeds.
func storeResyncSuccess() error { return nil }

func listAndWatch(mode string) {
	resyncCh, cleanup := resyncChan(20 * time.Millisecond)
	defer cleanup()

	var cancelCh chan struct{}

	resyncerrc := make(chan error, 1)

	if mode == "fixed" {
		// ---- the fix: commit 991674380b7773d73afaeafeac6242bf3b6e6001 ----
		cancelCh = make(chan struct{})
		defer close(cancelCh)
	}

	go func() {
		for {
			if mode == "fixed" {
				select {
				case <-resyncCh:
				case <-neverClosed:
					return
				case <-cancelCh:
					return
				}
			} else {
				// ---- buggy version: no cancel path ----
				select {
				case <-resyncCh:
				case <-neverClosed:
					return
				}
			}

			if err := storeResyncSuccess(); err != nil {
				resyncerrc <- err
				return
			}
			cleanup()
			resyncCh, cleanup = resyncChan(20 * time.Millisecond)
		}
	}()

	// The rest of ListAndWatch (List + Watch loop). Here we simply let it
	// "return" immediately, which is exactly the situation that leaks the
	// goroutine: the function returns, the deferred cleanup() stops the
	// resync timer, and nobody tells the child goroutine to stop.
}

func countBlockedInChanReceive() int {
	buf := make([]byte, 1<<20)
	n := runtime.Stack(buf, true)
	stacks := string(buf[:n])
	blocked := 0
	for _, g := range strings.Split(stacks, "\n\n") {
		if strings.Contains(g, "chan receive") || strings.Contains(g, "select") {
			blocked++
		}
	}
	return blocked
}

func main() {
	mode := flag.String("mode", "buggy", "buggy | fixed")
	calls := flag.Int("calls", 5, "how many ListAndWatch calls to simulate (i.e. how many times the reflector re-listens)")
	flag.Parse()

	runtime.GOMAXPROCS(1)

	baseline := runtime.NumGoroutine()
	fmt.Printf("[mode=%s] goroutines at start: %d\n", *mode, baseline)

	for i := 1; i <= *calls; i++ {
		listAndWatch(*mode)
		time.Sleep(30 * time.Millisecond) // let the resync timer fire in between
		fmt.Printf("[mode=%s] after ListAndWatch call #%d: goroutines = %d\n",
			*mode, i, runtime.NumGoroutine())
	}

	time.Sleep(120 * time.Millisecond) // give leaked goroutines time to park
	end := runtime.NumGoroutine()
	fmt.Printf("[mode=%s] goroutines at end: %d (start was %d, growth = %d)\n",
		*mode, end, baseline, end-baseline)
	fmt.Printf("[mode=%s] goroutines parked in chan receive/select at end: %d\n",
		*mode, countBlockedInChanReceive())

	if end > baseline {
		fmt.Printf("[mode=%s] VERDICT: BLOCKING REPRODUCED - %d goroutine(s) stuck, cannot make progress\n",
			*mode, end-baseline)
	} else {
		fmt.Printf("[mode=%s] VERDICT: NO BLOCKING - goroutine count back to baseline\n", *mode)
	}

	if end > baseline {
		fmt.Printf("\n--- goroutine dump (first 3 stacks) ---\n")
		buf := make([]byte, 1<<20)
		n := runtime.Stack(buf, true)
		parts := strings.Split(string(buf[:n]), "\n\n")
		for i, p := range parts {
			if i >= 3 {
				break
			}
			fmt.Println(p)
			fmt.Println()
		}
	}
}
