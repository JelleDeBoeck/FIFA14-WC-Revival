import { readFile } from "node:fs/promises";
import { openFifaDatabase } from "fifa-t3db";

async function loadDb(dbPath, metaPath) {
  const [databaseBytes, metadataXml] = await Promise.all([
    readFile(dbPath),
    readFile(metaPath, "utf8"),
  ]);

  return openFifaDatabase({
    database: databaseBytes,
    metadataXml,
  });
}

const wcDb = await loadDb(
  "./extracted/futwc_db/futwc_ng_db.db",
  "./extracted/futwc_db/futwc_ng_db-meta.xml"
);

const cardsDb = await loadDb(
  "./extracted/cards_db/cards_ng_db.db",
  "./extracted/cards_db/cards_ng_db-meta.xml"
);

const ids = [
  172114, // Arevalo
  167495, // Neuer
  158023, // Messi
];

function dump(db, label) {
  const players = db.readTable("players");

  console.log(`\n\n================ ${label} ================`);
  console.log("records:", players.info.recordCount);

  for (const id of ids) {
    const row = players.rows.find(
      (row) => Number(row.playerid) === id
    );

    console.log(`\n---------- ${id} ----------`);

    if (!row) {
      console.log("NIET GEVONDEN");
      continue;
    }

    console.dir(row, {
      depth: null,
      sorted: true,
    });
  }
}

dump(wcDb, "FUTWC DB");
dump(cardsDb, "CARDS DB");