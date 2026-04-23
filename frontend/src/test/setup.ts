import "@testing-library/jest-dom";

// ---------------------------------------------------------------------------
// Global Supabase mock — prevents real HTTP calls and CI crashes
// ---------------------------------------------------------------------------

const mockChannel = {
  on: () => mockChannel,
  subscribe: () => mockChannel,
  unsubscribe: () => {},
};

const mockSupabase = {
  from: () => ({
    select: () => ({
      eq: () => ({ single: async () => ({ data: null, error: null }), data: [], error: null, count: 0 }),
      neq: () => ({ data: [], error: null }),
      order: () => ({
        range: () => ({ data: [], error: null, count: 0 }),
        limit: () => ({ data: [], error: null }),
        data: [],
        error: null,
        count: 0,
      }),
      gte: () => ({ lte: () => ({ data: [], error: null, count: 0 }), data: [], error: null }),
      lte: () => ({ data: [], error: null }),
      range: () => ({ data: [], error: null, count: 0 }),
      filter: () => ({ order: () => ({ range: () => ({ data: [], error: null, count: 0 }) }) }),
      single: async () => ({ data: null, error: null }),
      data: [],
      error: null,
      count: 0,
    }),
    insert: () => ({ select: () => ({ single: async () => ({ data: null, error: null }) }), error: null }),
    update: () => ({ eq: () => ({ select: () => ({ single: async () => ({ data: null, error: null }) }) }) }),
    delete: () => ({ eq: () => ({ error: null }), neq: () => ({ error: null }) }),
    upsert: () => ({ error: null }),
  }),
  auth: {
    getSession: async () => ({ data: { session: null }, error: null }),
    onAuthStateChange: () => ({ data: { subscription: { unsubscribe: () => {} } } }),
    signInWithPassword: async () => ({ data: null, error: null }),
    signInWithOtp: async () => ({ error: null }),
    verifyOtp: async () => ({ data: { user: null }, error: null }),
    updateUser: async () => ({ error: null }),
    resetPasswordForEmail: async () => ({ error: null }),
    signOut: async () => ({ error: null }),
  },
  functions: {
    invoke: async () => ({ data: null, error: null }),
  },
  channel: () => mockChannel,
};

vi.mock("@/lib/supabase", () => ({
  supabase: mockSupabase,
}));
