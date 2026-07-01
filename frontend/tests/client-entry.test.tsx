import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, test, vi } from "vitest";

import HomePage from "@/app/page";

const push = vi.fn();

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push })
}));

describe("client entry route", () => {
  beforeEach(() => {
    push.mockReset();
  });

  test("root renders client-facing POS selection", () => {
    render(<HomePage />);

    expect(screen.getByText("HamTech Innovations")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "HamTech POS OS" })).toBeInTheDocument();
    expect(screen.getByText("Select POS System")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Hospital POS/ })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Liquor Store POS/ })).toBeInTheDocument();
    expect(screen.getAllByText("Ready")).toHaveLength(2);
    expect(screen.getAllByText("Coming Soon").length).toBeGreaterThan(0);
    expect(screen.queryByRole("button", { name: /Pharmacy POS/ })).not.toBeInTheDocument();
    expect(screen.queryByRole("link", { name: /startup/i })).not.toBeInTheDocument();
  });

  test("Hospital POS navigates to POS-aware login", async () => {
    render(<HomePage />);

    await userEvent.click(screen.getByRole("button", { name: /Hospital POS/ }));

    expect(push).toHaveBeenCalledWith("/login?pos=hospital");
  });

  test("Liquor Store POS navigates to POS-aware login", async () => {
    render(<HomePage />);

    await userEvent.click(screen.getByRole("button", { name: /Liquor Store POS/ }));

    expect(push).toHaveBeenCalledWith("/login?pos=liquor");
  });

  test("future POS cards show toast and do not navigate", async () => {
    render(<HomePage />);

    await userEvent.click(screen.getByRole("button", { name: /Restaurant POS/ }));

    expect(screen.getByText("This POS vertical is planned for a future rollout.")).toBeInTheDocument();
    expect(push).not.toHaveBeenCalled();
  });
});
