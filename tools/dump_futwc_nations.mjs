import { readFile } from "node:fs/promises";
import { openFifaDatabase } from "fifa-t3db";

const dbPath =
  "./extracted/futwc_db/futwc_ng_db.db";

const metaPath =
  "./extracted/futwc_db/futwc_ng_db-meta.xml";

const [databaseBytes, metadataXml] = await Promise.all([
  readFile(dbPath),
  readFile(metaPath, "utf8"),
]);

const db = openFifaDatabase({
  database: databaseBytes,
  metadataXml,
});

const nations = db.readTable("nations");

console.log("records:", nations.info.recordCount);

console.table(
  nations.rows.map((row) => ({
    nationid: row.nationid,
    nationname: row.nationname,
    teamid: row.teamid,
    confederation: row.confederation,
    worldcupqualified: row.worldcupqualified,
  }))
);