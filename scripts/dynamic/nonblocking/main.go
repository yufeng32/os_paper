// Standalone pattern reconstructions, not historical application builds.
// CASES.md maps every function to its pinned patch and states deviations.
package main

import (
	"encoding/json"
	"flag"
	"fmt"
	"math/rand"
	"os"
	"runtime"
	"runtime/debug"
	"strings"
	"sync"
)

type config struct {
	fixed, controlled bool
	seed              int64
}
type result struct {
	Case        string `json:"case"`
	Variant     string `json:"variant"`
	Schedule    string `json:"schedule"`
	Seed        int64  `json:"seed"`
	Symptom     bool   `json:"symptom"`
	Observation string `json:"observation"`
	Error       string `json:"error,omitempty"`
}
type finding struct {
	bad  bool
	note string
}
type experiment func(config) finding

var cases = map[string]experiment{
	"docker_4e262f638760":      stdinNotification,
	"docker_c1ad02ccc879":      logEventOwnership,
	"docker_1670914b8a56":      closurePair,
	"docker_825e3a66a419":      closureAPIVersion,
	"kubernetes_345f875c51c0":  proxyCalled,
	"kubernetes_647b826d697a":  namespaceOwnership,
	"kubernetes_3c345abafd02":  pluginSlice,
	"etcd_5d033c22afdf":        timerReuse,
	"etcd_c678dcbd9172":        revisionCounter,
	"etcd_91dc6b29a6e0":        progressInterval,
	"etcd_2c83362e63e6":        reconnectLock,
	"etcd_e129223dbeba":        watcherResume,
	"etcd_3ce31acda410":        contextString,
	"etcd_4bdfc0a46d28":        watchChannelReturn,
	"etcd_7f95780bfb5d":        raftChannelInit,
	"cockroachdb_d5a604c99d9e": checkpointFiles,
	"cockroachdb_4edda446686e": destroyStatus,
	"grpc_go_c6b46087ab92":     statusThenWrite,
	"grpc_go_b71aced4a2a1":     headersAfterClose,
	"grpc_go_a62701e4aa1d":     balancerMap,
	"grpc_go_87bcb38fba80":     balancerPointer,
	"boltdb_c69cb102ce8f":      closePendingTransaction,
	"boltdb_7fb06feea401":      transactionMetadata,
}

func main() {
	id := flag.String("case", "", "case ID from candidates.csv")
	variant := flag.String("variant", "buggy", "buggy or fixed")
	schedule := flag.String("schedule", "natural", "natural or controlled")
	seed := flag.Int64("seed", 1, "repeatable workload seed; scheduler is not deterministic")
	flag.Parse()
	fn, ok := cases[*id]
	if !ok || (*variant != "buggy" && *variant != "fixed") || (*schedule != "natural" && *schedule != "controlled") {
		fmt.Fprintln(os.Stderr, "invalid case, variant or schedule")
		os.Exit(2)
	}
	c := config{*variant == "fixed", *schedule == "controlled", *seed}
	r := result{Case: *id, Variant: *variant, Schedule: *schedule, Seed: *seed}
	func() {
		defer func() {
			if p := recover(); p != nil {
				s := fmt.Sprint(p)
				// Only case-specific original panic mechanisms count as target symptoms.
				expected := map[string]string{
					"grpc_go_c6b46087ab92": "send on closed channel",
					"etcd_4bdfc0a46d28":    "send on closed channel",
					"etcd_7f95780bfb5d":    "close of nil channel",
				}
				r.Symptom = expected[*id] != "" && strings.Contains(s, expected[*id])
				r.Observation = "panic: " + s
				if !r.Symptom {
					r.Error = "unexpected panic"
				}
				fmt.Fprintf(os.Stderr, "%s", debug.Stack())
			}
		}()
		f := fn(c)
		r.Symptom = f.bad
		r.Observation = f.note
	}()
	b, _ := json.Marshal(r)
	fmt.Println("RESULT " + string(b))
	if r.Error != "" {
		os.Exit(2)
	}
}

// A common launch gate precedes both conflicting accesses. It does NOT impose
// an order between accesses in the different workers. Wait only joins them.
func parallel(c config, fs ...func(*rand.Rand)) {
	var wg sync.WaitGroup
	gate := make(chan struct{})
	for i, f := range fs {
		wg.Add(1)
		go func(i int, f func(*rand.Rand)) {
			defer wg.Done()
			<-gate
			f(rand.New(rand.NewSource(c.seed + int64(i)*104729)))
		}(i, f)
	}
	close(gate)
	wg.Wait()
}

func yield(r *rand.Rand) {
	if r.Intn(4) == 0 {
		runtime.Gosched()
	}
}
