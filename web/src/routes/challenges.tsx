import { createFileRoute } from "@tanstack/react-router";
import { useState } from "react";
import { store, useDB, type Challenge, type Difficulty } from "@/lib/inkspeed";

export const Route = createFileRoute("/challenges")({
  head: () => ({
    meta: [
      { title: "Challenge Management – InkSpeed" },
      { name: "description", content: "Add, edit, and delete the typing passages used in InkSpeed." },
      { property: "og:title", content: "Challenge Management – InkSpeed" },
      { property: "og:description", content: "Add, edit, and delete the typing passages used in InkSpeed." },
    ],
  }),
  component: Challenges,
});

const blank = { id: undefined as string | undefined, category: "", difficulty: "easy" as Difficulty, text: "" };

function Challenges() {
  const db = useDB();
  const [form, setForm] = useState(blank);
  const [error, setError] = useState<string | null>(null);

  const submit = (e: React.FormEvent) => {
    e.preventDefault();
    try { store.upsertChallenge(form); setForm(blank); setError(null); } catch (err) { setError((err as Error).message); }
  };
  const remove = (c: Challenge) => {
    if (!confirm("Delete this passage?")) return;
    try { store.deleteChallenge(c.id); } catch (err) { setError((err as Error).message); }
  };

  return (
    <div className="space-y-8">
      <h1 className="text-5xl font-extrabold">Challenges</h1>
      <form onSubmit={submit} className="ink-card space-y-3 p-6">
        <h2 className="text-xl font-bold">{form.id ? "Edit passage" : "Add passage"}</h2>
        <div className="flex flex-wrap gap-2">
          <input value={form.category} onChange={(e) => setForm({ ...form, category: e.target.value })} placeholder="Category" className="ink-chip flex-1 bg-card" />
          <select value={form.difficulty} onChange={(e) => setForm({ ...form, difficulty: e.target.value as Difficulty })} className="ink-chip bg-card">
            <option value="easy">easy</option><option value="medium">medium</option><option value="hard">hard</option>
          </select>
        </div>
        <textarea value={form.text} onChange={(e) => setForm({ ...form, text: e.target.value })} placeholder="Passage text (10–400 characters)" rows={3} className="ink-chip w-full bg-card" />
        {error && <p className="text-sm text-destructive">{error}</p>}
        <div className="flex gap-2">
          <button className="ink-chip bg-accent text-accent-foreground">{form.id ? "Save changes" : "Add"}</button>
          {form.id && <button type="button" onClick={() => setForm(blank)} className="ink-chip">Cancel</button>}
        </div>
      </form>
      <ul className="space-y-3">
        {db.challenges.map((c) => (
          <li key={c.id} className="ink-card flex flex-wrap items-start gap-4 p-4">
            <div className="flex-1">
              <p className="font-mono text-xs uppercase text-muted-foreground">{c.category} · <span className="text-accent">{c.difficulty}</span></p>
              <p className="mt-1 font-mono">{c.text}</p>
            </div>
            <button onClick={() => setForm({ ...c })} className="text-xs text-muted-foreground hover:text-foreground">edit</button>
            <button onClick={() => remove(c)} className="text-xs text-muted-foreground hover:text-destructive">delete</button>
          </li>
        ))}
      </ul>
    </div>
  );
}
