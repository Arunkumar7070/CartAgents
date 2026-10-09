import { describe, expect, it } from "vitest";
import { createSseParser } from "../src/api/stream";
import type { StreamEvent } from "../src/api/types";

describe("createSseParser", () => {
  it("reassembles events split across network chunks", () => {
    const events: StreamEvent[] = [];
    const parse = createSseParser((event) => events.push(event));

    parse('event: step\ndata: {"node": "route_sk');
    parse('ill", "status": "start"}\n\nevent: delta\ndata: {"text": "Hel');
    parse('lo"}\n\n');

    expect(events).toEqual([
      { event: "step", data: { node: "route_skill", status: "start" } },
      { event: "delta", data: { text: "Hello" } },
    ]);
  });

  it("accepts CRLF line endings", () => {
    const events: StreamEvent[] = [];
    createSseParser((event) => events.push(event))('event: session\r\ndata: {"session_id": "abc"}\r\n\r\n');
    expect(events).toEqual([{ event: "session", data: { session_id: "abc" } }]);
  });
});
