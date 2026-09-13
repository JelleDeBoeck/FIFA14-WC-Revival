import { readFile } from "node:fs/promises";
import { openFifaDatabase } from "fifa-t3db";

const [databaseBytes, metadataXml] = await Promise.all([
  readFile("./extracted/futwc_db/futwc_ng_db.db"),
  readFile("./extracted/futwc_db/futwc_ng_db-meta.xml", "utf8"),
]);

const db = openFifaDatabase({
  database: databaseBytes,
  metadataXml,
});

const players = db.readTable("players");

console.log("records:", players.info.recordCount);

const messi = players.rows.find(
  (row) => Number(row.playerid) === 158023
);

console.log("MESSI:");
console.dir(messi, { depth: null });

console.log("\nPLAYER KEYS:");
console.log(Object.keys(players.rows[0] ?? {}).sort());