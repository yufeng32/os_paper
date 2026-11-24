# Case-to-patch mapping

All 23 entries are independent pattern reconstructions; no historical application was built.
Candidate identity is application + full commit; repeated issue IDs are not deduplicated.
The source URLs identify fixing commits; the pinned dataset patch exposes the before/after operations.

Natural mode uses a common launch gate, joins and scheduler yields, without forcing a particular conflict order.
Controlled mode adds a loop-exit gate (closure cases), a cleanup join (return channel), or a short transaction hold.
Those extra edges can suppress races and are diagnostic only. Random seeds select workload yields; OS scheduling remains nondeterministic.

## docker_4e262f638760

- Source: [Docker Moby#28682](https://github.com/moby/moby/commit/4e262f63876018ca78d54a98eee3f533352b0ac9); workbook row 5, cause `channel`.
- Dataset patch: `non-blocking-bugs/docker/4e262f63876018ca78d54a98eee3f533352b0ac9.txt`; SHA-256 `2d00b06e8caf61a55260daab89ae6f69d14939412032a326d87a36d927a93142`.
- Function: `stdinNotification`.
- Trigger: ready and canceled are both selectable.
- Fix: recheck ready after the first select.
- Limits: No container or stdin pipe; a missed notification is observed directly, not as a timeout.

## docker_c1ad02ccc879

- Source: [Docker Moby#22985](https://github.com/moby/moby/commit/c1ad02ccc8791b3c517aa37223d27792863cbf17); workbook row 7, cause `traditional`.
- Dataset patch: `non-blocking-bugs/docker/c1ad02ccc8791b3c517aa37223d27792863cbf17.txt`; SHA-256 `d0bfed861d8219b26721055d27410ea1c47df7249ebd16dc2c6282c9c2bbbe05`.
- Function: `logEventOwnership`.
- Trigger: producer reuses an input and event slice after publication.
- Fix: copy the input and event slice before sending.
- Limits: AWS API and SDK types are replaced by a small owned input; pointee event mutation is outside the model.

## docker_1670914b8a56

- Source: [Docker Moby#22940](https://github.com/moby/moby/commit/1670914b8a56ab8e6ead38739fddb416b61e444f); workbook row 9, cause `anonymous`.
- Dataset patch: `non-blocking-bugs/docker/1670914b8a56ab8e6ead38739fddb416b61e444f.txt`; SHA-256 `8d26f9e7e83d9075d7cec59ed99dfb127c9854a93f9e5f7380b3383b42baa112`.
- Function: `closurePair`.
- Trigger: range variable pair is captured by a child.
- Fix: pass pair[0] as a goroutine argument.
- Limits: Headers are represented by integers; HTTP/net.Pipe are omitted. Controlled mode delays children until loop exit.

## docker_825e3a66a419

- Source: [Docker Moby#27037](https://github.com/moby/moby/commit/825e3a66a419038600024be7dfc5ca24426444f0); workbook row 10, cause `anonymous`.
- Dataset patch: `non-blocking-bugs/docker/825e3a66a419038600024be7dfc5ca24426444f0.txt`; SHA-256 `c029526d775d3011586f94d25616611dd1e3f69c337f7fb6652beb41c3bf67d5`.
- Function: `closureAPIVersion`.
- Trigger: loop counter is captured by API-version workers.
- Fix: pass i as a goroutine argument.
- Limits: Uses Go 1.20 loop semantics and versions 17..21; real Docker API calls are omitted.

## kubernetes_345f875c51c0

- Source: [Kubernetes kbernetes#49404](https://github.com/kubernetes/kubernetes/commit/345f875c51c0acd909f206b855d158b8e3adbbb3); workbook row 28, cause `anonymous`.
- Dataset patch: `non-blocking-bugs/kubernetes/345f875c51c0acd909f206b855d158b8e3adbbb3.txt`; SHA-256 `49c6edd48f0dbf1889336fa0683f950a01b2fd16cc37bc48a5c7e01f41039462`.
- Function: `proxyCalled`.
- Trigger: callback writes the flag while a test reads it.
- Fix: replace bool with atomic count/load.
- Limits: Proxy and HTTP upgrade omitted. Race-only oracle; output need not be wrong.

## kubernetes_647b826d697a

- Source: [Kubernetes kubernetes#36377](https://github.com/kubernetes/kubernetes/commit/647b826d697abdc50aa4808fa21604c9f6fe80a4); workbook row 33, cause `traditional`.
- Dataset patch: `non-blocking-bugs/kubernetes/647b826d697abdc50aa4808fa21604c9f6fe80a4.txt`; SHA-256 `5ec7eb14813b405e1843795435d0ad436a5fe301d61740d4efbfea2da54a4dc1`.
- Function: `namespaceOwnership`.
- Trigger: reconciler modifies a shared informer object.
- Fix: deep-copy mutable fields before modifications.
- Limits: Namespace is a nested integer slice; API and informer infrastructure omitted.

## kubernetes_3c345abafd02

- Source: [Kubernetes kubernetes#26407](https://github.com/kubernetes/kubernetes/commit/3c345abafd024853d8ff0fb332db6076cfc610c5); workbook row 41, cause `traditional`.
- Dataset patch: `non-blocking-bugs/kubernetes/3c345abafd024853d8ff0fb332db6076cfc610c5.txt`; SHA-256 `40b3dfd921b594eb88da8e34eff32621977e80ac20dc6aae4e67ab91174c7dd8`.
- Function: `pluginSlice`.
- Trigger: appender changes slice header while test reads it.
- Fix: obtain slice header with RLock.
- Limits: Only immutable entries and length are observed; accessor does not protect arbitrary later entry mutation.

## etcd_5d033c22afdf

- Source: [etcd etcd#3593](https://github.com/etcd-io/etcd/commit/5d033c22afdf947649b680ed7ad3c1527432ca9e); workbook row 48, cause `shared_lib`.
- Dataset patch: `non-blocking-bugs/etcd/5d033c22afdf947649b680ed7ad3c1527432ca9e.txt`; SHA-256 `f956b85ba046090c5a6f924eca97ab266d4442637e16115dbb2f360cbe6876e3`.
- Function: `timerReuse`.
- Trigger: AfterFunc watchdog is reused with Reset across I/O phases.
- Fix: use one-shot select watchdogs and completion channels.
- Limits: Version-sensitive library candidate: I/O is simulated, timer API pattern retained. No unsafe variable is injected; historical library race may remain unobserved.

## etcd_c678dcbd9172

- Source: [etcd etcd#8183](https://github.com/etcd-io/etcd/commit/c678dcbd91721b17d52ef39afb3104444f14deac); workbook row 49, cause `traditional`.
- Dataset patch: `non-blocking-bugs/etcd/c678dcbd91721b17d52ef39afb3104444f14deac.txt`; SHA-256 `ff8597f8ab23d3db1f04667643a0ea1275fdd833251f3eeea4126812520aad0d`.
- Function: `revisionCounter`.
- Trigger: revision increment races with the test setter.
- Fix: atomic AddInt64 and StoreInt64.
- Limits: Compactor omitted. Concurrent stores have no prescribed final-value oracle.

## etcd_91dc6b29a6e0

- Source: [etcd etcd#4876](https://github.com/etcd-io/etcd/commit/91dc6b29a6e000375ba47181db1bfcf8ba92daad); workbook row 50, cause `traditional`.
- Dataset patch: `non-blocking-bugs/etcd/91dc6b29a6e000375ba47181db1bfcf8ba92daad.txt`; SHA-256 `a44c82a2b4f4f2d79bdb9b81e788780aaf68fe12b56fef513657ec37fb7d4b04`.
- Function: `progressInterval`.
- Trigger: configuration changes after server work has started.
- Fix: set interval before starting the server, using atomic store.
- Limits: Preserves the patch's startup ordering, not a claim that atomic stores make concurrent plain reads safe. Restore occurs after joining.

## etcd_2c83362e63e6

- Source: [etcd etcd#4876](https://github.com/etcd-io/etcd/commit/2c83362e63e6b796ea988442483673056c567455); workbook row 51, cause `traditional`.
- Dataset patch: `non-blocking-bugs/etcd/2c83362e63e6b796ea988442483673056c567455.txt`; SHA-256 `017b44e746728319e80614d4ec76260ee1ea2ded095dd4a34f51e2a3e77fa9bb`.
- Function: `reconnectLock`.
- Trigger: retryConnection reads active connection before taking mu.
- Fix: move Lock before reconnect/read/replace.
- Limits: Connections are integer generations; network I/O and cancellation omitted.

## etcd_e129223dbeba

- Source: [etcd etcd#4876](https://github.com/etcd-io/etcd/commit/e129223dbebaa5a13b9564dea27fdcd5bbebb317); workbook row 52, cause `traditional`.
- Dataset patch: `non-blocking-bugs/etcd/e129223dbebaa5a13b9564dea27fdcd5bbebb317.txt`; SHA-256 `e61aa1934d5413f00d35efb0ca28049b752a4fe415c3b291977330789a0d2a15`.
- Function: `watcherResume`.
- Trigger: reconnect reads lastRev while serveStream advances it.
- Fix: pause owner through resumec before rebuilding, then resume.
- Limits: Event stream and RPC are reduced to revision updates. Revision mismatch is recorded instead of panicking.

## etcd_3ce31acda410

- Source: [etcd etcd#7816](https://github.com/etcd-io/etcd/commit/3ce31acda410db937408ac1c1011fe7b0babd8a7); workbook row 55, cause `shared_lib`.
- Dataset patch: `non-blocking-bugs/etcd/3ce31acda410db937408ac1c1011fe7b0babd8a7.txt`; SHA-256 `76ba57b16b46d7087a0486c9fba59994c1970f25baefbf388723dc1f29602111`.
- Function: `contextString`.
- Trigger: String traverses a context value while it changes.
- Fix: wrap context with constant String().
- Limits: Reconstructs Go 1.7 valueCtx.String formatting with a mutable struct instead of trace. Go 1.20 no longer formats a non-Stringer value; the historical formatter is explicitly modeled, not attributed to the current stdlib.

## etcd_4bdfc0a46d28

- Source: [etcd etcd#4876](https://github.com/etcd-io/etcd/commit/4bdfc0a46d28f35462a312e1b51a771764321442); workbook row 57, cause `channel`.
- Dataset patch: `non-blocking-bugs/etcd/4bdfc0a46d28f35462a312e1b51a771764321442.txt`; SHA-256 `e68957147a3540ec0f1a7d4548e531d2826944be48cf09e35a1ef8a0315de026`.
- Function: `watchChannelReturn`.
- Trigger: serveStream closes retc before addStream sends on it.
- Fix: publish subscriber channel before starting serveStream.
- Limits: Buffered channel and closure ordering retained; cancellation/RPC omitted. Controlled mode waits for cleanup first.

## etcd_7f95780bfb5d

- Source: [etcd etcd#3060](https://github.com/etcd-io/etcd/commit/7f95780bfb5d72c651e870d0cc65c6f2b88700d8); workbook row 60, cause `channel`.
- Dataset patch: `non-blocking-bugs/etcd/7f95780bfb5d72c651e870d0cc65c6f2b88700d8.txt`; SHA-256 `ceaba245c1757820317d110c9bd0945e7e5b27ab3824826742823f4ef56f89ec`.
- Function: `raftChannelInit`.
- Trigger: defer close evaluates a nil done channel before raft start.
- Fix: initialize channels before registering deferred shutdown.
- Limits: Single-threaded trigger captures the same argument-evaluation order; raft/network omitted.

## cockroachdb_d5a604c99d9e

- Source: [CockroachDB cockroachdb#17112](https://github.com/cockroachdb/cockroach/commit/d5a604c99d9e9741f7f2242de204abde1b47c2d9); workbook row 63, cause `anonymous`.
- Dataset patch: `non-blocking-bugs/cockroachdb/d5a604c99d9e9741f7f2242de204abde1b47c2d9.txt`; SHA-256 `f84fb4ee65aad6cef773938e31c95cbf8561bc4399d5dc5dc75c96d5e63591a7`.
- Function: `checkpointFiles`.
- Trigger: checkpoint copies files after releasing mu.
- Fix: take snapshot under the existing lock.
- Limits: Models slice publication as an immutable backing array plus scalar published length, preserving the missed-lock read but excluding multiword-header tearing. A preliminary composite-header version corrupted RESULT metadata; its source and logs are retained separately and excluded from final results.

## cockroachdb_4edda446686e

- Source: [CockroachDB cockroachdb#19962](https://github.com/cockroachdb/cockroach/commit/4edda446686e8d6cd358c1db685bf27aaf680a06); workbook row 71, cause `traditional`.
- Dataset patch: `non-blocking-bugs/cockroachdb/4edda446686e8d6cd358c1db685bf27aaf680a06.txt`; SHA-256 `6de8fb647abf1e571ef4c44f37c57df384bfe7beb53c5edb7bcc7c6f754fb0b6`.
- Function: `destroyStatus`.
- Trigger: error field is read after Unlock while another writer holds mu.
- Fix: copy error field before Unlock.
- Limits: Errors are integer codes; no visible error-value invariant is asserted.

## grpc_go_c6b46087ab92

- Source: [gRPC grpc#1687](https://github.com/grpc/grpc-go/commit/c6b46087ab923e9f453ec433f99174cdd45b9b89); workbook row 80, cause `channel`.
- Dataset patch: `non-blocking-bugs/grpc-go/c6b46087ab923e9f453ec433f99174cdd45b9b89.txt`; SHA-256 `0d3d9e000d8525e00f99cee6fe80258cf8c5ff81d2845381d36ab8c58097f9f4`.
- Function: `statusThenWrite`.
- Trigger: Write follows WriteStatus while writes is closed but closedCh is open.
- Fix: serialize status and close transport before closing writes.
- Limits: Uses the patch's sequential WriteStatus/Write regression path. HTTP trailers and stream handling omitted; not the separate concurrent-status workload.

## grpc_go_b71aced4a2a1

- Source: [gRPC grpc#1803](https://github.com/grpc/grpc-go/commit/b71aced4a2a1ee80a1cbbd26b85a57623790d7f4); workbook row 81, cause `traditional`.
- Dataset patch: `non-blocking-bugs/grpc-go/b71aced4a2a1ee80a1cbbd26b85a57623790d7f4.txt`; SHA-256 `cd20de21e72d523cd070e3f775fb8cd27ffb5c823dc803f128980365992e2576`.
- Function: `headersAfterClose`.
- Trigger: later headers overwrite encoding already published to receiver.
- Fix: do not change encoding after headerDone.
- Limits: Begins after initial header publication; HTTP/2 frames and compression omitted.

## grpc_go_a62701e4aa1d

- Source: [gRPC grpc#1667](https://github.com/grpc/grpc-go/commit/a62701e4aa1d276bec70311251d62a478404d63f); workbook row 82, cause `traditional`.
- Dataset patch: `non-blocking-bugs/grpc-go/a62701e4aa1d276bec70311251d62a478404d63f.txt`; SHA-256 `802e0957273b33d3b2c3da57ef725944b23fa0f326a8a11e2782fb60da780d93`.
- Function: `balancerMap`.
- Trigger: watcher iterates subConns during mutation.
- Fix: protect iteration and mutation with RWMutex.
- Limits: Connection callbacks omitted. Runtime map fatal is a symptom, not itself a race-detector report.

## grpc_go_87bcb38fba80

- Source: [gRPC grpc#1662](https://github.com/grpc/grpc-go/commit/87bcb38fba807cf2f45bc15756795923bd33b4ae); workbook row 83, cause `traditional`.
- Dataset patch: `non-blocking-bugs/grpc-go/87bcb38fba807cf2f45bc15756795923bd33b4ae.txt`; SHA-256 `5c5296bc2ea46b265077d1da9b5165d6afee35928bc572ffb87c00040e70c823`.
- Function: `balancerPointer`.
- Trigger: wrapper pointer is published without reader's lock.
- Fix: take ac.mu around publication.
- Limits: Pointer payload is an initialized integer; network reconnection omitted.

## boltdb_c69cb102ce8f

- Source: [BoltDB boltdb#341](https://github.com/boltdb/bolt/commit/c69cb102ce8f7609b57f75d0ccb10862167001e7); workbook row 92, cause `traditional`.
- Dataset patch: `non-blocking-bugs/boltdb/c69cb102ce8f7609b57f75d0ccb10862167001e7.txt`; SHA-256 `bcca2f36f334bb82e3352ecfb5278698aa938da3aa71c4f3842c8cc913ed14f5`.
- Function: `closePendingTransaction`.
- Trigger: Close releases resources with a write transaction still active.
- Fix: Close takes the transaction rwlock.
- Limits: Upstream merge diff/test recovered from GitHub. Covers pending writable transaction, not all mmap/read-only cases. Atomic observation avoids an invented data race.

## boltdb_7fb06feea401

- Source: [BoltDB (no issue ID)](https://github.com/boltdb/bolt/commit/7fb06feea4012543b6a1b0726a09e9a4c4a84933); workbook row 93, cause `traditional`.
- Dataset patch: `non-blocking-bugs/boltdb/7fb06feea4012543b6a1b0726a09e9a4c4a84933.txt`; SHA-256 `e5fa183d3de7726b483b92ba1e71a32c8607806bc31a966578972acbfcfcbc16`.
- Function: `transactionMetadata`.
- Trigger: read transaction keeps a pointer to writer-mutated meta.
- Fix: copy meta when opening transaction.
- Limits: Transaction opening is serialized as upstream requires; pages/buckets and mmap omitted.
