import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { api, ApiError, LOCKED_EVENT, messageFor } from "./api";

const reply = (status: number, body: unknown) =>
  vi.fn().mockResolvedValue(new Response(body === undefined ? null : JSON.stringify(body), { status }));

beforeEach(() => {
  vi.stubGlobal("window", new EventTarget());
});
afterEach(() => {
  vi.unstubAllGlobals();
});

describe("api errors", () => {
  it("turns FastAPI validation lists into one readable line", async () => {
    vi.stubGlobal("fetch", reply(422, { detail: [{ msg: "Field required" }, { msg: "Not a PDF" }] }));
    await expect(api.search("jd")).rejects.toMatchObject({ status: 422, message: "Field required; Not a PDF" });
  });

  it("passes plain string details through", async () => {
    vi.stubGlobal("fetch", reply(404, { detail: "Candidate not found" }));
    await expect(api.candidate("x")).rejects.toMatchObject({ status: 404, message: "Candidate not found" });
  });

  it("explains a network failure", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new TypeError("Failed to fetch")));
    await expect(api.health()).rejects.toMatchObject({ status: 0 });
  });

  it("asks for the access code again on 401", async () => {
    vi.stubGlobal("fetch", reply(401, { detail: "Access code required" }));
    const locked = vi.fn();
    window.addEventListener(LOCKED_EVENT, locked);
    await expect(api.resumes()).rejects.toBeInstanceOf(ApiError);
    expect(locked).toHaveBeenCalledOnce();
  });

  it("returns undefined for 204", async () => {
    vi.stubGlobal("fetch", reply(204, undefined));
    await expect(api.deleteResume("r1")).resolves.toBeUndefined();
  });
});

describe("messageFor", () => {
  it("softens 503s", () => {
    expect(messageFor(new ApiError(503, "Groq timeout"))).toBe("The AI service is busy right now. Try again in a moment.");
  });
  it("falls back for unknown errors", () => {
    expect(messageFor(new Error("boom"))).toBe("Something went wrong.");
  });
});
