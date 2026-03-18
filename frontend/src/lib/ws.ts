/**
 * Realtime wrapper — replaces custom WebSocket manager with Supabase Realtime.
 */

import { supabase } from "@/lib/supabase";
import type { RealtimeChannel } from "@supabase/supabase-js";

const channels = new Map<string, RealtimeChannel>();

type Handler = (payload: unknown) => void;

/** Subscribe to postgres_changes on a table (INSERT, UPDATE, DELETE, or *) */
export function subscribeTable(
  channelName: string,
  table: string,
  event: "INSERT" | "UPDATE" | "DELETE" | "*",
  userId: string,
  handler: Handler,
): () => void {
  const existing = channels.get(channelName);
  if (existing) existing.unsubscribe();

  const channel = supabase
    .channel(channelName)
    .on(
      "postgres_changes",
      { event, schema: "public", table, filter: `user_id=eq.${userId}` },
      (payload) => handler(payload.new ?? payload),
    )
    .subscribe();

  channels.set(channelName, channel);

  return () => {
    channel.unsubscribe();
    channels.delete(channelName);
  };
}

/** Subscribe to broadcast events (e.g., price updates from engine-cron) */
export function subscribeBroadcast(
  channelName: string,
  eventName: string,
  handler: Handler,
): () => void {
  const existing = channels.get(channelName);
  if (existing) existing.unsubscribe();

  const channel = supabase
    .channel(channelName)
    .on("broadcast", { event: eventName }, (payload) => handler(payload.payload))
    .subscribe();

  channels.set(channelName, channel);

  return () => {
    channel.unsubscribe();
    channels.delete(channelName);
  };
}

/** Disconnect all channels */
export function disconnectAll(): void {
  for (const channel of channels.values()) {
    channel.unsubscribe();
  }
  channels.clear();
}
