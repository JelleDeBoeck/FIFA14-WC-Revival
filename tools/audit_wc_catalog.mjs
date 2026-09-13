import fs from "node:fs";
import path from "node:path";
import { openFifaDatabase } from "fifa-t3db";

const root = process.cwd();

const catalogPath = path.join(
  root,
  "src",
  "backend",
  "fifa14-special-catalog.v240.json"
);

const dbPath = path.join(
  root,
  "extracted",
  "futwc_db",
  "futwc_ng_db.db"
);

const metaPath = path.join(
  root,
  "extracted",
  "futwc_db",
  "futwc_ng_db-meta.xml"
);

const catalogDoc = JSON.parse(fs.readFileSync(catalogPath, "utf8"));
const catalog = Array.isArray(catalogDoc)
  ? catalogDoc
  : (catalogDoc.players ?? catalogDoc.items ?? []);

const databaseBytes = fs.readFileSync(dbPath);
const metadataXml = fs.readFileSync(metaPath, "utf8");

const db = openFifaDatabase({
  database: databaseBytes,
  metadataXml,
});

const players = db.readTable("players");
const nativeRows = players.rows ?? [];
const nativeIds = new Set(
  nativeRows.map(p => Number(p.playerid))
);

const wc = catalog.filter(
  r => String(r.cardType ?? "").toLowerCase() === "worldcup"
);

const errors = [];

for (const r of wc) {
  const assetId = Number(r.assetId ?? 0);
  const version = Number(r.version ?? 1);
  const resourceId = Number(r.resourceId ?? 0);

  const expectedResource =
    version === 1
      ? assetId
      : assetId + 0x02000000 + (version - 1) * 0x01000000;

  const problems = [];

  if (!nativeIds.has(assetId)) {
    problems.push("PLAYERID_MISSING");
  }

  if (resourceId !== expectedResource) {
    problems.push(
      `RESOURCE_BAD expected=${expectedResource}`
    );
  }

  if (problems.length) {
    errors.push({
      name: r.name,
      assetId,
      resourceId,
      version,
      matchMethod: r.matchMethod,
      problems,
    });
  }
}

console.log("WC catalog records:", wc.length);
console.log("Native WC players:", nativeRows.length);
console.log("Errors:", errors.length);

for (const e of errors) {
  console.log(
    `${e.name} | asset=${e.assetId} | resource=${e.resourceId} | v${e.version} | ${e.matchMethod} | ${e.problems.join(", ")}`
  );
}

if (errors.length === 0) {
  console.log("WC CATALOG INTEGRITY OK");
}
