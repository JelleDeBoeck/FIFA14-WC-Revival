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
const links = db.readTable("teamplayerlinks");
const nations = db.readTable("nations");
const teams = db.readTable("teams");

const player = players.rows.find(
  (row) => Number(row.playerid) === 158023
);

const playerLinks = links.rows.filter(
  (row) => Number(row.playerid) === 158023
);

const nation = nations.rows.find(
  (row) => Number(row.nationid) === Number(player?.nationality)
);

console.log("PLAYER:");
console.dir(player, { depth: null });

console.log("\nTEAMPLAYERLINKS:");
console.dir(playerLinks, { depth: null });

console.log("\nNATION:");
console.dir(nation, { depth: null });

console.log("\nLINKED TEAMS:");
for (const link of playerLinks) {
  const team = teams.rows.find(
    (row) => Number(row.teamid) === Number(link.teamid)
  );

  console.log("\nteamid =", link.teamid);
  console.dir(team, { depth: null });
}