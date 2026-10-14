import { useSyncExternalStore } from "react";

export type ModeCode = "classic" | "memory" | "chaos";
export const MODES = {
  classic: {
    name: "Classic",
    blurb: "A standard timed typing test.",
    durations: [60, 180, 300],
    durationLabel: "Test duration",
  },
  memory: {
    name: "Memory Rush",
    blurb: "Memorize, then type it blind. Survive the rounds.",
    durations: [15, 30, 60],
    durationLabel: "Memorize for",
  },
  chaos: {
    name: "Key Chaos",
    blurb: "Memorize, then type through scrambled keys.",
    durations: [15, 30, 60],
    durationLabel: "Memorize for",
  },
} satisfies Record<
  ModeCode,
  { name: string; blurb: string; durations: number[]; durationLabel: string }
>;
export type Difficulty = "easy" | "medium" | "hard";
export interface User {
  id: string;
  username: string;
  createdAt: string;
}
export interface Challenge {
  id: string;
  category: string;
  difficulty: Difficulty;
  text: string;
}
export interface RoundRecord {
  round: number;
  challengeId: string;
  accuracy: number;
  passed: boolean;
}
export interface Result {
  id: string;
  userId: string;
  mode: ModeCode;
  wpm: number;
  accuracy: number;
  errors: number;
  score: number;
  duration: number;
  rounds: number;
  roundDetails?: RoundRecord[];
  createdAt: string;
}
export interface Achievement {
  code: string;
  name: string;
  description: string;
  test: (r: Result) => boolean;
}
export interface UserAchievement {
  userId: string;
  code: string;
  resultId: string | null;
  unlockedAt: string;
}
interface DB {
  users: User[];
  challenges: Challenge[];
  results: Result[];
  userAchievements: UserAchievement[];
  currentUserId: string | null;
}

export function calcWpm(chars: number, seconds: number) {
  return seconds <= 0 ? 0 : Math.round((chars / 5 / (seconds / 60)) * 10) / 10;
}
export function calcAccuracy(correct: number, typed: number) {
  return typed <= 0 ? 0 : Math.round((correct / typed) * 1000) / 10;
}
export function calcScore(mode: ModeCode, wpm: number, accuracy: number, rounds: number) {
  return mode === "memory" ? rounds : Math.round(((wpm * accuracy) / 100) * 10) / 10;
}
export function compare(target: string, typed: string) {
  let correct = 0;
  for (let i = 0; i < typed.length; i++) if (typed[i] === target[i]) correct++;
  return { correct, incorrect: typed.length - correct };
}
export function validateUsername(name: string, users: User[], ignoreId?: string) {
  const value = name.trim();
  if (!value) return "Please enter a username.";
  if (value.length < 4) return "Username is too short. Use at least 4 characters.";
  if (value.length > 20) return "Username is too long. Use 20 characters or fewer.";
  if (!/^[A-Za-z0-9_.-]+$/.test(value))
    return "Use only letters, numbers, underscore (_), dot (.) or hyphen (-). No spaces.";
  if (
    users.some(
      (user) => user.id !== ignoreId && user.username.toLowerCase() === value.toLowerCase(),
    )
  )
    return `The username "${value}" is already taken. Please choose another one.`;
  return null;
}

export const CHAOS_SCRAMBLES = { easy: 5, medium: 8, hard: 10 };
export function scrambleCountFor(difficulty: Difficulty | "any") {
  if (difficulty !== "any") return CHAOS_SCRAMBLES[difficulty];
  const choice =
    (["easy", "medium", "hard"] as Difficulty[])[Math.floor(Math.random() * 3)] ?? "easy";
  return CHAOS_SCRAMBLES[choice];
}
export function makeKeyMap(count: number) {
  const letters = "abcdefghijklmnopqrstuvwxyz".split("");
  const chosen = [...letters]
    .sort(() => Math.random() - 0.5)
    .slice(0, Math.max(2, Math.min(count, 25)));
  let shuffled: string[];
  do {
    shuffled = [...chosen];
    for (let index = shuffled.length - 1; index > 0; index--) {
      const swapIndex = Math.floor(Math.random() * (index + 1));
      [shuffled[index], shuffled[swapIndex]] = [shuffled[swapIndex]!, shuffled[index]!];
    }
  } while (shuffled.some((letter, index) => letter === chosen[index]));
  const mapping = Object.fromEntries(letters.map((letter) => [letter, letter]));
  chosen.forEach((letter, index) => {
    mapping[letter] = shuffled[index]!;
  });
  return mapping;
}
export function translateKey(key: string, map: Record<string, string>) {
  const result = map[key.toLowerCase()] ?? key;
  return key === key.toLowerCase() ? result : result.toUpperCase();
}

export const ACHIEVEMENTS: Achievement[] = [
  {
    code: "first_ink",
    name: "First Ink",
    description: "Save your first result.",
    test: () => true,
  },
  {
    code: "wpm_40",
    name: "Quick Quill",
    description: "Reach 40 WPM in Classic.",
    test: (r) => r.mode === "classic" && r.wpm >= 40,
  },
  {
    code: "wpm_70",
    name: "Speed Scribe",
    description: "Reach 70 WPM in Classic.",
    test: (r) => r.mode === "classic" && r.wpm >= 70,
  },
  {
    code: "flawless",
    name: "Flawless",
    description: "Finish with 100% accuracy.",
    test: (r) => r.mode !== "memory" && r.accuracy === 100 && r.wpm > 0,
  },
  {
    code: "memory_3",
    name: "Steel Trap",
    description: "Complete 3 Memory Rush rounds.",
    test: (r) => r.mode === "memory" && r.rounds >= 3,
  },
  {
    code: "chaos_tamer",
    name: "Chaos Tamer",
    description: "Finish Key Chaos above 80% accuracy.",
    test: (r) => r.mode === "chaos" && r.accuracy >= 80,
  },
];

const EMPTY: DB = {
  users: [],
  challenges: [],
  results: [],
  userAchievements: [],
  currentUserId: null,
};
const API = import.meta.env["VITE_API_URL"] ?? "http://127.0.0.1:5000/api";
let db: DB | null = null;
const listeners = new Set<() => void>();

function request<T>(method: string, path: string, body?: unknown): T {
  const xhr = new XMLHttpRequest();
  xhr.open(method, `${API}${path}`, false);
  xhr.setRequestHeader("Content-Type", "application/json");
  try {
    xhr.send(body === undefined ? null : JSON.stringify(body));
  } catch {
    throw new Error(
      "Can't reach the database. Make sure MySQL is running in XAMPP, then try again.",
    );
  }
  if (xhr.status < 200 || xhr.status >= 300) {
    let message = "Something went wrong. Please try again.";
    if (xhr.status === 0 || xhr.status === 503) {
      message = "Can't reach the database. Make sure MySQL is running in XAMPP, then try again.";
    }
    try {
      const response = JSON.parse(xhr.responseText) as { error?: string };
      if (response.error) message = response.error;
    } catch {
      // Keep the friendly status-based message.
    }
    throw new Error(message);
  }
  return JSON.parse(xhr.responseText) as T;
}
function normalize(raw: any): DB {
  return {
    users: raw.users.map((u: any) => ({
      id: String(u.user_id),
      username: u.username,
      createdAt: u.created_at,
    })),
    challenges: raw.challenges.map((c: any) => ({
      id: String(c.challenge_id),
      category: c.category,
      difficulty: c.difficulty,
      text: c.text,
    })),
    results: raw.results.map((r: any) => ({
      id: String(r.result_id),
      userId: String(r.user_id),
      mode: r.mode,
      wpm: r.wpm,
      accuracy: r.accuracy,
      errors: r.errors,
      score: r.score,
      duration: r.duration_seconds,
      rounds: r.rounds,
      createdAt: r.created_at,
      roundDetails: (r.round_details ?? []).map((d: any) => ({
        round: d.round_number,
        challengeId: String(d.challenge_id),
        accuracy: d.accuracy,
        passed: d.passed,
      })),
    })),
    userAchievements: raw.userAchievements.map((a: any) => ({
      userId: String(a.user_id),
      code: a.code,
      resultId: a.result_id == null ? null : String(a.result_id),
      unlockedAt: a.unlocked_at,
    })),
    currentUserId: raw.currentUserId == null ? null : String(raw.currentUserId),
  };
}
function apply(raw: any) {
  db = normalize(raw);
  listeners.forEach((listener) => listener());
  return db;
}
function load() {
  if (!db && typeof XMLHttpRequest !== "undefined") apply(request<any>("GET", "/state"));
  return db ?? EMPTY;
}
export function useDB() {
  return useSyncExternalStore(
    (listener) => {
      listeners.add(listener);
      return () => listeners.delete(listener);
    },
    load,
    () => EMPTY,
  );
}

export const store = {
  createUser(username: string) {
    return apply(request<any>("POST", "/users", { username }));
  },
  renameUser(id: string, username: string) {
    return apply(request<any>("PATCH", `/users/${id}`, { username }));
  },
  deleteUser(id: string) {
    return apply(request<any>("DELETE", `/users/${id}`));
  },
  selectUser(id: string | null) {
    return apply(request<any>("POST", "/selected", { userId: id }));
  },
  upsertChallenge(challenge: Omit<Challenge, "id"> & { id?: string | undefined }) {
    return apply(request<any>("POST", "/challenges", challenge));
  },
  deleteChallenge(id: string) {
    return apply(request<any>("DELETE", `/challenges/${id}`));
  },
  saveResult(result: Omit<Result, "id" | "createdAt" | "score">) {
    const response = request<any>("POST", "/results", {
      ...result,
      userId: Number(result.userId),
      duration: result.duration,
      roundDetails: (result.roundDetails ?? []).map((round) => ({
        ...round,
        challengeId: Number(round.challengeId),
      })),
    });
    apply(response.state);
    const saved = normalize({ ...response.state, results: [response.outcome.result] }).results[0];
    if (!saved) throw new Error("The saved result could not be reloaded.");
    return {
      result: saved,
      unlocked: response.outcome.unlocked,
      isNewBest: response.outcome.is_new_best,
    };
  },
  deleteResult(_id: string) {
    throw new Error("Result deletion is not enabled in the MySQL repository.");
  },
};
export function personalBest(results: Result[], userId: string, mode: ModeCode) {
  return results
    .filter((r) => r.userId === userId && r.mode === mode)
    .sort((a, b) => b.score - a.score)[0];
}
export function leaderboard(results: Result[], mode: ModeCode) {
  return [...new Set(results.filter((r) => r.mode === mode).map((r) => r.userId))]
    .map((id) => personalBest(results, id, mode)!)
    .sort((a, b) => b.score - a.score);
}
export function pickChallenge(
  challenges: Challenge[],
  difficulty: Difficulty | "any",
  exclude?: string,
) {
  const pool = challenges.filter((c) => difficulty === "any" || c.difficulty === difficulty);
  const usable = (pool.length ? pool : challenges).filter((c) => c.id !== exclude);
  return (usable.length ? usable : challenges)[
    Math.floor(Math.random() * Math.max(1, usable.length))
  ]!;
}
export function buildPassage(
  challenges: Challenge[],
  difficulty: Difficulty | "any",
  minLength = 600,
) {
  const parts: string[] = [];
  let last: string | undefined;
  while (parts.join(" ").length < minLength && challenges.length) {
    const challenge = pickChallenge(challenges, difficulty, last);
    parts.push(challenge.text);
    last = challenge.id;
  }
  return parts.join(" ");
}
export function formatDuration(seconds: number) {
  const minutes = Math.floor(seconds / 60);
  const rest = Math.round(seconds % 60);
  return minutes ? `${minutes}m ${rest.toString().padStart(2, "0")}s` : `${rest}s`;
}
