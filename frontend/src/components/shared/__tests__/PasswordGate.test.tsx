import { render, screen } from "@testing-library/react";

// Mock crypto.subtle for jsdom
Object.defineProperty(globalThis, "crypto", {
  value: {
    ...globalThis.crypto,
    subtle: {
      digest: async (_algo: string, data: ArrayBuffer) => {
        // Simple mock: return a fixed hash for the correct password
        const text = new TextDecoder().decode(data);
        if (text === "correctpassword") {
          // Return the expected hash bytes
          const hex = "3bd8037a8ed38a35825983767f94e6cf3b18c3deee1601daee71faec0d83565f";
          const bytes = new Uint8Array(hex.match(/.{2}/g)!.map((b) => parseInt(b, 16)));
          return bytes.buffer;
        }
        // Return a different hash for wrong passwords
        return new Uint8Array(32).buffer;
      },
    },
    randomUUID: () => "00000000-0000-0000-0000-000000000000",
  },
});

import { PasswordGate } from "../PasswordGate";

describe("PasswordGate", () => {
  beforeEach(() => {
    sessionStorage.clear();
  });

  it("renders the gate form when not unlocked", () => {
    render(
      <PasswordGate>
        <div>Protected Content</div>
      </PasswordGate>,
    );
    expect(screen.getByText("SignalForge AI")).toBeInTheDocument();
    expect(screen.getByText("This app is in private beta.")).toBeInTheDocument();
    expect(screen.getByLabelText("Access code")).toBeInTheDocument();
    expect(screen.queryByText("Protected Content")).not.toBeInTheDocument();
  });

  it("renders children when sessionStorage has unlock flag", () => {
    sessionStorage.setItem("signalforge-unlocked", "true");
    render(
      <PasswordGate>
        <div>Protected Content</div>
      </PasswordGate>,
    );
    expect(screen.getByText("Protected Content")).toBeInTheDocument();
  });

  it("renders submit button", () => {
    render(
      <PasswordGate>
        <div>Protected Content</div>
      </PasswordGate>,
    );
    expect(screen.getByText("Enter")).toBeInTheDocument();
  });
});
