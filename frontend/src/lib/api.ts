/**
 * API helper — wraps Supabase client for direct table access
 * and Edge Function invocations.
 *
 * Replaces the old fetch-based api module.
 */

import { supabase } from "@/lib/supabase";

export class ApiError extends Error {
  status: number;
  code: string;

  constructor(status: number, message: string, code: string = "UNKNOWN") {
    super(message);
    this.status = status;
    this.code = code;
    this.name = "ApiError";
  }
}

/** Invoke a Supabase Edge Function */
export async function invokeFunction<T>(
  name: string,
  body?: Record<string, unknown>,
  method: "POST" | "GET" | "PUT" | "DELETE" = "POST",
): Promise<T> {
  const { data, error } = await supabase.functions.invoke(name, {
    body: body ?? {},
    method,
  });
  if (error) {
    throw new ApiError(500, error.message ?? "Edge function error", "FUNCTION_ERROR");
  }
  return data as T;
}

/** Query a Supabase table with RLS-enforced access */
export async function queryTable<T>(
  table: string,
  options?: {
    select?: string;
    filters?: Array<{ column: string; op: string; value: unknown }>;
    order?: { column: string; ascending?: boolean };
    limit?: number;
    offset?: number;
    single?: boolean;
  },
): Promise<T> {
  let query = supabase.from(table).select(options?.select ?? "*", {
    count: options?.limit ? "exact" : undefined,
  });

  if (options?.filters) {
    for (const f of options.filters) {
      query = query.filter(f.column, f.op, f.value);
    }
  }

  if (options?.order) {
    query = query.order(options.order.column, {
      ascending: options.order.ascending ?? false,
    });
  }

  if (options?.limit) query = query.limit(options.limit);
  if (options?.offset) query = query.range(options.offset, options.offset + (options.limit ?? 20) - 1);

  if (options?.single) {
    const { data, error } = await query.single();
    if (error) throw new ApiError(error.code === "PGRST116" ? 404 : 500, error.message, error.code);
    return data as T;
  }

  const { data, error } = await query;
  if (error) throw new ApiError(500, error.message, error.code);
  return data as T;
}

/** Insert into a Supabase table */
export async function insertRow<T>(
  table: string,
  row: Record<string, unknown>,
): Promise<T> {
  const { data, error } = await supabase.from(table).insert(row).select().single();
  if (error) throw new ApiError(500, error.message, error.code);
  return data as T;
}

/** Update a row in a Supabase table */
export async function updateRow<T>(
  table: string,
  id: string,
  updates: Record<string, unknown>,
): Promise<T> {
  const { data, error } = await supabase.from(table).update(updates).eq("id", id).select().single();
  if (error) throw new ApiError(500, error.message, error.code);
  return data as T;
}

/** Delete a row from a Supabase table */
export async function deleteRow(table: string, id: string): Promise<void> {
  const { error } = await supabase.from(table).delete().eq("id", id);
  if (error) throw new ApiError(500, error.message, error.code);
}

// Legacy api object for backward compatibility during migration
export const api = {
  get: queryTable,
  invoke: invokeFunction,
  insert: insertRow,
  update: updateRow,
  delete: deleteRow,
};
