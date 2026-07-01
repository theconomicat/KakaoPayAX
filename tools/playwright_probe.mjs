#!/usr/bin/env node
// Optional public-page probe. This does not bypass login, paywalls, or CAPTCHA.

const args = process.argv.slice(2);
const url = args[0];
let timeoutMs = 15000;

for (let index = 1; index < args.length; index += 1) {
  const arg = args[index];
  if (arg === "--timeout-ms" && args[index + 1]) {
    timeoutMs = Number(args[index + 1]);
    index += 1;
  } else if (arg.startsWith("--timeout-ms=")) {
    timeoutMs = Number(arg.split("=", 2)[1]);
  } else if (!arg.startsWith("--")) {
    timeoutMs = Number(arg);
  }
}

if (!Number.isFinite(timeoutMs) || timeoutMs <= 0) {
  timeoutMs = 15000;
}

if (!url) {
  console.error("usage: node tools/playwright_probe.mjs <public-url> [timeout-ms|--timeout-ms N]");
  process.exit(2);
}

let playwright;
try {
  playwright = await import("playwright");
} catch (error) {
  console.log(JSON.stringify({
    target: url,
    access_status: "blocked",
    retrieval_method: "playwright",
    title: "",
    text_length: 0,
    error: `optional dependency unavailable: ${error.message}`
  }, null, 2));
  process.exit(0);
}

const browser = await playwright.chromium.launch({ headless: true });
try {
  const context = await browser.newContext({
    viewport: { width: 1440, height: 1100 },
    locale: "ko-KR",
    userAgent: "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/146.0.0.0 Safari/537.36",
    extraHTTPHeaders: {
      "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
      "Cache-Control": "no-cache",
      "Pragma": "no-cache",
      "Upgrade-Insecure-Requests": "1"
    }
  });
  const page = await context.newPage();
  const networkCandidates = [];
  page.on("response", (response) => {
    const responseUrl = response.url();
    const headers = response.headers();
    const contentType = headers["content-type"] || "";
    const inspect = `${responseUrl} ${contentType}`.toLowerCase();
    if (
      inspect.includes("/api/") ||
      inspect.includes("graphql") ||
      inspect.includes(".json") ||
      inspect.includes("application/json") ||
      inspect.includes("rss") ||
      inspect.includes("xml")
    ) {
      networkCandidates.push({
        url: responseUrl,
        status_code: response.status(),
        method: response.request().method(),
        resource_type: response.request().resourceType(),
        content_type: contentType.slice(0, 120)
      });
    }
  });

  const mainResponse = await page.goto(url, { waitUntil: "domcontentloaded", timeout: timeoutMs });
  await page.waitForTimeout(Math.min(2500, Math.max(500, Math.floor(timeoutMs / 6))));
  const title = await page.title();
  const text = await page.locator("body").innerText({ timeout: 5000 }).catch(() => "");
  const lowered = text.toLowerCase();
  let accessStatus = "partial";
  if (
    lowered.includes("authentication required") ||
    lowered.includes("log in to continue") ||
    lowered.includes("login required") ||
    lowered.includes("paywall") ||
    lowered.includes("subscribe to continue") ||
    lowered.includes("subscription required")
  ) {
    accessStatus = "auth_required";
  } else if (
    lowered.includes("captcha") ||
    lowered.includes("verify you are human") ||
    lowered.includes("just a moment") ||
    lowered.includes("access denied") ||
    lowered.includes("attention required! | cloudflare") ||
    lowered.includes("cloudflare ray id") ||
    lowered.includes("datadome")
  ) {
    accessStatus = "blocked";
  } else if (text.length > 200) {
    accessStatus = "ok";
  }
  console.log(JSON.stringify({
    target: url,
    final_url: page.url(),
    access_status: accessStatus,
    status_code: mainResponse ? mainResponse.status() : null,
    retrieval_method: "playwright",
    title,
    excerpt: text.slice(0, 2000),
    text_length: text.length,
    network_candidates: networkCandidates.slice(0, 40),
    error: ""
  }, null, 2));
} catch (error) {
  console.log(JSON.stringify({
    target: url,
    access_status: "blocked",
    retrieval_method: "playwright",
    title: "",
    text_length: 0,
    error: error.message
  }, null, 2));
} finally {
  await browser.close();
}
