/**
 * HTML -> PDF via the Chrome DevTools Protocol. Zero npm dependencies:
 * Node 22+ ships a global WebSocket, so we drive Chrome directly.
 *
 *   node docs/planning/source/build_pdf.mjs docs/planning/source/prd_v2.html docs/planning/MPSTME_GUARDIAN_PRD_v2.0.pdf "Footer title"
 *
 * Why CDP instead of `--print-to-pdf`: that flag stamps Chrome's own header
 * (date + file:// URL), which we cannot style. Page.printToPDF lets us supply
 * our own header/footer templates and real page numbers.
 */
import { spawn } from "node:child_process";
import { writeFileSync, mkdtempSync } from "node:fs";
import { tmpdir } from "node:os";
import { join, resolve } from "node:path";

const CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome";
const [srcArg, outArg, footerTitle = "", settleMs = "4000"] = process.argv.slice(2);
if (!srcArg || !outArg) {
  console.error("usage: node build_pdf.mjs <input.html> <output.pdf> [footerTitle] [settleMs]");
  process.exit(1);
}
const src = resolve(srcArg), out = resolve(outArg);
const PORT = 9333 + Math.floor(process.pid % 500);

const profile = mkdtempSync(join(tmpdir(), "guardian-pdf-"));
const chrome = spawn(CHROME, [
  "--headless=new", "--disable-gpu", "--no-first-run", "--no-default-browser-check",
  "--allow-file-access-from-files", `--user-data-dir=${profile}`,
  `--remote-debugging-port=${PORT}`, "about:blank",
], { stdio: ["ignore", "ignore", "ignore"] });

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

async function endpoint() {
  for (let i = 0; i < 100; i++) {
    try {
      const r = await fetch(`http://127.0.0.1:${PORT}/json/version`);
      if (r.ok) return (await r.json()).webSocketDebuggerUrl;
    } catch { /* chrome not up yet */ }
    await sleep(120);
  }
  throw new Error("Chrome DevTools endpoint never came up");
}

class CDP {
  constructor(ws) { this.ws = ws; this.id = 0; this.pending = new Map(); this.handlers = []; }
  static async open(url) {
    const ws = new WebSocket(url);
    await new Promise((res, rej) => { ws.onopen = res; ws.onerror = rej; });
    const c = new CDP(ws);
    ws.onmessage = (e) => {
      const m = JSON.parse(e.data);
      if (m.id && c.pending.has(m.id)) {
        const { res, rej } = c.pending.get(m.id); c.pending.delete(m.id);
        m.error ? rej(new Error(JSON.stringify(m.error))) : res(m.result);
      } else if (m.method) c.handlers.forEach((h) => h(m));
    };
    return c;
  }
  send(method, params = {}, sessionId) {
    const id = ++this.id;
    this.ws.send(JSON.stringify({ id, method, params, ...(sessionId ? { sessionId } : {}) }));
    return new Promise((res, rej) => this.pending.set(id, { res, rej }));
  }
  once(method, sessionId) {
    return new Promise((res) => {
      const h = (m) => {
        if (m.method === method && (!sessionId || m.sessionId === sessionId)) {
          this.handlers = this.handlers.filter((x) => x !== h); res(m.params);
        }
      };
      this.handlers.push(h);
    });
  }
}

const style = "font-size:8px; font-family:-apple-system,Helvetica,sans-serif; " +
              "color:#8b8f98; width:100%; padding:0 14mm; -webkit-print-color-adjust:exact;";

try {
  const cdp = await CDP.open(await endpoint());
  const { targetId } = await cdp.send("Target.createTarget", { url: "about:blank" });
  const { sessionId } = await cdp.send("Target.attachToTarget", { targetId, flatten: true });

  await cdp.send("Page.enable", {}, sessionId);
  const loaded = cdp.once("Page.loadEventFired", sessionId);
  await cdp.send("Page.navigate", { url: `file://${src}` }, sessionId);
  await loaded;
  await cdp.send("Runtime.enable", {}, sessionId);
  // Poll for the page's own readiness flag rather than guessing a sleep: the
  // document sets window.__docReady once Mermaid has rendered AND every SVG
  // has been scaled to fit its page box.
  const deadline = Date.now() + Number(settleMs);
  for (;;) {
    const { result } = await cdp.send("Runtime.evaluate",
      { expression: "window.__docReady === true", returnByValue: true }, sessionId);
    if (result.value === true) break;
    if (Date.now() > deadline) { console.warn("warning: __docReady never set; printing anyway"); break; }
    await sleep(150);
  }
  await sleep(400);

  const { data } = await cdp.send("Page.printToPDF", {
    printBackground: true,
    paperWidth: 8.27, paperHeight: 11.69,            // A4
    marginTop: 0.62, marginBottom: 0.62, marginLeft: 0.0, marginRight: 0.0,
    displayHeaderFooter: true,
    headerTemplate:
      `<div style="${style} text-align:right; letter-spacing:.04em;">` +
      `MDRIIA 702CO0E012 &nbsp;&middot;&nbsp; GROUP 05 &nbsp;&middot;&nbsp; MPSTME GUARDIAN</div>`,
    footerTemplate:
      `<div style="${style} display:flex; justify-content:space-between;">` +
      `<span>${footerTitle}</span>` +
      `<span>Page <span class="pageNumber"></span> of <span class="totalPages"></span></span></div>`,
  }, sessionId);

  writeFileSync(out, Buffer.from(data, "base64"));
  console.log(`${out}  (${(Buffer.from(data, "base64").length / 1024).toFixed(0)} KB)`);
} finally {
  chrome.kill();
}
