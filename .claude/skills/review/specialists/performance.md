# Performance Specialist

Review the diff for structural performance problems. Only flag issues introduced by the diff.

## Checklist

**Database / storage (HIGH if on a hot path)**
- N+1 queries: is a query executed inside a loop over a result set?
- Missing index: does a new filter or join condition reference an unindexed column?
- Unbounded result set: does a new query lack LIMIT, pagination, or a range constraint?
- Lock contention: does a new write transaction hold a row/table lock longer than necessary?
- Synchronous migration in request path: is a schema change triggered by a web request?

**I/O on hot paths (HIGH if blocking, MEDIUM if async)**
- Is a blocking network call (HTTP, DB, file read) introduced on a synchronous request path?
- Is a large file read fully into memory when streaming would suffice?
- Are multiple sequential I/O calls introduced where a single batched call would work?

**Memory (MEDIUM–HIGH depending on input bounds)**
- Is there an allocation proportional to untrusted input size (no upper bound)?
- Is a large collection accumulated in memory before being streamed or paginated?
- Are there new caches without eviction policies or size limits?

**Concurrency (MEDIUM)**
- Is a shared data structure accessed without synchronization?
- Is a lock held across an I/O operation or a long-running computation?
- Is a goroutine/thread spawned without a bound or cleanup path?

**Compute (LOW–MEDIUM)**
- Is an O(n²) or worse algorithm introduced on a hot path?
- Is an expensive operation (compression, encryption, hashing) called per-item in a loop when it could be batched?
- Is a regex compiled inside a loop instead of once at initialization?

## Note

Flag only what the diff introduces. Pre-existing performance issues are not in scope unless
the diff makes them significantly worse (e.g., a diff that adds a loop around an existing
slow query).
