import { describe, expect, it } from "vitest";
import {
  CHAOS_SCRAMBLES,
  calcAccuracy,
  calcScore,
  calcWpm,
  makeKeyMap,
  personalBest,
  scrambleCountFor,
  validateUsername,
  type Result,
} from "./inkspeed";

const r = (id: string, score: number): Result => ({
  id,
  userId: "u",
  mode: "classic",
  wpm: 0,
  accuracy: 0,
  errors: 0,
  score,
  duration: 60,
  rounds: 0,
  createdAt: "",
});

describe("InkSpeed rules", () => {
  it("WPM = chars / 5 / minutes", () => expect(calcWpm(300, 60)).toBe(60));
  it("accuracy = correct / typed", () => expect(calcAccuracy(90, 100)).toBe(90));
  it("classic score = WPM x accuracy/100", () => expect(calcScore("classic", 50, 80, 0)).toBe(40));
  it("memory score = rounds only", () => expect(calcScore("memory", 99, 100, 4)).toBe(4));
  it("key chaos scrambles 5 letters on easy, 8 on medium, 10 on hard", () => {
    expect(CHAOS_SCRAMBLES).toEqual({ easy: 5, medium: 8, hard: 10 });
    expect(scrambleCountFor("easy")).toBe(5);
    expect(scrambleCountFor("medium")).toBe(8);
    expect(scrambleCountFor("hard")).toBe(10);
  });
  it("makeKeyMap scrambles only the chosen number of letters, none mapping to itself", () => {
    for (const count of [5, 8, 10]) {
      const map = makeKeyMap(count);
      const scrambled = Object.entries(map).filter(([from, to]) => from !== to);
      expect(scrambled).toHaveLength(count);
      for (const [from, to] of scrambled) expect(scrambled.some(([f]) => f === to)).toBe(true);
    }
  });
  it("makes varied maps for every chaos difficulty", () => {
    for (const count of [5, 8, 10]) {
      const maps = Array.from({ length: 50 }, () => makeKeyMap(count));
      const signatures = new Set(maps.map((map) => JSON.stringify(map)));
      expect(signatures.size).toBeGreaterThan(1);
      for (const map of maps) {
        const scrambled = Object.entries(map).filter(([from, to]) => from !== to);
        expect(scrambled).toHaveLength(count);
        expect(
          scrambled.every(
            ([from, to]) => from !== to && Object.prototype.hasOwnProperty.call(map, to),
          ),
        ).toBe(true);
      }
    }
  });
  it("username must be 4-20 chars", () => {
    expect(validateUsername("abc", [])).not.toBeNull();
    expect(validateUsername("a".repeat(21), [])).not.toBeNull();
    expect(validateUsername("abcd", [])).toBeNull();
  });
  it("uses the exact username messages and allows case-only self-renames", () => {
    const users = [{ id: "1", username: "Jaik", createdAt: "" }];
    expect(validateUsername("", users)).toBe("Please enter a username.");
    expect(validateUsername("abc", users)).toBe(
      "Username is too short. Use at least 4 characters.",
    );
    expect(validateUsername("a".repeat(21), users)).toBe(
      "Username is too long. Use 20 characters or fewer.",
    );
    expect(validateUsername("bad name", users)).toBe(
      "Use only letters, numbers, underscore (_), dot (.) or hyphen (-). No spaces.",
    );
    expect(validateUsername("jaik", users)).toContain('The username "jaik" is already taken.');
    expect(validateUsername("JAIK", users, "1")).toBeNull();
  });
  it("personal best falls back to next best after deletion", () => {
    const list = [r("a", 30), r("b", 50)];
    expect(personalBest(list, "u", "classic")?.id).toBe("b");
    expect(
      personalBest(
        list.filter((x) => x.id !== "b"),
        "u",
        "classic",
      )?.id,
    ).toBe("a");
  });
});
