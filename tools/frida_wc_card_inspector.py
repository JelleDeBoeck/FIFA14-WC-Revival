import argparse
import json
import time
from datetime import datetime, timezone
from pathlib import Path

import frida


def utc_now():
    return datetime.now(timezone.utc).isoformat()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--pid", type=int, required=True)
    parser.add_argument(
        "--log",
        default=r".\logs\wc-card-inspector.jsonl",
    )
    parser.add_argument("--run-seconds", type=int, default=1800)
    args = parser.parse_args()

    agent = r"""
'use strict';

const MODULE_NAME = 'CardsDLLzf.dll';

let installed = false;
let sequence = 0;
let lastField = Object.create(null);

function emit(kind, extra) {
    const obj = Object.assign({
        kind: kind,
        seq: ++sequence,
        time_ms: Date.now()
    }, extra || {});
    send(obj);
}

function u32(v) {
    try {
        return v.toUInt32();
    } catch (_) {
        return 0;
    }
}

function safePreview(p, amount) {
    try {
        if (!p || p.isNull())
            return null;

        const range = Process.findRangeByAddress(p);
        if (!range || range.protection.indexOf('r') === -1)
            return null;

        const n = Math.min(amount || 32, range.size);
        const buf = p.readByteArray(n);

        if (!buf)
            return null;

        return Array.from(new Uint8Array(buf))
            .map(x => x.toString(16).padStart(2, '0'))
            .join(' ');
    } catch (_) {
        return null;
    }
}

function snapshotRegs(ctx) {
    return {
        eax: ctx.eax.toString(),
        ebx: ctx.ebx.toString(),
        ecx: ctx.ecx.toString(),
        edx: ctx.edx.toString(),
        esi: ctx.esi.toString(),
        edi: ctx.edi.toString(),
        ebp: ctx.ebp.toString(),
        esp: ctx.esp.toString()
    };
}

function hookField(base, name, rva) {
    const address = base.add(rva);

    Interceptor.attach(address, {
        onEnter(args) {
            const original = u32(this.context.eax);
            let patched = original;

            /*
             * TEMP WC ART PROOF
             *
             * Archie Thompson:
             * Australia WC team = 1415
             * AFC confederation = 5
             */

            const key =
                name + ':' +
                original.toString() + ':' +
                this.context.esi.toString();

            const now = Date.now();

            if (lastField[key] && now - lastField[key] < 500)
                return;

            lastField[key] = now;

            emit('wc-card-field', {
                field: name,
                hook_rva: '0x' + rva.toString(16),

                original_u32: original,
                original_hex: '0x' + original.toString(16),

                patched_u32: patched,
                patched_hex: '0x' + patched.toString(16),

                registers: snapshotRegs(this.context)
            });
        }
    });

    emit('wc-card-field-hook-installed', {
        field: name,
        rva: '0x' + rva.toString(16),
        address: address.toString()
    });
}

function install() {
    if (installed)
        return;

    let mod = null;

    try {
        mod = Process.getModuleByName(MODULE_NAME);
    } catch (_) {
        return;
    }

    const base = mod.base;

    emit('wc-card-module-found', {
        module: MODULE_NAME,
        base: base.toString(),
        size: mod.size
    });

    // GetPlayerCardInfo native binding.
    const getPlayerCardInfo = base.add(0x0007CEA0);

    Interceptor.attach(getPlayerCardInfo, {
        onEnter(args) {
            this.shouldLog = true;

            emit('get-player-card-info-enter', {
                address: getPlayerCardInfo.toString(),
                thread_id: Process.getCurrentThreadId(),

                arg0: args[0].toString(),
                arg1: args[1].toString(),
                arg2: args[2].toString(),
                arg3: args[3].toString(),
                arg4: args[4].toString(),
                arg5: args[5].toString(),

                arg0_preview: safePreview(args[0], 48),
                arg1_preview: safePreview(args[1], 48),
                arg2_preview: safePreview(args[2], 48),

                registers: snapshotRegs(this.context)
            });
        },

        onLeave(retval) {
            if (!this.shouldLog)
                return;

            emit('get-player-card-info-leave', {
                retval: retval.toString(),
                retval_u32: u32(retval),
                retval_preview: safePreview(retval, 64)
            });
        }
    });

    emit('get-player-card-info-hook-installed', {
        rva: '0x0007CEA0',
        address: getPlayerCardInfo.toString()
    });

    /*
       Deze adressen zijn telkens de instruction direct NA de
       property lookup call.

       Daardoor bevat EAX het resultaat van de native lookup.
    */

    hookField(
        base,
        'NATIONALITY_ASSET_ID',
        0x00024C57
    );

    hookField(
        base,
        'CONFEDERATION_ASSET_ID',
        0x00024CFA
    );

    hookField(
        base,
        'TEAM_ASSET_ID',
        0x00024D11
    );

    hookField(
        base,
        'CARD_TOTW',
        0x00024847
    );

    function hookActualValue(name, rva) {
        const address = base.add(rva);

        Interceptor.attach(address, {
            onEnter(args) {
                const original = u32(this.context.eax);

                if (name === 'CONFEDERATION_ASSET_ID') {
                    this.context.eax = ptr(5);
                }

                if (name === 'TEAM_ASSET_ID') {
                    this.context.eax = ptr(1415);
                }

                emit('wc-card-actual-value', {
                    field: name,
                    rva: '0x' + rva.toString(16),

                    original_u32: original,
                    original_hex: '0x' + original.toString(16),

                    patched_u32: u32(this.context.eax),
                    patched_hex: this.context.eax.toString(),

                    registers: snapshotRegs(this.context)
                });
            }
        });

        emit('wc-card-actual-hook-installed', {
            field: name,
            rva: '0x' + rva.toString(16),
            address: address.toString()
        });
    }

    hookActualValue(
        'CONFEDERATION_ASSET_ID',
        0x00024CED
    );

    hookActualValue(
        'TEAM_ASSET_ID',
        0x00024D07
    );

    installed = true;

    emit('wc-card-inspector-ready', {
        module: MODULE_NAME,
        base: base.toString()
    });
}

install();

const timer = setInterval(function () {
    if (!installed)
        install();
    else
        clearInterval(timer);
}, 500);
"""

    output = Path(args.log)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.unlink(missing_ok=True)

    session = frida.get_local_device().attach(args.pid)
    script = session.create_script(agent)

    log_handle = output.open("a", encoding="utf-8")

    def record(event):
        line = json.dumps(
            {"outer_time": utc_now(), **event},
            ensure_ascii=False,
        )
        log_handle.write(line + "\n")
        log_handle.flush()

        kind = event.get("kind", "")
        if (
            "ready" in kind
            or "installed" in kind
            or "module-found" in kind
            or "error" in kind
        ):
            print(line, flush=True)

    def on_message(message, data):
        if message.get("type") == "send":
            payload = message.get("payload")
            if isinstance(payload, dict):
                record(payload)
            else:
                record({
                    "kind": "frida-send",
                    "payload": payload,
                })
        else:
            record({
                "kind": "frida-message",
                "message": message,
            })

    script.on("message", on_message)
    script.load()

    print(
        f"\nWC card inspector attached to PID {args.pid}"
        f"\nlog: {output}\n",
        flush=True,
    )

    deadline = time.monotonic() + max(1, args.run_seconds)

    try:
        while time.monotonic() < deadline:
            time.sleep(0.25)
    except KeyboardInterrupt:
        pass
    finally:
        try:
            script.unload()
        except Exception:
            pass

        try:
            session.detach()
        except Exception:
            pass

        log_handle.close()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())