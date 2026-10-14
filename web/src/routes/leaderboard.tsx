import { createFileRoute } from "@tanstack/react-router";
import { useState } from "react";
import { MODES, leaderboard, useDB, type ModeCode } from "@/lib/inkspeed";

export const Route = createFileRoute("/leaderboard")({
  head: () => ({
    meta: [
      { title: "Leaderboard – InkSpeed" },
      { name: "description", content: "See the top InkSpeed scores for Classic, Memory Rush, and Key Chaos." },
      { property: "og:title", content: "Leaderboard – InkSpeed" },
      { property: "og:description", content: "See the top InkSpeed scores for Classic, Memory Rush, and Key Chaos." },
    ],
  }),
  component: Leaderboard,
});

function Leaderboard() {
  const db = useDB();
  const [mode, setMode] = useState<ModeCode>("classic");
  const rows = leaderboard(db.results, mode);
  const name = (id: string) => db.users.find((u) => u.id === id)?.username ?? "?";

  return (
    <div className="space-y-8">
      <h1 className="text-5xl font-extrabold">Leaderboard</h1>
      <div className="flex flex-wrap gap-2">
        {(Object.keys(MODES) as ModeCode[]).map((m) => (
          <button key={m} onClick={() => setMode(m)} className={`ink-chip ${m === mode ? "bg-primary text-primary-foreground" : "hover:bg-secondary"}`}>{MODES[m].name}</button>
        ))}
      </div>
      <ol className="space-y-3">
        {rows.length === 0 && <li className="ink-card p-6 text-muted-foreground">No scores yet for {MODES[mode].name}.</li>}
        {rows.map((r, i) => (
          <li key={r.id} className={`ink-card flex items-center gap-6 p-4 ${r.userId === db.currentUserId ? "bg-secondary" : ""}`}>
            <span className={`font-display text-4xl font-extrabold ${i === 0 ? "text-accent" : ""}`}>{i + 1}</span>
            <span className="flex-1 font-mono">@{name(r.userId)}</span>
            <span className="text-sm text-muted-foreground">{mode === "memory" ? `${r.rounds} rounds` : `${r.wpm} WPM · ${r.accuracy}%`}</span>
            <span className="font-display text-2xl font-bold">{r.score}</span>
          </li>
        ))}
      </ol>
    </div>
  );
}
