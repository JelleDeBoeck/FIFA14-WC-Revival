import { readFile, writeFile } from "node:fs/promises";
import { openFifaDatabase } from "fifa-t3db";

const dbPath = "./extracted/futwc_db/futwc_ng_db.db";
const metaPath = "./extracted/futwc_db/futwc_ng_db-meta.xml";
const outputPath = "./src/backend/fifa14-wc-nations.v1.json";

const [databaseBytes, metadataXml] = await Promise.all([
  readFile(dbPath),
  readFile(metaPath, "utf8"),
]);

const db = openFifaDatabase({
  database: databaseBytes,
  metadataXml,
});

const nations = db.readTable("nations").rows;
const teams = db.readTable("teams").rows;
const badges = db.readTable("fcc_badgecards").rows;
const kits = db.readTable("fcc_kitcards").rows;

const teamsById = new Map(
  teams.map((row) => [Number(row.teamid), row]),
);

const badgesByTeamId = new Map();
for (const row of badges) {
  const teamId = Number(row.teamid);
  const list = badgesByTeamId.get(teamId) ?? [];
  list.push(row);
  badgesByTeamId.set(teamId, list);
}

const kitsByTeamId = new Map();
for (const row of kits) {
  const teamId = Number(row.teamid);
  const list = kitsByTeamId.get(teamId) ?? [];
  list.push(row);
  kitsByTeamId.set(teamId, list);
}

const catalog = {};

for (const nation of nations) {
  const teamId = Number(nation.teamid);

  // A nation without a real linked team cannot be used as a FUTWC
  // Support Nation identity.
  if (teamId <= 0) {
    continue;
  }

  const team = teamsById.get(teamId);
  if (!team) {
    continue;
  }

  const badgeRows = badgesByTeamId.get(teamId) ?? [];
  const kitRows = kitsByTeamId.get(teamId) ?? [];

  const badge = badgeRows[0] ?? null;
  const homeKit =
    kitRows.find((row) => Number(row.category) === 2) ?? null;
  const awayKit =
    kitRows.find((row) => Number(row.category) === 3) ?? null;

  catalog[String(teamId)] = {
    teamId,
    teamAssetId: Number(team.assetid),
    nationId: Number(nation.nationid),
    name: String(nation.nationname),
    teamName: String(team.teamname),
    confederation: Number(nation.confederation),
    worldCupQualified: Number(nation.worldcupqualified),

    badge: badge
      ? {
          cardDbId: Number(badge.carddbid),
          assetId: Number(badge.assetid),
          cardAssetId: Number(badge.cardassetid),
          name: String(badge.name),
          description: String(badge.biodescription),
        }
      : null,

    kits: {
      home: homeKit
        ? {
            cardDbId: Number(homeKit.carddbid),
            assetId: Number(homeKit.assetid),
            cardAssetId: Number(homeKit.cardassetid),
            category: Number(homeKit.category),
            value: Number(homeKit.value),
            year: Number(homeKit.year),
            weightrare: Number(homeKit.weightrare),
            name: String(homeKit.name),
            description: String(homeKit.biodescription),
          }
        : null,

      away: awayKit
        ? {
            cardDbId: Number(awayKit.carddbid),
            assetId: Number(awayKit.assetid),
            cardAssetId: Number(awayKit.cardassetid),
            category: Number(awayKit.category),
            value: Number(awayKit.value),
            year: Number(awayKit.year),
            weightrare: Number(awayKit.weightrare),
            name: String(awayKit.name),
            description: String(awayKit.biodescription),
          }
        : null,
    },
  };
}

await writeFile(
  outputPath,
  `${JSON.stringify(catalog, null, 2)}\n`,
  "utf8",
);

console.log(`Wrote ${Object.keys(catalog).length} WC nations to ${outputPath}`);

console.log("\nSwitzerland sanity check:");
console.dir(catalog["1364"], { depth: null });