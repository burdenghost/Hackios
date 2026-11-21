# Security Policy

HackiOS is an experimental research project. It is not a production operating
system, and its bootloader, kernel port, drivers, and host-side tools may contain
bugs that can cause data loss, device instability, or an unbootable device.

## Reporting a vulnerability

Please report suspected security vulnerabilities privately through
[GitHub Security Advisories](https://github.com/burdenghost/Hackios/security/advisories/new)
for this repository, rather than opening a public issue.

Include:
- the affected commit, release, device, and build configuration;
- the smallest reproducible description or proof of concept;
- the expected and observed behavior, including logs where safe to share;
- any known impact on device data, boot integrity, or hardware state.

Do not include personal data, firmware dumps, proprietary Apple files, or
vendor firmware in a report or public issue. Share only the minimum material
needed to reproduce the problem.

Please allow maintainers reasonable time to investigate and coordinate a fix
before public disclosure. There is no guaranteed response or patch timeline.

## Safety expectations

- Test on a device you own or are explicitly authorized to use.
- Prefer QEMU and other disposable test environments for malformed inputs.
- Do not flash partitions or alter device storage unless the relevant procedure
  explicitly requires it and you have a verified recovery path.
- Treat experimental builds as unsafe for devices or data you cannot afford
  to lose.
