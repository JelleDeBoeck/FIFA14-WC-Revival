import { readFile } from "node:fs/promises";
import { openFifaDatabase } from "fifa-t3db";

const DB_PATH = "./extracted/cards_db/cards_ng_db.db";
const META_PATH = "./extracted/cards_db/cards_ng_db-meta.xml";

const [databaseBytes, metadataXml] = await Promise.all([
  readFile(DB_PATH),
  readFile(META_PATH, "utf8"),
]);

const db = openFifaDatabase({
  database: databaseBytes,
  metadataXml,
});

const targets = new Set([
  158023,
  117598535,
]);

const tableNames = [
  ...metadataXml.matchAll(/<table\s+name="([^"]+)"/g),
].map((m) => m[1]);

console.log("tables:", tableNames.length);

for (const tableName of tableNames) {
  let table;

  try {
    table = db.readTable(tableName);
  } catch {
    continue;
  }

  const hits = [];

  for (const row of table.rows ?? []) {
    const matchedFields = [];

    for (const [key, value] of Object.entries(row)) {
      if (
        typeof value === "number" &&
        targets.has(Number(value))
      ) {
        matchedFields.push(`${key}=${value}`);
      }
    }

    if (matchedFields.length) {
      hits.push({
        matchedFields,
        row,
      });
    }
  }

  if (!hits.length) {
    continue;
  }

  console.log("\n========================================");
  console.log("TABLE:", tableName);
  console.log("records:", table.info?.recordCount);
  console.log("========================================");

  for (const hit of hits) {
    console.log("\nMATCH:", hit.matchedFields.join(", "));
    console.dir(hit.row, { depth: null });
  }
}