import { render, screen } from "@testing-library/react";
import { DataTable, type Column } from "../DataTable";

interface TestRow {
  id: string;
  name: string;
  value: number;
  [key: string]: unknown;
}

const columns: Column<TestRow>[] = [
  { key: "name", header: "Name" },
  { key: "value", header: "Value", align: "right" },
];

const data: TestRow[] = [
  { id: "1", name: "Alpha", value: 100 },
  { id: "2", name: "Beta", value: 200 },
];

describe("DataTable", () => {
  it("renders column headers", () => {
    render(<DataTable data={data} columns={columns} />);
    expect(screen.getByText("Name")).toBeInTheDocument();
    expect(screen.getByText("Value")).toBeInTheDocument();
  });

  it("renders row data", () => {
    render(<DataTable data={data} columns={columns} />);
    expect(screen.getByText("Alpha")).toBeInTheDocument();
    expect(screen.getByText("200")).toBeInTheDocument();
  });

  it("renders empty message when no data", () => {
    render(<DataTable data={[]} columns={columns} />);
    expect(screen.getByText("No data available")).toBeInTheDocument();
  });

  it("renders custom empty message", () => {
    render(<DataTable data={[]} columns={columns} emptyMessage="Nothing here" />);
    expect(screen.getByText("Nothing here")).toBeInTheDocument();
  });

  it("renders loading skeleton rows", () => {
    const { container } = render(<DataTable data={[]} columns={columns} loading />);
    const skeletons = container.querySelectorAll(".animate-pulse");
    expect(skeletons.length).toBeGreaterThan(0);
  });
});
