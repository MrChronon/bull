# Experimental features

Agent Benchmark is a direct action within **Home → Additional**.
Engine options are in Connection settings.
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

GPU Lab has been removed. Ordinary GPU/VRAM measurements remain available in
chat and benchmark telemetry; historical experiment results remain untouched.

## Advanced engine and server tools

Manual Ollama/llama.cpp paths, server deployment, raw backend diagnostics, and
compatibility commands are retained for experienced operators. They are hidden
from the primary route because a typical user needs only Local Ollama, a saved
server, or an SSH alias.
