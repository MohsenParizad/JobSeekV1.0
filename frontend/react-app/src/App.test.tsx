import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import App from "./App";

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), { status, headers: { "Content-Type": "application/json" } });
}

beforeEach(() => {
  localStorage.clear();
});

afterEach(() => {
  vi.restoreAllMocks();
});

describe("App", () => {
  it("shows a name prompt before any candidate is bootstrapped", () => {
    render(<App />);
    expect(screen.getByText(/enter your name above to get started/i)).toBeInTheDocument();
  });

  it("bootstraps a candidate and reveals the tabs on Start", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn((url: string) => {
        if (url.includes("/candidates") && !url.includes("/evidence")) {
          return Promise.resolve(jsonResponse({ id: "c1", name: "Ada Example", email: null }));
        }
        if (url.includes("/evidence")) {
          return Promise.resolve(jsonResponse([]));
        }
        return Promise.resolve(jsonResponse([]));
      }),
    );

    const user = userEvent.setup();
    render(<App />);

    await user.type(screen.getByLabelText(/your name/i), "Ada Example");
    await user.click(screen.getByRole("button", { name: /start/i }));

    await waitFor(() => expect(screen.getByRole("button", { name: "Documents" })).toBeInTheDocument());
    expect(screen.getByRole("button", { name: "Job Analysis" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Generate Application" })).toBeInTheDocument();
    expect(screen.getByText(/upload a document/i)).toBeInTheDocument();
  });
});
