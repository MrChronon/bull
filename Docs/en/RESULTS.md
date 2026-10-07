# Understanding BULL results

## During a comparison

The live line shows the current phase, elapsed time and approximate token rate.
The token budget is a limit, not the percentage of the task completed. CPU, RAM,
GPU and VRAM appear when the active inference host provides the sensors. The line
fits the terminal width; narrow windows abbreviate sensors to G/V/C/R.

After each saved run, BULL prints its Native score, Final score if different,
task-contract status, measured speed and resources. The next line accumulates
only the current **model + backend + test**. It reports the number of successful
runs and scored answers, mean Native quality and observed generation speed.
This is provisional: it does not rank models while test coverage is unequal.

## After a comparison

The concise terminal view starts with top-three **places**, followed by model
IDs, a numeric quality–speed map and a compact resource/completion summary.
Long names wrap below the chart rather than changing its width. The result menu
offers the HTML report, export files, custom priorities, answers and a separate
**Detailed terminal metrics** view. No report requires an active model server.

### Measured places and recommendations are different

- **Native quality:** observed score, descending. This never includes recovery.
- **Generation speed:** tokens per second, descending. Warm observations are used
  when available; models without warm measurements are not silently mixed into
  that ranking. If none have warm measurements, the all-load-states basis is explicit.
- **Task time:** mean recorded pipeline wall time, ascending. This includes
  allowed client assistance; a higher token rate does not imply a shorter task.
- **VRAM peak:** observed memory use, ascending. Unknown sensors are excluded,
  not interpreted as zero. This is not a minimum hardware requirement.
- **Balance:** ordering by the existing weighted preference formula, not a new
  benchmark score. The HTML shortlist marks candidates that fail the gate.

Equal values share a place (for example, 1, 1, 3). All tied third places are kept,
so a top-three list can contain more than three models. Close but unequal means
are merely an observed order, not evidence of a statistically certain winner.

Speed, Balance, Low memory and custom recommendations require conservative Native
quality of at least `max(60%, best conservative quality − 10 percentage points)`
and task completion of at least 80% when known. The conservative value is the
lower 95% confidence bound when available, otherwise the observed mean.
Unknown metrics required by a profile exclude that candidate.

If only one model passes, BULL states this explicitly. It may be recommended for
several priorities without being the measured fastest or smallest model. The
quality-led profile retains its own weighted policy and does not apply the speed
quality gate. Open **Places & reasons** to inspect every candidate and weights.

Different recorded test/seed coverage, failed execution records or parameter
sweeps disable recommendations. Descriptive measurements remain visible. Identical
coverage alone does not prove identical hardware, output length or background load.

## HTML report

The report follows the selected application language (English or Russian) and
works offline without JavaScript, a CDN or remote assets.

1. **Top 3:** measured places, balanced priorities, qualified recommendations and
   explicit exclusion reasons.
2. **Quality & speed:** numeric Native-quality versus throughput scatter plot.
   The separate time plot uses pipeline seconds. Colors and model IDs stay the same
   throughout the report; the table is the accessible numeric alternative.
3. **Resources:** CPU/GPU run averages and RAM/VRAM observed peaks. These are
   whole-host sensors including background processes, not per-model allocation.
   Sensor coverage is reported; partial measurement coverage limits comparisons.
4. **Tests:** Native-quality heatmap, plain-language descriptions for built-in
   CHAT tests, sample counts and category scores. Other tests are identified by
   their recorded IDs without exposing a private prompt or inventing a description.
5. **Settings:** recorded context capacity, output limit, threads, sampling,
   reasoning, seeds and load states. Expand provenance to see whether a parameter
   was explicitly sent or inherited. Multiple values remain multiple values.
6. **Full data:** per-test means, uncertainty, timing ranges, critical findings,
   execution/transport counts and context curves when comparable points exist.

Quality bars use the 0–100% scale. Resource memory bars are relative to the largest
measured value in this report. A time range is an observed min–max, not a confidence
interval. SD is variability; a 95% interval is uncertainty around an estimate.

**GEN** means generation ended; **TASK** means required structure/schema was
satisfied. Neither proves semantic correctness. Final system quality, recovery
and transport errors remain separate from Native quality.

## Sharing and old results

HTML never embeds prompts, answers, tokens, connection settings or private paths.
Model and test names are still visible: inspect them before sharing. Use the
share-safe evidence JSON for metrics exchange; raw JSON remains private.

Existing benchmark files are not silently rescored or overwritten. A newly
generated report uses the new presentation; a previously saved HTML keeps its
original appearance. Prompts, scorers and inference settings are unchanged by
the report redesign.
