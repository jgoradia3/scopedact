> Legacy evaluation paths. For the current authenticated ticket pilot, use [the reviewer guide](REVIEW_GUIDE.md), [architecture](ARCHITECTURE.md), and [capability matrix](CAPABILITIES.md). The descriptions below apply only to the older workspace/laboratory examples.

# Docker evaluation

Build the dependency-free image:

```bash
docker build -t scopedact:dev .
docker run --rm scopedact:dev
```

The default container command runs the narrated offline tour. It is useful for confirming that the package starts, but the protected workspace application is the primary product workflow.

The current application intentionally binds every listener to loopback. Host-native execution is therefore the supported interactive path in v0.11. Containerized multi-service deployment is not advertised until the project has explicit network identities, TLS, and a production secrets boundary.
