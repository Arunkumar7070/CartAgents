import { expect, type Page, test } from "@playwright/test";

const API = "http://api.test";
const SESSION = "s".repeat(43);

const probook = {
  id: "probook-15",
  name: "ProBook 15",
  brand: "TechCorp",
  category: "laptops",
  price_cents: 129999,
  stock: 5,
  specs: '15.6" display, 16GB RAM, 512GB SSD, Intel i7',
  description: "Business laptop with all-day battery life.",
};

const cart = {
  type: "cart",
  lines: [
    {
      product_id: "probook-15",
      name: "ProBook 15",
      category: "laptops",
      quantity: 1,
      unit_price_cents: 129999,
      line_total_cents: 129999,
    },
  ],
  subtotal_cents: 129999,
  shipping_cents: 0,
  tax_cents: 10400,
  total_cents: 140399,
  cart_hash: "9f2c4e1ab37d55e0c8a1",
};

function sse(events: [string, unknown][]): string {
  return events.map(([name, data]) => `event: ${name}\ndata: ${JSON.stringify(data)}\n\n`).join("");
}

function done(blocks: unknown[], pending = false) {
  return {
    session_id: SESSION,
    skill: "qa",
    blocks,
    pending_confirmation: pending,
    confirm_token: pending ? "tok" : null,
  };
}

async function mockApi(page: Page) {
  let orders: unknown[] = [];
  await page.route(`${API}/health`, (route) => route.fulfill({ json: { status: "ok" } }));
  await page.route(`${API}/orders`, (route) => route.fulfill({ json: orders }));
  await page.route(`${API}/chat/stream`, async (route) => {
    const body = route.request().postDataJSON() as { message: string; confirm_token: string | null };
    let events: [string, unknown][];
    if (body.confirm_token === "tok") {
      const order = {
        type: "order",
        order_id: "ORD-1000",
        status: "processing",
        eta: "Ships within 2 minutes",
        lines: [{ ...cart.lines[0] }],
        total_cents: 140399,
        cart_hash: cart.cart_hash,
        created_at: "2026-10-15T09:30:00+00:00",
      };
      orders = [order];
      events = [["done", done([{ type: "text", markdown: "Order **ORD-1000** is placed." }, order])]];
    } else if (body.message.startsWith("I'd like to buy")) {
      events = [
        ["step", { node: "prepare_order", status: "start" }],
        [
          "done",
          done(
            [
              { type: "text", markdown: "Here's your cart. The total of **$1,403.99** includes shipping and tax." },
              cart,
              { type: "confirmation", action: "order", prompt: "Place this order?" },
            ],
            true,
          ),
        ],
      ];
    } else {
      events = [
        ["session", { session_id: SESSION }],
        ["step", { node: "search_products", status: "start" }],
        ["delta", { text: "The ProBook 15 is " }],
        ["delta", { text: "built for travel." }],
        [
          "done",
          done([
            { type: "text", markdown: "The **ProBook 15** is built for professionals who travel." },
            { type: "product_cards", products: [probook] },
            { type: "filters", applied: [{ field: "category", value: "laptops" }] },
            { type: "citations", items: [{ source: "catalog", ref: "probook-15", quote: "ProBook 15 — $1,299.99" }] },
          ]),
        ],
      ];
    }
    await route.fulfill({ headers: { "content-type": "text/event-stream" }, body: sse(events) });
  });
}

test("browse, order and confirm a laptop end to end", async ({ page }) => {
  await mockApi(page);
  await page.goto("/");

  await page.getByLabel("Message CartAgent").fill("a laptop for travel");
  await page.getByRole("button", { name: "Send" }).click();
  await expect(page.getByRole("heading", { name: "ProBook 15" })).toBeVisible();
  await expect(page.getByText("$1,299.99").first()).toBeVisible();
  await page.screenshot({ path: "e2e/screens/browse.png", fullPage: true });

  await page.getByRole("button", { name: "Order" }).click();
  await expect(page.getByRole("button", { name: "Place order" })).toBeVisible();
  await expect(page.getByLabel("Counter").getByText("$1,403.99")).toBeVisible();
  await page.screenshot({ path: "e2e/screens/cart.png", fullPage: true });

  await page.getByRole("button", { name: "Place order" }).click();
  await expect(page.getByRole("article", { name: /Order ORD-1000/ })).toBeVisible();
  await expect(page.getByLabel("Counter").getByRole("button", { name: "ORD-1000" })).toBeVisible();
  await page.waitForTimeout(500);
  await page.screenshot({ path: "e2e/screens/order.png", fullPage: true });
});

test("fits a phone screen in dark mode without horizontal scrolling", async ({ page }) => {
  await mockApi(page);
  await page.setViewportSize({ width: 375, height: 812 });
  await page.emulateMedia({ colorScheme: "dark" });
  await page.goto("/");
  await page.getByRole("button", { name: /Something light to carry/ }).click();
  await expect(page.getByRole("heading", { name: "ProBook 15" })).toBeVisible();
  await page.waitForTimeout(400);
  const overflow = await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
  expect(overflow).toBeLessThanOrEqual(0);
  await page.screenshot({ path: "e2e/screens/phone-dark.png", fullPage: true });
});
