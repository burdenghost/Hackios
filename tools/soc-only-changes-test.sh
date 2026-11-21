#!/bin/bash
# tools/soc-only-changes.sh: the reference's own values are not sent; a port's differences are; CRs do not matter.
cd "$(dirname "$0")/.." || exit 1
. tools/soc-only-changes.sh
fails=0
check() { # check LABEL WANT GOT
	if [ "$2" = "$3" ]; then echo "ok   $1"; else echo "FAIL $1"; echo "     want: [$2]"; echo "     got:  [$3]"; fails=$((fails + 1)); fi
}
ref=devices/redwood/soc.args
tmp=$(mktemp -d); trap 'rm -rf "$tmp"' EXIT

# When the private reference-device repository is not checked out (no HAKIOS_SYNC_TOKEN),
# keep testing the generic comparison with a small synthetic defaults file.
if [ -f "$ref" ]; then
    defaults=$ref
    check "the reference phone's own soc.args sends nothing" "" "$(SOC_DEFAULTS=$defaults soc_only_changes "$defaults" | tr '\n' ' ')"
    real_ref=1
else
    defaults=$tmp/defaults.args
    printf 'soc_aoss=0xc300000\n' > "$defaults"
    real_ref=0
    echo "skip reference-device comparison: devices/redwood is not checked out"
fi

# a port: one value differs, one is new, the rest equal the defaults
{ sed 's/^soc_aoss=.*/soc_aoss=0x1000000/' "$defaults"; echo "soc_extra=0x5"; } > "$tmp/port.args"
check "a port sends only its differences" "soc_aoss=0x1000000 soc_extra=0x5 " "$(SOC_DEFAULTS=$defaults soc_only_changes "$tmp/port.args" | tr '\n' ' ')"

# the same file with Windows line endings
sed 's/$/\r/' "$tmp/port.args" > "$tmp/port-crlf.args"
got=$(SOC_DEFAULTS=$defaults soc_only_changes "$tmp/port-crlf.args" | tr '\n' ' ')
check "CRLF line endings: same result" "soc_aoss=0x1000000 soc_extra=0x5 " "$got"
check "CRLF line endings: no CR in what is sent" "0" "$(printf '%s' "$got" | tr -cd '\r' | wc -c | tr -d ' ')"

# The reference file itself with CRLF still sends nothing.
sed 's/$/\r/' "$defaults" > "$tmp/ref-crlf.args"
if [ "$real_ref" -eq 1 ]; then
    check "the reference with CRLF sends nothing" "" "$(SOC_DEFAULTS=$defaults soc_only_changes "$tmp/ref-crlf.args" | tr '\n' ' ')"
else
    check "synthetic defaults with CRLF send nothing" "" "$(SOC_DEFAULTS=$defaults soc_only_changes "$tmp/ref-crlf.args" | tr '\n' ' ')"
fi

printf '# a comment\n\nsoc_x=0x1\n' > "$tmp/c.args"
check "comments and blank lines are dropped" "soc_x=0x1 " "$(soc_only_changes "$tmp/c.args" | tr '\n' ' ')"
check "a missing file sends nothing, and is not an error" "" "$(soc_only_changes "$tmp/none.args" | tr '\n' ' ')"
check "without a reference file everything is sent" "soc_x=0x1 " "$(SOC_DEFAULTS=$tmp/no-such-ref soc_only_changes "$tmp/c.args" | tr '\n' ' ')"

# What it buys for the reference phone, when its private repository is available.
if [ "$real_ref" -eq 1 ]; then
    all=$(tr -d '\r' < "$ref" | tr '\n' ' ' | wc -c | tr -d ' ')
    echo "info: all 16 soc_* values are $all characters of the kernel's 607; for the reference phone $(SOC_DEFAULTS=$defaults soc_only_changes "$ref" | wc -c | tr -d ' ') are sent"
fi
[ "$fails" -eq 0 ] && echo "soc-only-changes-test: all passed" || { echo "soc-only-changes-test: $fails FAILED"; exit 1; }
