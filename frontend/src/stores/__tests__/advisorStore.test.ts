import { useAdvisorStore } from "../advisorStore";

// Mock the api module
vi.mock("@/lib/api", () => ({
  invokeFunction: vi.fn().mockResolvedValue({
    pairs_scanned: 50,
    pairs_scored: 10,
    results: [],
    market_profile: null,
  }),
}));

describe("advisorStore", () => {
  beforeEach(() => {
    useAdvisorStore.setState({ scanHistory: [], activeScanId: null });
  });

  it("starts with empty scan history", () => {
    const state = useAdvisorStore.getState();
    expect(state.scanHistory).toHaveLength(0);
    expect(state.activeScanId).toBeNull();
  });

  it("deleteScan removes entry from history", () => {
    useAdvisorStore.setState({
      scanHistory: [
        {
          id: "scan-1",
          timestamp: Date.now(),
          status: "completed",
          pairs_scanned: 10,
          pairs_scored: 5,
          results: [],
          market_profile: null,
        },
      ],
      activeScanId: null,
    });

    useAdvisorStore.getState().deleteScan("scan-1");
    expect(useAdvisorStore.getState().scanHistory).toHaveLength(0);
  });

  it("clearHistory empties all scans", () => {
    useAdvisorStore.setState({
      scanHistory: [
        {
          id: "scan-1",
          timestamp: Date.now(),
          status: "completed",
          pairs_scanned: 10,
          pairs_scored: 5,
          results: [],
          market_profile: null,
        },
        {
          id: "scan-2",
          timestamp: Date.now(),
          status: "completed",
          pairs_scanned: 20,
          pairs_scored: 10,
          results: [],
          market_profile: null,
        },
      ],
      activeScanId: null,
    });

    useAdvisorStore.getState().clearHistory();
    expect(useAdvisorStore.getState().scanHistory).toHaveLength(0);
    expect(useAdvisorStore.getState().activeScanId).toBeNull();
  });

  it("setPlan attaches plan to scan", () => {
    useAdvisorStore.setState({
      scanHistory: [
        {
          id: "scan-1",
          timestamp: Date.now(),
          status: "completed",
          pairs_scanned: 10,
          pairs_scored: 5,
          results: [],
          market_profile: null,
        },
      ],
      activeScanId: null,
    });

    const plan = {
      summary: "Test plan",
      selected_cryptos: [],
      strategy_config: {},
      reasoning: "test",
      expected_behavior: "test",
      warnings: [],
    };

    useAdvisorStore.getState().setPlan("scan-1", plan, 1000);
    const scan = useAdvisorStore.getState().scanHistory[0];
    expect(scan.plan).toEqual(plan);
    expect(scan.planAmount).toBe(1000);
  });

  it("setDeployed attaches deployment info", () => {
    useAdvisorStore.setState({
      scanHistory: [
        {
          id: "scan-1",
          timestamp: Date.now(),
          status: "completed",
          pairs_scanned: 10,
          pairs_scored: 5,
          results: [],
          market_profile: null,
        },
      ],
      activeScanId: null,
    });

    useAdvisorStore.getState().setDeployed("scan-1", "strat-123", "Deployed successfully");
    const scan = useAdvisorStore.getState().scanHistory[0];
    expect(scan.deployedStrategyId).toBe("strat-123");
    expect(scan.deployedMessage).toBe("Deployed successfully");
  });

  it("clearPlan removes plan and deployment info", () => {
    useAdvisorStore.setState({
      scanHistory: [
        {
          id: "scan-1",
          timestamp: Date.now(),
          status: "completed",
          pairs_scanned: 10,
          pairs_scored: 5,
          results: [],
          market_profile: null,
          plan: { summary: "x", selected_cryptos: [], strategy_config: {}, reasoning: "", expected_behavior: "", warnings: [] },
          planAmount: 500,
          deployedStrategyId: "strat-1",
          deployedMessage: "done",
        },
      ],
      activeScanId: null,
    });

    useAdvisorStore.getState().clearPlan("scan-1");
    const scan = useAdvisorStore.getState().scanHistory[0];
    expect(scan.plan).toBeUndefined();
    expect(scan.planAmount).toBeUndefined();
    expect(scan.deployedStrategyId).toBeUndefined();
  });
});
