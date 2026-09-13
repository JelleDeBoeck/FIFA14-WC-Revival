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

function rows(table) {
  if (Array.isArray(table)) return table;
  if (Array.isArray(table?.rows)) return table.rows;
  if (Array.isArray(table?.records)) return table.records;
  if (Array.isArray(table?.data)) return table.data;

  throw new Error(
    "Onbekende table-structuur: " +
    JSON.stringify(Object.keys(table ?? {}))
  );
}

const players = rows(db.readTable("players"));
const nations = rows(db.readTable("nations"));

const wanted = [
  34373,   // Archie Thompson
  209457,  // Jairo Arrieta
  190588,  // Rodney Wallace
  199737,  // kaart die als vreemde GK verscheen
];

for (const id of wanted) {
  const player = players.find(
    p => Number(p.playerid) === id
  );

  if (!player) {
    console.log({
      playerid: id,
      status: "NOT FOUND IN WC DB",
    });
    continue;
  }

  const nation = nations.find(
    n => Number(n.nationid) === Number(player.nationality)
  );

  console.log({
    playerid: id,
    nationality: Number(player.nationality),
    nationName: nation?.nationname ?? "UNKNOWN",
    wcTeamId: Number(nation?.teamid ?? -1),
    confederation: Number(nation?.confederation ?? -1),
    rating: Number(player.overallrating ?? 0),
  });
}