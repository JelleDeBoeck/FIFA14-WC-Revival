import fs from "node:fs";
import path from "node:path";
import { openFifaDatabase } from "fifa-t3db";

const root = process.cwd();

const catalogDoc = JSON.parse(
  fs.readFileSync(
    path.join(root, "src/backend/fifa14-special-catalog.v240.json"),
    "utf8"
  )
);

const catalog = Array.isArray(catalogDoc)
  ? catalogDoc
  : (catalogDoc.players ?? catalogDoc.items ?? []);

const db = openFifaDatabase({
  database: fs.readFileSync(
    path.join(root, "extracted/futwc_db/futwc_ng_db.db")
  ),
  metadataXml: fs.readFileSync(
    path.join(root, "extracted/futwc_db/futwc_ng_db-meta.xml"),
    "utf8"
  ),
});

const playersTable = db.readTable("players");
const namesTable = db.readTable("playernames");

const players = playersTable.rows ?? [];
const names = namesTable.rows ?? [];

const nameById = new Map(
  names.map(r => [Number(r.nameid), String(r.name ?? "")])
);

function norm(s) {
  return String(s ?? "")
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, " ")
    .trim()
    .replace(/\s+/g, " ");
}

function playerNames(p) {
  const first = nameById.get(Number(p.firstnameid)) ?? "";
  const last = nameById.get(Number(p.lastnameid)) ?? "";
  const common = nameById.get(Number(p.commonnameid)) ?? "";
  const jersey = nameById.get(Number(p.playerjerseynameid)) ?? "";

  return {
    first,
    last,
    common,
    jersey,
    full: `${first} ${last}`.trim(),
  };
}

function levenshtein(a, b) {
  a = norm(a);
  b = norm(b);

  const dp = Array(b.length + 1)
    .fill(0)
    .map((_, i) => i);

  for (let i = 1; i <= a.length; i++) {
    let prev = dp[0];
    dp[0] = i;

    for (let j = 1; j <= b.length; j++) {
      const old = dp[j];
      const cost = a[i - 1] === b[j - 1] ? 0 : 1;

      dp[j] = Math.min(
        dp[j] + 1,
        dp[j - 1] + 1,
        prev + cost
      );

      prev = old;
    }
  }

  return dp[b.length];
}

function scoreName(target, names) {
  const variants = [
    names.full,
    names.common,
    names.last,
    names.jersey,
  ].filter(Boolean);

  let best = 9999;

  for (const candidate of variants) {
    if (norm(target) === norm(candidate))
      return 0;

    best = Math.min(best, levenshtein(target, candidate));
  }

  return best;
}

const nativeIds = new Set(players.map(p => Number(p.playerid)));

const broken = catalog.filter(r =>
  String(r.cardType ?? "").toLowerCase() === "worldcup" &&
  !nativeIds.has(Number(r.assetId))
);

console.log("Broken WC records:", broken.length);

for (const card of broken) {
  const targetNation = Number(card.nation ?? -1);

  const candidates = players
    .filter(p => Number(p.nationality) === targetNation)
    .map(p => {
      const n = playerNames(p);

      return {
        playerid: Number(p.playerid),
        rating: Number(p.overallrating),
        position: Number(p.preferredposition1),
        names: n,
        score: scoreName(card.name, n),
      };
    })
    .sort((a, b) =>
      a.score - b.score ||
      Math.abs(a.rating - Number(card.rating ?? 0)) -
      Math.abs(b.rating - Number(card.rating ?? 0))
    )
    .slice(0, 5);

  console.log("\n==================================================");
  console.log(
    `${card.name} | OLD asset=${card.assetId} | nation=${card.nation} | rating=${card.rating}`
  );

  for (const c of candidates) {
    console.log(
      `  score=${c.score} ` +
      `playerid=${c.playerid} ` +
      `rating=${c.rating} ` +
      `pos=${c.position} ` +
      `full="${c.names.full}" ` +
      `common="${c.names.common}" ` +
      `jersey="${c.names.jersey}"`
    );
  }
}
