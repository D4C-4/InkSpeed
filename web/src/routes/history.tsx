import { createFileRoute, Link } from "@tanstack/react-router";
import { MODES, formatDuration, personalBest, store, useDB, type ModeCode } from "@/lib/inkspeed";

export const Route = createFileRoute("/history")({
  head: () => ({
    meta: [
      { title: "History & Personal Bests – InkSpeed" },
      { name: "description", content: "Review your saved InkSpeed typing results and personal bests." },
      { property: "og:title", content: "History & Personal Bests – InkSpeed" },
      { property: "og:description", content: "Review your saved InkSpeed typing results and personal bests." },
    ],
  }),
  component: History,
});

function History() {
  const db = useDB();
  const user = db.users.find((u) => u.id === db.currentUserId);
  if (!user) return <div className="ink-card p-8"><h1 className="text-3xl font-bold">No player selected</h1><Link to="/" className="ink-chip mt-4 inline-block">Pick a player</Link></div>;

  const mine = db.results.filter((r) => r.userId === user.id).sort((a, b) => b.createdAt.localeCompare(a.createdAt));
  const modes = Object.keys(MODES) as ModeCode[];
  const bestIds = new Set(modes.map((m) => personalBest(db.results, user.id, m)?.id));
  const unlocked = db.userAchievements.filter((a) => a.userId === user.id).length;

  return (
    <div className="space-y-8">
      <div>
        <p className="font-mono text-xs uppercase tracking-[0.3em] text-accent">@{user.username} · {unlocked} achievements</p>
        <h1 className="text-5xl font-extrabold">History</h1>
      </div>
      <div className="grid gap-4 md:grid-cols-3">
        {modes.map((m) => {
          const pb = personalBest(db.results, user.id, m);
          return (
            <div key={m} className="ink-card p-4">
              <p className="font-mono text-[10px] uppercase tracking-widest text-muted-foreground">Best · {MODES[m].name}</p>
              <p className="font-display text-3xl font-extrabold text-accent">{pb ? pb.score : "—"}</p>
              {pb && <p className="text-xs text-muted-foreground">{m === "memory" ? `${pb.rounds} rounds` : `${pb.wpm} WPM · ${pb.accuracy}%`}</p>}
            </div>
          );
        })}
      </div>
      <div className="ink-card overflow-x-auto">
        <table className="w-full text-sm">
          <thead className="border-b-[1.5px] border-foreground font-mono text-xs uppercase">
            <tr>{["Date", "Mode", "WPM", "Acc", "Errors", "Score", "Duration", "Rounds", ""].map((h) => <th key={h} className="p-3 text-left">{h}</th>)}</tr>
          </thead>
          <tbody>
            {mine.length === 0 && <tr><td colSpan={9} className="p-6 text-center text-muted-foreground">No results yet — go play a round.</td></tr>}
            {mine.map((r) => (
              <tr key={r.id} className="border-b last:border-0">
                <td className="p-3 font-mono text-xs">{new Date(r.createdAt).toLocaleString()}</td>
                <td className="p-3">{MODES[r.mode].name}{bestIds.has(r.id) && <span className="ml-2 text-xs text-accent">★ best</span>}</td>
                <td className="p-3">{r.wpm}</td>
                <td className="p-3">{r.accuracy}%</td>
                <td className="p-3">{r.errors}</td>
                <td className="p-3 font-bold">{r.score}</td>
                <td className="p-3">{formatDuration(r.duration)}</td>
                <td className="p-3">{r.mode === "memory" ? r.rounds : "—"}</td>
                <td className="p-3"><button onClick={() => confirm("Delete this result?") && store.deleteResult(user.id, r.id)} className="text-xs text-muted-foreground hover:text-destructive">delete</button></td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
