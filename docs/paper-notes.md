# Reading Notes: Understanding Real-World Concurrency Bugs in Go

Source: Tu et al., [ASPLOS 2019 paper](https://songlh.github.io/paper/go-study.pdf). Page numbers follow PDF order. Paper results and our measurements are identified separately.

## 1. Research question

Go makes concurrent tasks easy to create and encourages communication through channels. Does this also make concurrent programs easier to write correctly? The authors investigate actual failures: causes, fixes, and whether existing detectors find them. This is an empirical bug study, rather than a new scheduling algorithm or detector.

The study covers 171 bugs in Docker, Kubernetes, etcd, CockroachDB, gRPC, and BoltDB. Its evidence concerns collected, fixed defects, not a universal failure probability for all Go programs (Sections 1 and 4, pp. 1-2 and 5-6).

## 2. Concepts before the results

A **goroutine** is a concurrent task scheduled by the Go runtime. Task execution order can change between runs. Correctness must hold for the relevant possible orders, not just the order seen in one successful run.

**Shared memory** means tasks access the same data. A mutex can coordinate access: one task holds the lock while updating data, and another waits. Incorrect locking can leave data unprotected or tasks waiting forever.

**Message passing** means tasks exchange data or signals through mechanisms such as channels. An unbuffered send waits for a matching receiver; a buffered channel can temporarily store values while capacity remains. Channels still require correct coordination of task lifetimes (Section 2, pp. 2-3).

## 3. Figure 1: a timeout leaves a worker behind

The Kubernetes example on p. 2 starts a worker to calculate a request result. The parent waits for either the result or a timeout. If the timeout wins, the parent returns. Later, the worker sends on an unbuffered channel, but the parent is no longer receiving. The worker remains blocked.

The sequence is: start worker -> parent times out -> parent returns -> worker finishes -> worker waits forever while sending. This is a message-passing blocking bug even if the server continues handling other requests.

The repair provides capacity for the single result, allowing that send to finish after the parent leaves. Adding a buffer is not a universal channel repair: this example has one result to store. A standalone implementation would demonstrate the mechanism, but would not reproduce the historical application's detector evaluation.

## 4. Method and two classification dimensions

The authors searched concurrency-related commit messages, sampled candidates, and manually examined fixes and linked reports (Section 4, p. 5). The repository provides annotations and patch histories rather than a single ready-to-run benchmark suite.

| Dimension | Categories | Meaning |
| --- | --- | --- |
| Behavior | Blocking / non-blocking | Whether one or more goroutines unintentionally cannot proceed |
| Cause | Shared memory / message passing | Which communication mechanism was misused |

Figure 1 is both blocking and message-passing related. Blocking is broader than circular-wait deadlock; non-blocking is broader than a data race. The four Table 5 columns are not four disjoint groups.

## 5. Main evidence and limits

| Reference | Authors' reported result | Meaning |
| --- | --- | --- |
| Table 5, p. 5 | 85 blocking, 86 non-blocking; 105 shared-memory, 66 message-passing bugs | Distribution within the studied sample |
| Table 6, p. 6 | 49 of 85 blocking bugs involve message passing | Channels and related mechanisms still produce blocking errors |
| Table 8, p. 8 | Built-in deadlock detection finds 2 of 21 reproduced blocking bugs | Detection misses blocking bugs in this tested sample |
| Table 12, p. 11 | Race detection finds 10 of 20 tested bugs within the repeated-run budget | Race detection does not cover every tested non-blocking bug |

These are paper results, not ours. The detector samples are smaller than 171. Triggering the intended defect and getting a detector report are separate observations. The paper's counts are not a controlled, general comparison of per-operation failure rates between channels and locks.

## 6. Our first reproduction task

Reconstruct Table 5 from the two detailed workbook sheets, retaining original identifiers and flags, and compare against the paper rather than the workbook summaries.

Our audit recovers 171 behavior records, including two BoltDB issue-ID records a full-hash filter misses. One Kubernetes blocking row has both cause flags set, yielding 106 shared-memory flags instead of 105. The conflicting annotation stays unresolved; see [method and evidence](reproduction-plan.md).

This supplies a first traceable data result. It does not reproduce collection/sampling, independently validate every label, or execute Go defects. Next, identify a historical case, recover the buggy revision and triggering input, and separately record the symptom and detector output.
