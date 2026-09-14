import fs from "node:fs";
import { openFifaDatabase } from "fifa-t3db";

const db = openFifaDatabase({
    database: fs.readFileSync("./extracted/futwc_db/futwc_ng_db.db"),
    metadataXml: fs.readFileSync("./extracted/futwc_db/futwc_ng_db-meta.xml", "utf8"),
});

const teamId = 1364;

const nations = db.readTable("nations").rows;
const nation = nations.find(row => Number(row.teamid) === teamId);

console.log("=== NATION ===");
console.log(nation ?? `No nation with teamid=${teamId}`);

console.log("\n=== TEAM ===");
const teams = db.readTable("teams").rows;
console.log(teams.find(row => Number(row.teamid) === teamId) ?? "No team");

console.log("\n=== BADGE CARDS ===");
console.log(
    db.readTable("fcc_badgecards").rows.filter(
        row => Number(row.teamid) === teamId
    )
);

console.log("\n=== KIT CARDS ===");
console.log(
    db.readTable("fcc_kitcards").rows.filter(
        row => Number(row.teamid) === teamId
    )
);

console.log("\n=== MANAGER ===");
console.log(
    db.readTable("manager").rows.filter(
        row => Number(row.teamid) === teamId
    )
);
