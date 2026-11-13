# Environment

All values below were collected from the machine on which the experiment was actually run
(2026-11-13).

## Hardware / OS

| Item | Value |
| --- | --- |
| OS | Microsoft Windows 11 家庭中文版, version 10.0.26200 |
| CPU | 12th Gen Intel Core i7-1260P (12 cores / 16 logical processors) |
| RAM | 15.7 GB |

## Toolchain

| Item | Value |
| --- | --- |
| Go — version actually tested | `go1.20.14 windows/amd64` (portable toolchain, downloaded from https://go.dev/dl/go1.20.14.windows-amd64.zip) |
| Go — version declared by the project | `go 1.20` (in `reproducer/go.mod`) |
| Go — other versions | **not verified.** Nothing in this experiment was run on Go < 1.20 or > 1.20.14, so no claim is made about them |
| Git | `git version 2.56.0.windows.2` |
| Shell | PowerShell 7.6.4 |

Read the three Go rows separately: `go 1.20` in `go.mod` is only the *declared* minimum, `1.20.14`
is the *only* version this experiment actually ran on, and every other version is unverified.

## Historical code requirements (Kubernetes at the buggy commit `6abb4723…`)

Checked through the GitHub contents API at that commit:

| Item | Value | Consequence |
| --- | --- | --- |
| `go.mod` | **absent** (HTTP 404) | the project is pre-modules, so `go build` in module mode cannot resolve it |
| `Godeps/Godeps.json` | present (80,849 bytes) | dependencies are vendored and pinned by Godeps |
| `vendor/` | present (directory) | build must run in GOPATH mode against the vendored tree |
| Go version of that era | Go 1.6 – 1.7 (2016) | Go 1.20 rejects/does not reproduce the old GOPATH build without manual surgery |
| `build/` directory | absent at that commit | no containerised build script at that exact revision |

Conclusion recorded in `feasibility_results.csv`: retrieving the code succeeded; compiling the
**whole historical Kubernetes tree** was **not attempted and is not feasible** on a modern
workstation within a week's budget (pre-modules GOPATH build, Godeps vendoring, Go-version drift,
multi-GB clone). Instead the bug pattern was reconstructed in a standalone Go module and run, which
is sufficient to establish that the blocking behaviour is reproducible.
