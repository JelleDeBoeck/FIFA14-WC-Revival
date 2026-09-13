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

                arg0_preview: safePreview(args[0], 64),
                arg1_preview: safePreview(args[1], 64),
                arg2_preview: safePreview(args[2], 64),
                arg3_preview: safePreview(args[3], 64),
                arg4_preview: safePreview(args[4], 64),
                arg5_preview: safePreview(args[5], 64),

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

    const wcNationMap = {
        // GROUP A
        54:  { teamId: 1370,   confederationId: 4 }, // Brazil
        10:  { teamId: 1328,   confederationId: 2 }, // Croatia
        83:  { teamId: 1386,   confederationId: 7 }, // Mexico
        103: { teamId: 1395,   confederationId: 3 }, // Cameroon

        // GROUP B
        45:  { teamId: 1362,   confederationId: 2 }, // Spain
        34:  { teamId: 105035, confederationId: 2 }, // Netherlands / Holland
        55:  { teamId: 111459, confederationId: 4 }, // Chile
        195: { teamId: 1415,   confederationId: 5 }, // Australia

        // GROUP C
        56:  { teamId: 111109, confederationId: 4 }, // Colombia
        22:  { teamId: 1338,   confederationId: 2 }, // Greece
        108: { teamId: 111112, confederationId: 3 }, // Ivory Coast
        163: { teamId: 1411,   confederationId: 5 }, // Japan

        // GROUP D
        60:  { teamId: 1377,   confederationId: 4 }, // Uruguay
        72:  { teamId: 1383,   confederationId: 7 }, // Costa Rica
        14:  { teamId: 1318,   confederationId: 2 }, // England
        27:  { teamId: 1343,   confederationId: 2 }, // Italy

        // GROUP E
        47:  { teamId: 1364,   confederationId: 2 }, // Switzerland
        57:  { teamId: 111465, confederationId: 4 }, // Ecuador
        18:  { teamId: 1335,   confederationId: 2 }, // France
        81:  { teamId: 111548, confederationId: 7 }, // Honduras

        // GROUP F
        52:  { teamId: 1369,   confederationId: 4 }, // Argentina
        8:   { teamId: 105013, confederationId: 2 }, // Bosnia & Herzegovina
        161: { teamId: 111115, confederationId: 5 }, // Iran
        133: { teamId: 1393,   confederationId: 3 }, // Nigeria

        // GROUP G
        21:  { teamId: 1337,   confederationId: 2 }, // Germany
        38:  { teamId: 1354,   confederationId: 2 }, // Portugal
        117: { teamId: 111462, confederationId: 3 }, // Ghana
        95:  { teamId: 1387,   confederationId: 7 }, // United States

        // GROUP H
        7:   { teamId: 1325,   confederationId: 2 }, // Belgium
        97:  { teamId: 111448, confederationId: 3 }, // Algeria
        40:  { teamId: 1357,   confederationId: 2 }, // Russia
        167: { teamId: 974,    confederationId: 5 }  // Korea Republic
    };

    const currentNationByThread = {};

    function hookActualValue(name, rva) {
        const address = base.add(rva);

        Interceptor.attach(address, {
            onEnter(args) {
                const tid = Process.getCurrentThreadId();
                const original = u32(this.context.eax);

                if (name === 'NATIONALITY_ASSET_ID') {
                    currentNationByThread[tid] = original;
                }

                const nation = currentNationByThread[tid];
                const wc = wcNationMap[nation];

                if (wc) {
                    if (name === 'CONFEDERATION_ASSET_ID') {
                        this.context.eax = ptr(wc.confederationId);
                    }

                    if (name === 'TEAM_ASSET_ID') {
                        this.context.eax = ptr(wc.teamId);
                    }
                }

                emit('wc-card-actual-value', {
                    field: name,
                    rva: '0x' + rva.toString(16),

                    nation: nation || null,

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
        'NATIONALITY_ASSET_ID',
        0x00024C4A
    );

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