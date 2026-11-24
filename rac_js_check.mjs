// Ελέγχει ότι οι κανόνες της online εφαρμογής (web/rac.js) δίνουν ίδιες αποφάσεις με την Python.
import { RAC } from "../web/rac.js";
import fs from "fs";
const ex = JSON.parse(fs.readFileSync(process.argv[2], "utf8"));
let ok = 0;
for (const e of ex) {
  const a = { age: e.age, months: e.months, reg: e.reg, cont: e.cont, digital: e.digital, codes: e.codes };
  const elig = RAC["374859"].filter(r => r.applies(a)).every(r => r.check(a));
  if (elig === e.expected) ok++; else console.log("MISMATCH", e.name);
}
console.log(`JS rules: ${ok}/${ex.length} ίδια με το αναμενόμενο`);
