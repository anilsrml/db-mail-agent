import { readFileSync } from "node:fs";
import vm from "node:vm";

const html = readFileSync("app/static/index.html", "utf8");
const scripts = [...html.matchAll(/<script>([\s\S]*?)<\/script>/g)];

if (scripts.length !== 1) {
  throw new Error(`Bir adet inline script bekleniyordu, bulunan: ${scripts.length}`);
}

// Kodu çalıştırmadan yalnızca JavaScript sözdizimini derler.
new vm.Script(scripts[0][1], { filename: "app/static/index.html" });
console.log("Web arayüzü JavaScript sözdizimi geçerli.");
