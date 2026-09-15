import frida
import sqlite3
import sys
import time
from pathlib import Path

pid = int(sys.argv[1])

DB = Path(r".\state\wc-revival-worldcup.sqlite3")

session = frida.attach(pid)

script = session.create_script(r"""
'use strict';

const dll = Process.getModuleByName("CardsDLLzf.dll");

// Preferred VA 0x101D7C7C -> RVA 0x1D7C7C
const singletonSlot = dll.base.add(0x1D7C7C);

rpc.exports = {
    setteamid(teamId) {
        const controller = singletonSlot.readPointer();

        if (controller.isNull())
            return "controller=null";

        const gate   = controller.add(0x13148);
        const nation = controller.add(0x1314C);
        const team   = controller.add(0x13150);

        const oldTeam = team.readU32();

        // This is the state consumed by vtable +0x1F8 / RVA 0x118DC0.
        gate.writeU32(1);
        team.writeU32(teamId >>> 0);

        return (
            "controller=" + controller +
            " old=" + oldTeam +
            " new=" + team.readU32() +
            " nationCache=" + nation.readU32()
        );
    }
};
""")

script.load()

last_team_id = None

print("[WC TeamName] attached")
print("[WC TeamName] DB:", DB)
print("[WC TeamName] Ctrl+C to stop")
print()

while True:
    try:
        con = sqlite3.connect(DB)
        row = con.execute("""
            SELECT team_id
            FROM clubs
            WHERE team_id IS NOT NULL
              AND team_id > 0
            ORDER BY rowid DESC
            LIMIT 1
        """).fetchone()
        con.close()

        if not row:
            time.sleep(0.5)
            continue

        team_id = int(row[0])

        # Write on change, plus periodically re-assert because native code
        # can clear +0x13150 while navigating.
        changed = team_id != last_team_id

        result = script.exports_sync.setteamid(team_id)

        if changed:
            print(f"[WC TeamName] teamId={team_id}")
            print(f"[WC TeamName] {result}")
            last_team_id = team_id

        time.sleep(0.5)

    except KeyboardInterrupt:
        break
    except Exception as exc:
        print("[WC TeamName]", exc)
        time.sleep(1.0)

session.detach()
