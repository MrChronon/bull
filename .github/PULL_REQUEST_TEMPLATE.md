## What changed

Describe the problem, the chosen change and the user-visible outcome.
Можно писать по-русски: проблема, изменение и результат для пользователя.

## Scope and compatibility

- [ ] This pull request is one small, verifiable change.
- [ ] I did not combine benchmark prompt, scorer and runtime-pipeline changes.
- [ ] I identified any schema or historical-result compatibility impact.
- [ ] Native-model metrics remain separate from client-recovery metrics.

Русский: одно небольшое изменение; prompt/scorer/runtime не объединены;
совместимость schemas/истории указана; Native/recovery раздельны.

## Verification

- [ ] Added or updated a regression test for changed behavior.
- [ ] `Run-Tests.ps1` passes.
- [ ] Public-release audit passes when relevant.
- [ ] Manual checks and environment are listed below.

Русский: regression test, Run-Tests, privacy gate и реальные ручные проверки.

## Privacy and provenance

- [ ] No keys, tokens, endpoints, usernames, personal paths, private prompts,
      model responses, runtime state or unreviewed logs are included.
- [ ] External code/data includes compatible licensing and provenance.

Русский: без секретов/локальных данных; для чужих данных указаны права и источник.

## Evidence

Paste concise test output or before/after evidence. Sanitize it before posting.
