# Case Info — Kubernetes blocking bug (ListAndWatch resync goroutine leak)

## 1. Identity

| Field | Value |
| --- | --- |
| Project | Kubernetes (`kubernetes/kubernetes`) |
| Bug type (paper taxonomy) | **Blocking bug** |
| Root cause dimension (paper taxonomy) | **Message passing** (goroutine blocked on a channel it will never receive from again) |
| Bug-inducing commit (buggy version) | `6abb4723571fc6b9e4dc05807511569dfc865f83` (commit date 2016-12-02, "Merge pull request #37720 from freehan/lb-src-update") |
| Fix commit | `991674380b7773d73afaeafeac6242bf3b6e6001` (author date 2016-10-25, commit date 2016-12-02; Tatsuhiro Tsujikawa, "Fix resync goroutine leak in ListAndWatch") |
| File touched by the fix | `pkg/client/cache/reflector.go` (only one file) |
| Data source | `system-pclub/go-concurrency-bugs`, `blocking-bugs/kubernetes/991674380b7773d73afaeafeac6242bf3b6e6001.txt` (the file name is the fix commit) |
| Paper table this bug belongs to | Table 5 / Table 6 (Kubernetes, blocking + message passing); Table 8 (blocking bugs reproduced and fed to the Go deadlock detector) |

## 1a. Commit relationship — verified, not inferred

The first check raised a fair question: the fix commit is dated 2016-10-25 while its parent
`6abb4723…` is dated 2016-12-02, i.e. the parent looks *newer* than the child. That is not an error,
and it is not resolved by trusting either date alone. It is resolved by the two timestamps Git
stores separately, plus the file content:

| Object | author date | commit (committer) date |
| --- | --- | --- |
| fix `99167438…` | 2016-10-25 02:20:35 | 2016-12-02 06:26:25 |
| buggy parent `6abb4723…` | 2016-12-02 02:21:39 | 2016-12-02 02:21:39 |

Reading: the patch was **authored on 10-25** and **committed (rebased onto the then-current master)
on 12-02 at 06:26**, which is after the parent's 02:21 that same day. Author date < parent date <
committer date is a normal rebase/merge pattern, so the parent/child relation holds.

Second check — does the fix diff really correspond to *this* parent version? Verified by content,
not by assumption: the file at the parent commit (14,191 bytes, fetched via the GitHub contents API)
and the file at the fix commit (14,278 bytes) were diffed against each other. The result is exactly
4 inserted lines and nothing else:

```diff
@@ -260,4 +260,6 @@
 	resyncerrc := make(chan error, 1)
+	cancelCh := make(chan struct{})
+	defer close(cancelCh)
 	go func() {
 		for {
@@ -266,4 +268,6 @@
 			case <-stopCh:
 				return
+			case <-cancelCh:
+				return
 			}
```

That is byte-for-byte the same change as the patch recorded in the dataset file. So: correct parent,
correct buggy file, and the fix diff applies to that version exactly.

## 2. Why this case (relation to the paper's Figure 1)

The paper's Figure 1 (message-passing blocking bug) works like this: a parent function creates a
child goroutine and then returns early (timeout), so nobody ever receives from the channel the
child sends on; the child blocks forever. This case is the same failure family:

- the child goroutine is created inside `ListAndWatch`;
- the child waits in a `select` on channels only;
- `ListAndWatch` returns (for example because `Watch` failed), `defer cleanup()` stops the resync
  timer, and **nobody ever signals the child again**;
- the child stays parked in `select` forever → goroutine leak → blocking bug.

The difference from Figure 1: the child blocks on **receive** instead of send. Both are
"parent leaves, child has no exit path" message-passing blocking bugs.

## 3. Buggy code (parent commit `6abb4723…`, `pkg/client/cache/reflector.go`)

Verbatim excerpt of the buggy version, lines 236–277 of the file at that commit:

```go
	resyncCh, cleanup := r.resyncChan()
	defer cleanup()
	...
	resyncerrc := make(chan error, 1)
	go func() {
		for {
			select {
			case <-resyncCh:
			case <-stopCh:
				return
			}
			glog.V(4).Infof("%s: forcing resync", r.name)
			if err := r.store.Resync(); err != nil {
				resyncerrc <- err
				return
			}
			cleanup()
			resyncCh, cleanup = r.resyncChan()
		}
	}()
```

The child goroutine has exactly two exit paths: `stopCh` being closed, or `Resync()` returning an
error. When `ListAndWatch` returns normally (e.g. the watch errored out), `stopCh` is **not** closed
(it is the long-lived stop channel of the whole reflector / informer), and `Resync()` is not being
called at all any more, because `defer cleanup()` has just stopped the resync timer. So the child
waits on `resyncCh` and `stopCh` forever.

## 4. The fix (commit `991674380…`)

```diff
@@ -259,12 +259,16 @@ func (r *Reflector) ListAndWatch(stopCh <-chan struct{}) error {
 	r.setLastSyncResourceVersion(resourceVersion)
 
 	resyncerrc := make(chan error, 1)
+	cancelCh := make(chan struct{})
+	defer close(cancelCh)
 	go func() {
 		for {
 			select {
 			case <-resyncCh:
 			case <-stopCh:
 				return
+			case <-cancelCh:
+				return
 			}
 			glog.V(4).Infof("%s: forcing resync", r.name)
 			if err := r.store.Resync(); err != nil {
```

The fix adds a third exit path that is guaranteed to fire when `ListAndWatch` returns: `cancelCh`
is closed by `defer close(cancelCh)`. That is a "lifetime signal" fix, not a "make the channel
buffered" fix.

## 5. Original test case

The fix commit `991674380…` does **not** add a regression test. Kubernetes of that era had no
unit test that observes this leak (that is part of why the bug lived for a while). This is a
finding of the feasibility investigation, not an omission:

- searched the fix commit for `_test.go` changes: none (the commit touches only
  `pkg/client/cache/reflector.go`);
- no upstream issue number is recorded in the dataset entry.

Consequence for reproduction: the original test input that would trip the bug **does not exist in
the repository**. A reproducer has to be written from the code pattern, which is what
`feasibility/reproducer/` does.

## 6. Relation to the detectors evaluated in the paper

- Go's built-in deadlock detector: will **not** report this bug. The detector only fires when *all*
  goroutines are asleep; here the main goroutine keeps running (and in real Kubernetes many other
  goroutines keep running), so "all goroutines asleep" never happens. This matches the paper's
  Table 8 conclusion (2 / 21 blocking bugs detected).
- `-race` detector: will **not** report this bug. There is no shared-memory data race; the problem
  is purely a missing channel signal. This matches the paper's point that `-race` targets data races,
  not blocking bugs.

So this single case is a clean illustration of both limitations the paper reports, and it is the
natural bridge to the next stage (running the two detectors).
