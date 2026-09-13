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
const names = db.readTable("playernames");

const candidates = [176518, 178691, 182103, 186408];

function nameById(id) {
  return names.rows.find(
    (row) => Number(row.nameid) === Number(id)
  )?.name ?? `UNKNOWN(${id})`;
}

for (const id of candidates) {
  const p = players.rows.find(
    (row) => Number(row.playerid) === id
  );

  if (!p) {
    console.log(`\n${id}: NIET GEVONDEN`);
    continue;
  }

  const first = nameById(p.firstnameid);
  const last = nameById(p.lastnameid);
  const jersey = nameById(p.playerjerseynameid);

  console.log(`\n========== ${id} ==========`);
  console.log("firstname :", first);
  console.log("lastname  :", last);
  console.log("jersey    :", jersey);
  console.log("rating    :", p.overallrating);
  console.log("position  :", p.preferredposition1);
  console.log("height    :", p.height);
  console.log("weight    :", p.weight);
  console.log("birthdate :", p.birthdate);
}