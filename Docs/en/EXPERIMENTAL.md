# Experimental features

Experimental features are available under **More → Experimental features**.
They are not required for ordinary chat or model comparison.

## Agent Benchmark

Agent Lab runs bounded multi-step tasks with independent verification. It records
task success, verifier results, tool calls, repetitions, duration, interventions,
and available resource telemetry. A successful tool call is not proof that the
task succeeded; the verifier is authoritative.

Agent work may create files and run code with the user's operating-system rights.
Use a disposable workspace or VM. Private configuration and full traces remain
under `Benchmarks/Agents` and must be reviewed before sharing. The generated HTML
report is an analysis artifact, not a security certificate.

## GPU Lab

GPU Lab targets Windows + Ollama experiments. It can compare declared GPU
configurations, including one GPU and supported combinations. BULL records
observed telemetry and uses unknown rather than zero when a sensor is unavailable.

The selected configuration describes the requested experiment; Ollama, drivers,
model fit, and the operating system determine actual placement. Verify effective
GPU use from telemetry. Stop unrelated jobs yourself: BULL terminates only the
worker process tree it owns.

Hardware results are meaningful only when model, quantization, context, sampling,
driver, thermal state, background load, power policy, and run order are recorded.

## Advanced engine and server tools

Manual Ollama/llama.cpp paths, server deployment, raw backend diagnostics, and
compatibility commands are retained for experienced operators. They are hidden
from the primary route because a typical user needs only Local Ollama, a saved
server, or an SSH alias.

