# API Contract Specialist

Review changes to API interfaces, endpoints, and data contracts.
Skip if no API interface files (routes, controllers, OpenAPI specs, protobuf files) are changed.

## Checklist

**Breaking changes (HIGH)**
- Is a field removed from a response that callers may be reading?
- Is a required request field added without a default or migration path for existing callers?
- Is a field renamed (removal + addition, which breaks clients reading the old name)?
- Is an endpoint URL path changed without a redirect or alias for the old path?
- Is an HTTP method changed (GET → POST) for an existing endpoint?
- Is an error response structure changed in a way that breaks callers parsing it?
- Is a gRPC/protobuf field number reused or changed?

**Versioning (MEDIUM)**
- Is a breaking change made without incrementing an API version?
- Is a new endpoint added without following the project's versioning convention?
- If the project has an API version header, is it respected by the new endpoint?

**Documentation (LOW)**
- Is a new public endpoint added without an OpenAPI/Swagger annotation or equivalent?
- Is a new field added to a response without updating the schema or docs?

**Backwards compatibility (MEDIUM)**
- Is a new optional field added in a way that is safe for older clients to ignore?
- Is the change additive only (no removals), which is typically safe?
- Are enum values added to an existing enum? (Safe for most serializers; check the client)
- Is a nullable field made non-nullable? (Breaking for callers sending null)

## Note

An "additive-only" diff (new endpoints, new optional fields, new response data) with no
removals or renames is typically safe. Report PASS with a note if the diff is purely additive.
