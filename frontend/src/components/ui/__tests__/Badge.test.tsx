import { render, screen } from "@testing-library/react";
import { Badge } from "../Badge";

describe("Badge", () => {
  it("renders children text", () => {
    render(<Badge>Active</Badge>);
    expect(screen.getByText("Active")).toBeInTheDocument();
  });

  it("applies neutral variant by default", () => {
    const { container } = render(<Badge>Default</Badge>);
    const span = container.querySelector("span");
    expect(span?.className).toContain("text-xs");
    expect(span?.className).toContain("font-medium");
  });

  it("renders with success variant", () => {
    render(<Badge variant="success">Win</Badge>);
    expect(screen.getByText("Win")).toBeInTheDocument();
  });

  it("renders with danger variant", () => {
    render(<Badge variant="danger">Loss</Badge>);
    expect(screen.getByText("Loss")).toBeInTheDocument();
  });

  it("renders with warning variant", () => {
    render(<Badge variant="warning">Caution</Badge>);
    expect(screen.getByText("Caution")).toBeInTheDocument();
  });

  it("renders with info variant", () => {
    render(<Badge variant="info">Info</Badge>);
    expect(screen.getByText("Info")).toBeInTheDocument();
  });

  it("accepts custom className", () => {
    const { container } = render(<Badge className="custom-class">Test</Badge>);
    const span = container.querySelector("span");
    expect(span?.className).toContain("custom-class");
  });
});
