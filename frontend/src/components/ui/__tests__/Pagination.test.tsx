import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { Pagination } from "../Pagination";

describe("Pagination", () => {
  it("renders showing range text", () => {
    render(<Pagination total={100} limit={20} offset={0} onChange={() => {}} />);
    expect(screen.getByText("1")).toBeInTheDocument();
    expect(screen.getByText("20")).toBeInTheDocument();
    expect(screen.getByText("100")).toBeInTheDocument();
  });

  it("disables previous button on first page", () => {
    render(<Pagination total={100} limit={20} offset={0} onChange={() => {}} />);
    const buttons = screen.getAllByRole("button");
    expect(buttons[0]).toBeDisabled();
  });

  it("disables next button on last page", () => {
    render(<Pagination total={100} limit={20} offset={80} onChange={() => {}} />);
    const buttons = screen.getAllByRole("button");
    expect(buttons[1]).toBeDisabled();
  });

  it("calls onChange with next offset on next click", async () => {
    const user = userEvent.setup();
    const onChange = vi.fn();
    render(<Pagination total={100} limit={20} offset={0} onChange={onChange} />);
    const buttons = screen.getAllByRole("button");
    await user.click(buttons[1]); // Next button
    expect(onChange).toHaveBeenCalledWith(20);
  });

  it("calls onChange with previous offset on prev click", async () => {
    const user = userEvent.setup();
    const onChange = vi.fn();
    render(<Pagination total={100} limit={20} offset={40} onChange={onChange} />);
    const buttons = screen.getAllByRole("button");
    await user.click(buttons[0]); // Prev button
    expect(onChange).toHaveBeenCalledWith(20);
  });

  it("shows 0 for empty result set", () => {
    render(<Pagination total={0} limit={20} offset={0} onChange={() => {}} />);
    // from (0), to (0), total (0) — three zeros
    expect(screen.getAllByText("0")).toHaveLength(3);
  });
});
