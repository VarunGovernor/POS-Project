import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, test, vi } from "vitest";

import { ScreenNavActions } from "@/app/components/ScreenNavActions";

const push = vi.fn();
const back = vi.fn();

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push, back })
}));

describe("screen navigation actions", () => {
  beforeEach(() => {
    push.mockReset();
    back.mockReset();
  });

  test("back uses browser history when available", async () => {
    Object.defineProperty(window.history, "length", { configurable: true, value: 2 });
    render(<ScreenNavActions />);

    await userEvent.click(screen.getByRole("button", { name: "← Back" }));

    expect(back).toHaveBeenCalled();
    expect(push).not.toHaveBeenCalled();
  });

  test("back falls back to dashboard without history", async () => {
    Object.defineProperty(window.history, "length", { configurable: true, value: 1 });
    render(<ScreenNavActions />);

    await userEvent.click(screen.getByRole("button", { name: "← Back" }));

    expect(back).not.toHaveBeenCalled();
    expect(push).toHaveBeenCalledWith("/dashboard");
  });

  test("dashboard button routes directly to dashboard", async () => {
    render(<ScreenNavActions />);

    await userEvent.click(screen.getByRole("button", { name: "Dashboard" }));

    expect(push).toHaveBeenCalledWith("/dashboard");
  });
});
