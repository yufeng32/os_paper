// Pattern-level reproducers for a reduced-scale Table 8 (blocking bug -> Go built-in
// deadlock detector). One binary, selected by -case; -mode A = natural behaviour,
// -mode B = force every goroutine asleep via select{}.
//
// Each case re-implements only the control flow that caused the original blocking bug,
// extracted from the fix-commit patch in system-pclub/go-concurrency-bugs. The historical
// 2016-era applications are pre-modules and cannot be built with a modern toolchain, so
// this is a pattern-level reconstruction, not the original program (documented deviation).
package main

import (
	"flag"
	"fmt"
	"io"
	"os"
	"os/exec"
	"runtime"
	"sync"
	"time"
)

func main() {
	// moby#256 child process: write a lot to stderr, then exit.
	if os.Getenv("DYN_CHILD") == "1" {
		moby256Child()
		return
	}
	caseID := flag.String("case", "", "case id")
	mode := flag.String("mode", "A", "A=natural behaviour, B=force all-asleep")
	flag.Parse()
	switch *caseID {
	case "docker_17176":
		caseDocker17176(*mode)
	case "etcd_5509":
		caseEtcd5509(*mode)
	case "etcd_4474":
		caseEtcd4474(*mode)
	case "grpc_1850":
		caseGrpc1850(*mode)
	case "grpc_1293":
		caseGrpc1293(*mode)
	case "moby_27782":
		caseMoby27782(*mode)
	case "grpc_1459":
		caseGrpc1459(*mode)
	case "moby_256":
		caseMoby256(*mode)
	default:
		fmt.Fprintf(os.Stderr, "unknown case %q\n", *caseID)
		os.Exit(2)
	}
}

// finish prints a one-line result to stderr, then decides how this mode should end:
//   - mode B: always block on select{} so every goroutine is asleep (detector condition).
//   - mode A with detectInA: main blocks too, mirroring a real program that hangs.
//   - mode A otherwise: main returns, the process exits 0, and the detector does NOT fire.
func finish(mode string, detectInA bool, note string) {
	fmt.Fprintf(os.Stderr, "[case] mode=%s goroutines=%d %s\n", mode, runtime.NumGoroutine(), note)
	if mode == "B" {
		select {}
	}
	if detectInA {
		<-make(chan struct{})
	}
}

// docker#17176 (Mutex): cleanupDeletedDevices takes devices.Lock() and, on the
// nrDeletedDevices == 0 early-return path, forgets Unlock. The lock stays held, so any
// later Lock() blocks forever. Fix commit 2f16895ee948.
func caseDocker17176(mode string) {
	var mu sync.Mutex
	mu.Lock() // early return without Unlock (the bug)
	go func() {
		mu.Lock() // blocks forever: the mutex was leaked
		mu.Unlock()
	}()
	time.Sleep(80 * time.Millisecond)
	finish(mode, false, "1 goroutine blocked on a leaked mutex")
}

// etcd#5509 (Mutex): acquire() locked r.client.mu then r.mu while another path locked
// them in the opposite order -> ABBA circular deadlock. Fix commit 1d8813052292.
// A WaitGroup barrier makes the ABBA deterministic: both goroutines take their first
// lock, wait for each other, then both reach for the lock the other one holds.
func caseEtcd5509(mode string) {
	var a, b sync.Mutex
	var ready sync.WaitGroup
	ready.Add(2)
	go func() {
		a.Lock()
		ready.Done()
		ready.Wait() // both hold their first lock before either reaches for the second
		b.Lock()     // blocks: the other goroutine holds b
		a.Unlock()
		b.Unlock()
	}()
	go func() {
		b.Lock()
		ready.Done()
		ready.Wait()
		a.Lock() // blocks: the other goroutine holds a
		b.Unlock()
		a.Unlock()
	}()
	ready.Wait()
	time.Sleep(80 * time.Millisecond)
	finish(mode, true, "2 goroutines circularly deadlocked on two mutexes (ABBA)")
}

// etcd#4474 (Chan): the raft replay path sends an unconditional nil on the unbuffered
// commitC with no receiver, so it blocks forever. Fix commit 0cb304ec6101 adds a
// select with a stopc escape.
func caseEtcd4474(mode string) {
	commitC := make(chan string) // unbuffered
	go func() {
		commitC <- "nil" // bug: no receiver -> blocks forever
	}()
	time.Sleep(80 * time.Millisecond)
	finish(mode, false, "1 goroutine blocked sending on an unbuffered channel")
}

// grpc#1850 (Chan): a flow-control token is acquired and, on the error path, never
// returned to the pool, so the next acquire blocks forever. Fix commit 484b3ebb4ab5
// adds the token back. The pool is modelled as a 1-slot buffered channel.
func caseGrpc1850(mode string) {
	quota := make(chan struct{}, 1)
	quota <- struct{}{} // one token available
	<-quota             // acquire it
	// bug: the error path returns without `quota <- struct{}{}`
	go func() {
		<-quota // blocks: the pool is empty and is never refilled
	}()
	time.Sleep(80 * time.Millisecond)
	finish(mode, false, "1 goroutine blocked acquiring a leaked flow-control token")
}

// grpc#1293 (Chan): CloseStream deletes the active stream without writing the error to
// it, so an in-flight RecvMsg blocks forever. Fix commit 7df48bee8829 writes recvMsg{err}
// before deletion.
func caseGrpc1293(mode string) {
	msgCh := make(chan string) // stream message channel
	go func() {
		<-msgCh // RecvMsg blocks forever: the stream was deleted, nothing is sent
	}()
	time.Sleep(80 * time.Millisecond)
	finish(mode, false, "1 goroutine blocked receiving a message that is never sent")
}

// moby#27782 (Chan + other): the only reader of an unbuffered inotify-like event channel
// is inside Close() waiting for a later event, so the producer's first send blocks and the
// later event can never be produced -> circular. Fix commit a69a59ffc7e3 decouples removal
// from reading via a context-cancel signal.
func caseMoby27782(mode string) {
	events := make(chan int) // unbuffered event channel
	go func() {
		events <- 1 // IN_MODIFY: blocks because there is no receiver
		events <- 2 // IN_IGNORE: would arrive only after 1 is delivered
	}()
	time.Sleep(80 * time.Millisecond)
	// The consumer is "inside Close()" waiting for IN_IGNORE and is not reading events.
	finish(mode, true, "consumer waits for a later event while the producer is blocked sending an earlier one")
}

// grpc#1459 (Chan + mutex): the keepalive goroutine holds the transport mutex while
// waiting on the awakenKeepalive channel, so the next NewStream/Close blocks on the mutex.
// Fix commit c29d6389e66f refills awakenKeepalive.
func caseGrpc1459(mode string) {
	var mu sync.Mutex
	awaken := make(chan struct{}, 1)
	go func() {
		mu.Lock()
		<-awaken // waits (holding mu) for a refill that never comes
		mu.Unlock()
	}()
	time.Sleep(50 * time.Millisecond)
	go func() {
		mu.Lock() // next stream: blocks on mu held by keepalive
		mu.Unlock()
	}()
	time.Sleep(50 * time.Millisecond)
	finish(mode, true, "keepalive holds the mutex while waiting; the next stream blocks on the mutex")
}

// moby#256 (messaging library): CmdStream copies the child's stdout first, then drains
// stderr. If the child writes enough to stderr, the stderr pipe fills, the child blocks,
// and the parent blocks reading stdout -> a deadlock that is NOT on a Go primitive, so the
// Go deadlock detector cannot fire even in forced mode. Fix commit 58befe308172 reads
// stdout and stderr in two goroutines.
func moby256Child() {
	buf := make([]byte, 1024)
	for i := 0; i < 4096; i++ { // ~4 MB to stderr, enough to fill the pipe buffer
		os.Stderr.Write(buf)
	}
	os.Exit(0)
}

func caseMoby256(mode string) {
	cmd := exec.Command(os.Args[0])
	cmd.Env = append(os.Environ(), "DYN_CHILD=1")
	stdout, err := cmd.StdoutPipe()
	if err != nil {
		fmt.Fprintln(os.Stderr, err)
		os.Exit(2)
	}
	stderr, err := cmd.StderrPipe()
	if err != nil {
		fmt.Fprintln(os.Stderr, err)
		os.Exit(2)
	}
	if err := cmd.Start(); err != nil {
		fmt.Fprintln(os.Stderr, err)
		os.Exit(2)
	}
	// BUG: read stdout first; stderr is never drained, so the child blocks once the
	// stderr pipe buffer is full and the parent blocks here on the stdout read.
	io.Copy(io.Discard, stdout)
	io.Copy(io.Discard, stderr)
	cmd.Wait()
	finish(mode, false, "should not reach here (pipe deadlock)")
}
