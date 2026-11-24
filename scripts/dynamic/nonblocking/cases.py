"""Authored mapping from pinned patch identities to reconstructed mechanisms."""

# SHA prefix: (Go function, trigger, faithful fix, omissions / interpretation).
SPECS = {
    "4e262f638760": ("stdinNotification", "ready and canceled are both selectable", "recheck ready after the first select", "No container or stdin pipe; a missed notification is observed directly, not as a timeout."),
    "c1ad02ccc879": ("logEventOwnership", "producer reuses an input and event slice after publication", "copy the input and event slice before sending", "AWS API and SDK types are replaced by a small owned input; pointee event mutation is outside the model."),
    "1670914b8a56": ("closurePair", "range variable pair is captured by a child", "pass pair[0] as a goroutine argument", "Headers are represented by integers; HTTP/net.Pipe are omitted. Controlled mode delays children until loop exit."),
    "825e3a66a419": ("closureAPIVersion", "loop counter is captured by API-version workers", "pass i as a goroutine argument", "Uses Go 1.20 loop semantics and versions 17..21; real Docker API calls are omitted."),
    "345f875c51c0": ("proxyCalled", "callback writes the flag while a test reads it", "replace bool with atomic count/load", "Proxy and HTTP upgrade omitted. Race-only oracle; output need not be wrong."),
    "647b826d697a": ("namespaceOwnership", "reconciler modifies a shared informer object", "deep-copy mutable fields before modifications", "Namespace is a nested integer slice; API and informer infrastructure omitted."),
    "3c345abafd02": ("pluginSlice", "appender changes slice header while test reads it", "obtain slice header with RLock", "Only immutable entries and length are observed; accessor does not protect arbitrary later entry mutation."),
    "5d033c22afdf": ("timerReuse", "AfterFunc watchdog is reused with Reset across I/O phases", "use one-shot select watchdogs and completion channels", "Version-sensitive library candidate: I/O is simulated, timer API pattern retained. No unsafe variable is injected; historical library race may remain unobserved."),
    "c678dcbd9172": ("revisionCounter", "revision increment races with the test setter", "atomic AddInt64 and StoreInt64", "Compactor omitted. Concurrent stores have no prescribed final-value oracle."),
    "91dc6b29a6e0": ("progressInterval", "configuration changes after server work has started", "set interval before starting the server, using atomic store", "Preserves the patch's startup ordering, not a claim that atomic stores make concurrent plain reads safe. Restore occurs after joining."),
    "2c83362e63e6": ("reconnectLock", "retryConnection reads active connection before taking mu", "move Lock before reconnect/read/replace", "Connections are integer generations; network I/O and cancellation omitted."),
    "e129223dbeba": ("watcherResume", "reconnect reads lastRev while serveStream advances it", "pause owner through resumec before rebuilding, then resume", "Event stream and RPC are reduced to revision updates. Revision mismatch is recorded instead of panicking."),
    "3ce31acda410": ("contextString", "String traverses a context value while it changes", "wrap context with constant String()", "Reconstructs Go 1.7 valueCtx.String formatting with a mutable struct instead of trace. Go 1.20 no longer formats a non-Stringer value; the historical formatter is explicitly modeled, not attributed to the current stdlib."),
    "4bdfc0a46d28": ("watchChannelReturn", "serveStream closes retc before addStream sends on it", "publish subscriber channel before starting serveStream", "Buffered channel and closure ordering retained; cancellation/RPC omitted. Controlled mode waits for cleanup first."),
    "7f95780bfb5d": ("raftChannelInit", "defer close evaluates a nil done channel before raft start", "initialize channels before registering deferred shutdown", "Single-threaded trigger captures the same argument-evaluation order; raft/network omitted."),
    "d5a604c99d9e": ("checkpointFiles", "checkpoint copies files after releasing mu", "take snapshot under the existing lock", "Models slice publication as an immutable backing array plus scalar published length, preserving the missed-lock read but excluding multiword-header tearing. A preliminary composite-header version corrupted RESULT metadata; its source and logs are retained separately and excluded from final results."),
    "4edda446686e": ("destroyStatus", "error field is read after Unlock while another writer holds mu", "copy error field before Unlock", "Errors are integer codes; no visible error-value invariant is asserted."),
    "c6b46087ab92": ("statusThenWrite", "Write follows WriteStatus while writes is closed but closedCh is open", "serialize status and close transport before closing writes", "Uses the patch's sequential WriteStatus/Write regression path. HTTP trailers and stream handling omitted; not the separate concurrent-status workload."),
    "b71aced4a2a1": ("headersAfterClose", "later headers overwrite encoding already published to receiver", "do not change encoding after headerDone", "Begins after initial header publication; HTTP/2 frames and compression omitted."),
    "a62701e4aa1d": ("balancerMap", "watcher iterates subConns during mutation", "protect iteration and mutation with RWMutex", "Connection callbacks omitted. Runtime map fatal is a symptom, not itself a race-detector report."),
    "87bcb38fba80": ("balancerPointer", "wrapper pointer is published without reader's lock", "take ac.mu around publication", "Pointer payload is an initialized integer; network reconnection omitted."),
    "c69cb102ce8f": ("closePendingTransaction", "Close releases resources with a write transaction still active", "Close takes the transaction rwlock", "Upstream merge diff/test recovered from GitHub. Covers pending writable transaction, not all mmap/read-only cases. Atomic observation avoids an invented data race."),
    "7fb06feea401": ("transactionMetadata", "read transaction keeps a pointer to writer-mutated meta", "copy meta when opening transaction", "Transaction opening is serialized as upstream requires; pages/buckets and mmap omitted."),
}


def enrich(candidate):
    symbol, trigger, fix, limitation = SPECS[candidate["commit"][:12]]
    return {**candidate, "symbol": symbol, "trigger": trigger, "fix": fix,
            "limitation": limitation,
            "evidence": "upstream merge diff + TestDB_Close_PendingTx" if symbol == "closePendingTransaction" else "pinned dataset patch",
            "status": "implemented_pattern"}
