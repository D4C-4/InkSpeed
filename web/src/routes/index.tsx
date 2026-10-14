import { createFileRoute, Link } from "@tanstack/react-router";
import { useState } from "react";
import { MODES, store, useDB, validateUsername, type ModeCode } from "@/lib/inkspeed";

export const Route = createFileRoute("/")({
  head: () => ({
    meta: [
      { title: "InkSpeed – Typing Test and Practice" },
      {
        name: "description",
        content: "Pick a player and play Classic, Memory Rush, or Key Chaos typing tests.",
      },
      { property: "og:title", content: "InkSpeed – Typing Test and Practice" },
      {
        property: "og:description",
        content: "Pick a player and play Classic, Memory Rush, or Key Chaos typing tests.",
      },
    ],
  }),
  component: Home,
});

function Home() {
  const db = useDB();
  const [name, setName] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [editing, setEditing] = useState<string | null>(null);
  const [editName, setEditName] = useState("");
  const user = db.users.find((u) => u.id === db.currentUserId);

  const attempt = (fn: () => void) => {
    try {
      fn();
      setError(null);
    } catch (e) {
      setError((e as Error).message || "Something went wrong. Please try again.");
    }
  };

  return (
    <div className="space-y-12">
      <section>
        <p className="font-mono text-xs uppercase tracking-[0.3em] text-accent">
          Typing test & practice
        </p>
        <h1 className="mt-2 text-5xl font-extrabold leading-none md:text-7xl">
          Type fast.
          <br />
          Leave a mark.
        </h1>
      </section>

      <section className="ink-card p-6">
        <h2 className="text-2xl font-bold">Player</h2>
        <p className="text-sm text-muted-foreground">
          No password needed — just a username (4–20 characters).
        </p>
        <div className="mt-4 max-h-64 space-y-2 overflow-y-auto pr-2">
          {db.users.map((u) => (
            <div key={u.id} className="flex items-center gap-1">
              {editing === u.id ? (
                <form
                  onSubmit={(e) => {
                    e.preventDefault();
                    attempt(() => {
                      const validation = validateUsername(editName, db.users, u.id);
                      if (validation) throw new Error(validation);
                      store.renameUser(u.id, editName);
                      setEditing(null);
                    });
                  }}
                  className="flex gap-1"
                >
                  <input
                    autoFocus
                    value={editName}
                    onChange={(e) => {
                      setEditName(e.target.value);
                      setError(null);
                    }}
                    className="ink-chip w-36 bg-card"
                  />
                  <button className="ink-chip">Save</button>
                </form>
              ) : (
                <>
                  <button
                    onClick={() => store.selectUser(u.id)}
                    className={`ink-chip ${u.id === db.currentUserId ? "bg-primary text-primary-foreground" : "hover:bg-secondary"}`}
                  >
                    @{u.username}
                  </button>
                  <button
                    aria-label="Rename"
                    onClick={() => {
                      setEditing(u.id);
                      setEditName(u.username);
                    }}
                    className="px-1 text-xs text-muted-foreground hover:text-foreground"
                  >
                    edit
                  </button>
                  <button
                    aria-label="Delete"
                    onClick={() =>
                      confirm(`Delete ${u.username} and all their results?`) &&
                      attempt(() => store.deleteUser(u.id))
                    }
                    className="px-1 text-xs text-muted-foreground hover:text-destructive"
                  >
                    ×
                  </button>
                </>
              )}
            </div>
          ))}
        </div>
        <p className="mt-4 text-xs text-muted-foreground">
          Use 4-20 characters: letters, numbers, _ . - (no spaces)
        </p>
        <form
          onSubmit={(e) => {
            e.preventDefault();
            attempt(() => {
              const validation = validateUsername(name, db.users);
              if (validation) throw new Error(validation);
              store.createUser(name);
              setName("");
            });
          }}
          className="mt-2 flex gap-2"
        >
          <input
            value={name}
            onChange={(e) => {
              setName(e.target.value);
              setError(null);
            }}
            placeholder="new username"
            className="ink-chip flex-1 bg-card"
          />
          <button className="ink-chip bg-accent text-accent-foreground">Add player</button>
        </form>
        {error && <p className="mt-2 text-sm text-destructive">{error}</p>}
      </section>

      <section>
        <h2 className="mb-4 text-2xl font-bold">Choose a mode</h2>
        <div className="grid gap-6 md:grid-cols-3">
          {(Object.keys(MODES) as ModeCode[]).map((m, i) => (
            <div key={m} className="ink-card flex flex-col p-6">
              <span className="font-mono text-xs text-accent">0{i + 1}</span>
              <h3 className="mt-1 text-2xl font-bold">{MODES[m].name}</h3>
              <p className="mt-2 flex-1 text-sm text-muted-foreground">{MODES[m].blurb}</p>
              {user ? (
                <Link
                  to="/play/$mode"
                  params={{ mode: m }}
                  className="ink-chip mt-6 self-start bg-primary text-primary-foreground"
                >
                  Play →
                </Link>
              ) : (
                <span className="mt-6 text-xs text-muted-foreground">Select a player first</span>
              )}
            </div>
          ))}
        </div>
      </section>
    </div>
  );
}
