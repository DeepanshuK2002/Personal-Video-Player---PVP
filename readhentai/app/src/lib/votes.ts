"use client";

import { useEffect, useState } from "react";

export type VoteType = "like" | "dislike";
export type Votes = { likes: number; dislikes: number; mine: VoteType | null };

const KEY = "readhentai-votes";
const EVENT = "votes-change";

/** Deterministic seed so each file starts with a realistic vote spread. */
function seed(slug: string): Votes {
  let h = 2166136261;
  for (let i = 0; i < slug.length; i++) {
    h ^= slug.charCodeAt(i);
    h = Math.imul(h, 16777619);
  }
  const likes = 40 + (h % 160);
  const dislikes = 10 + ((h >>> 5) % 40);
  return { likes, dislikes, mine: null };
}

function getAll(): Record<string, Votes> {
  if (typeof window === "undefined") return {};
  try {
    return JSON.parse(localStorage.getItem(KEY) || "{}");
  } catch {
    return {};
  }
}

export function getVotes(slug: string): Votes {
  return getAll()[slug] ?? seed(slug);
}

/** Rating = 1 + 4 × (Likes / (Likes + Dislikes)), clamped to 1..5. */
export function getRating(slug: string): number {
  const v = getVotes(slug);
  const total = v.likes + v.dislikes;
  if (total === 0) return 1;
  return Math.min(5, Math.max(1, 1 + 4 * (v.likes / total)));
}

/**
 * Cast a vote. Clicking the active vote removes it; clicking the opposite
 * vote switches it. Returns the updated tallies.
 */
export function vote(slug: string, type: VoteType): Votes {
  const all = getAll();
  const cur = all[slug] ?? seed(slug);
  const next: Votes = { ...cur };

  if (cur.mine === type) {
    if (type === "like") next.likes = Math.max(0, next.likes - 1);
    else next.dislikes = Math.max(0, next.dislikes - 1);
    next.mine = null;
  } else {
    if (cur.mine === "like") next.likes = Math.max(0, next.likes - 1);
    if (cur.mine === "dislike") next.dislikes = Math.max(0, next.dislikes - 1);
    if (type === "like") next.likes += 1;
    else next.dislikes += 1;
    next.mine = type;
  }

  all[slug] = next;
  localStorage.setItem(KEY, JSON.stringify(all));
  window.dispatchEvent(new CustomEvent(EVENT));
  return next;
}

/** Subscribe to vote changes; returns tallies + current rating. */
export function useVotes(slug: string) {
  const [votes, setVotes] = useState<Votes>(() => getVotes(slug));

  useEffect(() => {
    const sync = () => setVotes(getVotes(slug));
    sync();
    window.addEventListener(EVENT, sync);
    return () => window.removeEventListener(EVENT, sync);
  }, [slug]);

  const total = votes.likes + votes.dislikes;
  const rating = total === 0 ? 1 : Math.min(5, Math.max(1, 1 + 4 * (votes.likes / total)));

  return { votes, rating, vote: (t: VoteType) => vote(slug, t) };
}
