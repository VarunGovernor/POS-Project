import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, test } from "vitest";

import DemoPage from "@/app/demo/page";

describe("client demo route", () => {
  test("demo landing renders", () => {
    render(<DemoPage />);
    expect(screen.getByText("HamTech Innovations")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "HamTech POS OS" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Start Demo" })).toBeInTheDocument();
  });

  test("Start Demo shows POS selection", async () => {
    render(<DemoPage />);
    await userEvent.click(screen.getByRole("button", { name: "Start Demo" }));
    expect(screen.getByRole("heading", { name: "Select POS System" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Hospital POS/ })).toBeInTheDocument();
    expect(screen.getAllByText("Coming Soon").length).toBeGreaterThan(0);
  });

  test("future POS cards do not open dashboards", async () => {
    render(<DemoPage />);
    await userEvent.click(screen.getByRole("button", { name: "Start Demo" }));
    await userEvent.click(screen.getByRole("button", { name: /Restaurant POS/ }));
    expect(screen.getByText("This POS vertical is planned for a future rollout.")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Select POS System" })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "New Order" })).not.toBeInTheDocument();
  });

  test("selecting Hospital POS opens dashboard", async () => {
    render(<DemoPage />);
    await userEvent.click(screen.getByRole("button", { name: "Start Demo" }));
    await userEvent.click(screen.getByRole("button", { name: /Hospital POS/ }));
    expect(screen.getByRole("heading", { name: "Hospital POS" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "OP Billing" })).toBeInTheDocument();
  });

  test("module buttons switch active panels", async () => {
    render(<DemoPage />);
    await userEvent.click(screen.getByRole("button", { name: "Start Demo" }));
    await userEvent.click(screen.getByRole("button", { name: /Hospital POS/ }));
    await userEvent.click(screen.getByRole("button", { name: "Reports" }));
    expect(screen.getByRole("heading", { name: "Reports" })).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Settings" }));
    expect(screen.getByRole("heading", { name: "Settings" })).toBeInTheDocument();
  });

  test("bill finalization demo shows success and receipt", async () => {
    render(<DemoPage />);
    await userEvent.click(screen.getByRole("button", { name: "Start Demo" }));
    await userEvent.click(screen.getByRole("button", { name: /Hospital POS/ }));
    await userEvent.click(screen.getByRole("button", { name: "Finalize Bill" }));
    await waitFor(() => expect(screen.getByText(/Bill finalized:/)).toBeInTheDocument());
    expect(screen.getByText("Receipt generated")).toBeInTheDocument();
  });

  test("sync retry demo updates status", async () => {
    render(<DemoPage />);
    await userEvent.click(screen.getByRole("button", { name: "Start Demo" }));
    await userEvent.click(screen.getByRole("button", { name: /Hospital POS/ }));
    await userEvent.click(screen.getByRole("button", { name: "Sync" }));
    await userEvent.click(screen.getByRole("button", { name: "Retry Sync" }));
    expect(screen.getByText("attempt recorded")).toBeInTheDocument();
  });

  test("printer demo creates visible job", async () => {
    render(<DemoPage />);
    await userEvent.click(screen.getByRole("button", { name: "Start Demo" }));
    await userEvent.click(screen.getByRole("button", { name: /Hospital POS/ }));
    await userEvent.click(screen.getByRole("button", { name: "Printer" }));
    await userEvent.click(screen.getByRole("button", { name: "Print Test Receipt" }));
    expect(screen.getByText("Test receipt printed")).toBeInTheDocument();
  });

  test("logout returns to POS selection", async () => {
    render(<DemoPage />);
    await userEvent.click(screen.getByRole("button", { name: "Start Demo" }));
    await userEvent.click(screen.getByRole("button", { name: /Hospital POS/ }));
    await userEvent.click(screen.getByRole("button", { name: "Logout" }));
    expect(screen.getByRole("heading", { name: "Select POS System" })).toBeInTheDocument();
  });
});
