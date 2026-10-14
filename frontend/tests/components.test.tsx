import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import axe from "axe-core";
import { describe, expect, it, vi } from "vitest";
import type { CartBlock } from "../src/api/types";
import type { Entry } from "../src/hooks/useChat";
import { ConfirmBar } from "../src/components/ConfirmBar";
import { Markdown } from "../src/components/Markdown";
import { CartReceipt } from "../src/components/Receipt";
import { Tape } from "../src/components/Tape";

const cart: CartBlock = {
  type: "cart",
  lines: [
    {
      product_id: "probook-15",
      name: "ProBook 15",
      category: "laptops",
      quantity: 2,
      unit_price_cents: 129999,
      line_total_cents: 259998,
    },
  ],
  subtotal_cents: 259998,
  shipping_cents: 0,
  tax_cents: 20800,
  total_cents: 280798,
  cart_hash: "a1b2c3d4e5f6a7b8c9d0",
};

describe("CartReceipt", () => {
  it("prints every amount from the cart data, with free shipping spelled out", () => {
    render(<CartReceipt cart={cart} />);
    expect(screen.getByText("2 x ProBook 15")).toBeInTheDocument();
    expect(screen.getByText("$2,807.98")).toBeInTheDocument();
    expect(screen.getByText("FREE")).toBeInTheDocument();
    expect(screen.getByText("$208.00")).toBeInTheDocument();
  });
});

describe("ConfirmBar", () => {
  it("can be confirmed with the keyboard alone", async () => {
    const onAnswer = vi.fn();
    render(<ConfirmBar block={{ type: "confirmation", action: "order", prompt: "Place this order?" }} active onAnswer={onAnswer} />);
    await userEvent.tab();
    expect(screen.getByRole("button", { name: "Place order" })).toHaveFocus();
    await userEvent.keyboard("{Enter}");
    expect(onAnswer).toHaveBeenCalledWith("yes");
  });

  it("shows no buttons once the question is answered", () => {
    render(
      <ConfirmBar block={{ type: "confirmation", action: "order", prompt: "Place this order?" }} active={false} onAnswer={vi.fn()} />,
    );
    expect(screen.queryByRole("button")).not.toBeInTheDocument();
  });
});

describe("Markdown", () => {
  it("does not render raw HTML, images or non-https links from model output", () => {
    const { container } = render(
      <Markdown>{'<img src=x onerror="alert(1)"> ![pixel](https://evil.example/p.png) [click](javascript:alert(1))'}</Markdown>,
    );
    expect(container.querySelector("img")).toBeNull();
    expect(container.querySelector("a")).toBeNull();
    expect(screen.getByText("click")).toBeInTheDocument();
  });
});

describe("Tape", () => {
  const entries: Entry[] = [
    { id: 1, role: "user", text: "two ProBooks please" },
    {
      id: 2,
      role: "agent",
      blocks: [
        { type: "text", markdown: "Here's your cart." },
        cart,
        { type: "confirmation", action: "order", prompt: "Place this order?" },
      ],
    },
  ];

  it("announces new entries through a polite live region", () => {
    render(<Tape entries={entries} streaming={null} pending={{ token: "t", action: "order" }} comparing={[]} onSend={vi.fn()} onToggleCompare={vi.fn()} />);
    const log = screen.getByRole("log");
    expect(log).toHaveAttribute("aria-live", "polite");
    expect(log).toHaveTextContent("two ProBooks please");
  });

  it("has no detectable accessibility violations", async () => {
    const { container } = render(
      <Tape entries={entries} streaming={null} pending={{ token: "t", action: "order" }} comparing={[]} onSend={vi.fn()} onToggleCompare={vi.fn()} />,
    );
    const results = await axe.run(container, { rules: { "color-contrast": { enabled: false } } });
    expect(results.violations.map((v) => v.id)).toEqual([]);
  });
});
