import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { ApiError, apiFetch, registerUnauthorizedHandler } from "./client";

describe("apiFetch", () => {
  const originalFetch = globalThis.fetch;

  beforeEach(() => {
    localStorage.clear();
    registerUnauthorizedHandler(null);
  });

  afterEach(() => {
    globalThis.fetch = originalFetch;
    vi.restoreAllMocks();
  });

  it("injects Authorization Bearer header from localStorage", async () => {
    localStorage.setItem("authToken", "test-jwt-token");
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ ok: true }), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      })
    );
    globalThis.fetch = fetchMock;

    const result = await apiFetch<{ ok: boolean }>("/users/123");

    expect(result).toEqual({ ok: true });
    expect(fetchMock).toHaveBeenCalledTimes(1);
    const [, init] = fetchMock.mock.calls[0]!;
    const headers = new Headers((init as RequestInit).headers);
    expect(headers.get("Authorization")).toBe("Bearer test-jwt-token");
  });

  it("returns undefined on 204 No Content without parsing JSON", async () => {
    const fetchMock = vi.fn().mockResolvedValue(new Response(null, { status: 204 }));
    globalThis.fetch = fetchMock;

    const result = await apiFetch<void>("/screenshots/p1", { method: "DELETE" });
    expect(result).toBeUndefined();
  });

  it("throws ApiError with fallback status message on non-JSON error responses", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response("<html>502 Bad Gateway</html>", { status: 502 })
    );
    globalThis.fetch = fetchMock;

    await expect(apiFetch("/users/123")).rejects.toMatchObject({
      name: "ApiError",
      status: 502,
      message: "HTTP error! status: 502",
    });
  });

  it("invokes unauthorized handler on 401 unless skipped", async () => {
    const onUnauthorized = vi.fn();
    registerUnauthorizedHandler(onUnauthorized);
    const fetchMock = vi.fn().mockImplementation(() =>
      Promise.resolve(
        new Response(JSON.stringify({ detail: "Token expired" }), {
          status: 401,
          headers: { "Content-Type": "application/json" },
        })
      )
    );
    globalThis.fetch = fetchMock;

    await expect(apiFetch("/users/123")).rejects.toBeInstanceOf(ApiError);
    expect(onUnauthorized).toHaveBeenCalledTimes(1);

    await expect(
      apiFetch("/token", { method: "POST", skipUnauthorizedHandler: true })
    ).rejects.toBeInstanceOf(ApiError);
    expect(onUnauthorized).toHaveBeenCalledTimes(1);
  });
});
