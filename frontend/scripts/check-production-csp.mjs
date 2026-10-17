import assert from "node:assert/strict";
import { readFile, readdir } from "node:fs/promises";

const outputDirectory = new URL("../dist/", import.meta.url);
const html = await readFile(new URL("index.html", outputDirectory), "utf8");
const policyTag = html.match(
  /<meta\s+http-equiv="Content-Security-Policy"\s+content="([^"]+)"\s*\/?>/i,
);
assert.ok(policyTag, "Production index.html must include a CSP meta policy.");

const policy = new Map(
  policyTag[1]
    .split(";")
    .map((directive) => directive.trim().split(/\s+/))
    .filter(([name]) => name)
    .map(([name, ...sources]) => [name, sources]),
);
const policyPosition = html.indexOf(policyTag[0]);
for (const resourceTag of html.matchAll(/<(?:script|link)\b[^>]*>/gi)) {
  assert.ok(
    policyPosition < resourceTag.index,
    "CSP meta policy must precede resource tags in the document head.",
  );
}

assert.ok(policy.get("default-src")?.includes("'self'"));
assert.ok(policy.get("script-src")?.includes("'self'"));
assert.ok(!policy.get("script-src")?.includes("'unsafe-inline'"));
assert.ok(!policy.get("script-src")?.includes("'unsafe-eval'"));
assert.ok(policy.get("style-src")?.includes("https://fonts.googleapis.com"));
assert.ok(policy.get("font-src")?.includes("https://fonts.gstatic.com"));
assert.ok(policy.get("connect-src")?.includes("'self'"));
const configuredApiBase = process.env.VITE_API_BASE_URL?.trim();
if (configuredApiBase) {
  assert.ok(
    policy.get("connect-src")?.includes(new URL(configuredApiBase).origin),
    "CSP connect-src must permit the configured API origin.",
  );
}
assert.ok(policy.get("frame-ancestors")?.includes("'none'"));
assert.ok(policy.get("object-src")?.includes("'none'"));

const scriptAssets = [...html.matchAll(/<script\b[^>]*src="([^"]+)"/gi)];
const stylesheetAssets = [
  ...html.matchAll(/<link\b(?=[^>]*\brel="stylesheet")[^>]*href="([^"]+)"/gi),
];
assert.ok(scriptAssets.length, "Production HTML must load a bundled script.");
assert.ok(
  stylesheetAssets.length,
  "Production HTML must load a bundled stylesheet.",
);
for (const [, assetPath] of [...scriptAssets, ...stylesheetAssets]) {
  assert.equal(
    new URL(assetPath, "https://mindbridge.invalid").origin,
    "https://mindbridge.invalid",
    `Asset ${assetPath} must be same-origin under the production CSP.`,
  );
}

const assetsDirectory = new URL("assets/", outputDirectory);
const assetFiles = await readdir(assetsDirectory);
const bundles = await Promise.all(
  assetFiles.map((name) => readFile(new URL(name, assetsDirectory), "utf8")),
);
const javascript = bundles.join("\n");
assert.ok(
  javascript.includes("/api/v1/auth/login") &&
    javascript.includes("/api/v1/auth/me"),
  "Built frontend must include the existing login and session API calls.",
);
const stylesheet = bundles.find((content) => content.includes("@import"));
assert.ok(stylesheet, "Built stylesheet must contain the expected font import.");
const fontImport = stylesheet.match(
  /@import\s+(?:url\()?["']?(https?:\/\/[^"')\s;]+)/i,
);
assert.ok(fontImport, "Expected an external Google Fonts stylesheet import.");
assert.ok(
  policy.get("style-src")?.includes(new URL(fontImport[1]).origin),
  "CSP style-src must permit the font stylesheet used by the built app.",
);

console.log("Production CSP permits the built frontend assets, fonts, and API calls.");
