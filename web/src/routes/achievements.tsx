import { createFileRoute, Link } from "@tanstack/react-router";
import { ACHIEVEMENTS, useDB } from "@/lib/inkspeed";

export const Route = createFileRoute("/achievements")({
  head: () => ({
    meta: [
      { title: "Achievements – InkSpeed" },
      { name: "description", content: "See which InkSpeed achievements you have unlocked and which are still waiting." },
      { property: "og:title", content: "Achievements – InkSpeed" },
      { property: "og:description", content: "See which InkSpeed achievements you have unlocked and which are still waiting." },
    ],
  }),
  component: Achievements,
});

function Achievements() {
  const db = useDB();
  const user = db.users.find((u) => u.id === db.currentUserId);
  const unlocked = user ? db.userAchievements.filter((a) => a.userId === user.id) : [];

  if (!user) {
    return (
      <div className="ink-card p-8">
        <h1 className="text-3xl font-bold">Pick a player first</h1>
        <Link to="/" className="ink-chip mt-4 inline-block">Go to players</Link>
      </div>
    );
  }

  return (
    <div className="space-y-8">
      <div>
        <p className="font-mono text-xs uppercase tracking-[0.3em] text-accent">@{user.username}</p>
        <h1 className="text-5xl font-extrabold">Achievements</h1>
        <p className="text-muted-foreground">
          {unlocked.length} of {ACHIEVEMENTS.length} unlocked.
        </p>
      </div>

      <div className="grid gap-4 md:grid-cols-2">
        {ACHIEVEMENTS.map((a) => {
          const got = unlocked.find((u) => u.code === a.code);
          return (
            <div key={a.code} className={`ink-card p-5 ${got ? "" : "opacity-60"}`}>
              <div className="flex items-start justify-between gap-3">
                <div>
                  <h2 className="text-xl font-bold">{a.name}</h2>
                  <p className="mt-1 text-sm text-muted-foreground">{a.description}</p>
                </div>
                <span className={`ink-chip shrink-0 font-mono text-[10px] uppercase tracking-widest ${got ? "bg-accent text-accent-foreground" : ""}`}>
                  {got ? "Unlocked" : "Locked"}
                </span>
              </div>
              {got && (
                <p className="mt-3 font-mono text-xs text-muted-foreground">
                  {new Date(got.unlockedAt).toLocaleDateString()}
                </p>
              )}
            </div>
          );
        })}
      </div>

      <Link to="/" className="ink-chip inline-block hover:bg-secondary">Play a mode</Link>
    </div>
  );
}
