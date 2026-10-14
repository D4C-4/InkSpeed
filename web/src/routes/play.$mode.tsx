import { createFileRoute, Link, notFound } from "@tanstack/react-router";
import { useEffect, useMemo, useRef, useState } from "react";
import { TypingBox } from "@/components/TypingBox";
import {
  CHAOS_SCRAMBLES,
  MODES,
  buildPassage,
  calcAccuracy,
  calcWpm,
  compare,
  formatDuration,
  makeKeyMap,
  pickChallenge,
  scrambleCountFor,
  store,
  useDB,
  type Achievement,
  type Difficulty,
  type ModeCode,
  type Result,
  type RoundRecord,
} from "@/lib/inkspeed";

export const Route = createFileRoute("/play/$mode")({
  beforeLoad: ({ params }) => {
    if (!(params.mode in MODES)) throw notFound();
  },
  head: ({ params }) => {
    const name = MODES[params.mode as ModeCode]?.name ?? "Play";
    return {
      meta: [
        { title: `${name} – InkSpeed` },
        {
          name: "description",
          content: `Play ${name} on InkSpeed and measure your typing speed and accuracy.`,
        },
        { property: "og:title", content: `${name} – InkSpeed` },
        {
          property: "og:description",
          content: `Play ${name} on InkSpeed and measure your typing speed and accuracy.`,
        },
      ],
    };
  },
  component: Play,
});

type Phase = "setup" | "memorize" | "typing" | "done";
const PASS_ACCURACY = 90;

function Play() {
  const mode = Route.useParams().mode as ModeCode;
  const cfg = MODES[mode];
  const db = useDB();
  const user = db.users.find((u) => u.id === db.currentUserId);

  const [duration, setDuration] = useState(cfg.durations[0]!);
  const [difficulty, setDifficulty] = useState<Difficulty | "any">("any");
  const [phase, setPhase] = useState<Phase>("setup");
  const [target, setTarget] = useState("");
  const [challengeId, setChallengeId] = useState("");
  const [typed, setTyped] = useState("");
  const [errors, setErrors] = useState(0);
  const [startAt, setStartAt] = useState<number | null>(null);
  const [phaseEnd, setPhaseEnd] = useState(0);
  const [now, setNow] = useState(0);
  const [keyMap, setKeyMap] = useState<Record<string, string> | undefined>();
  const [rounds, setRounds] = useState<RoundRecord[]>([]);
  const [saved, setSaved] = useState<{
    result: Result;
    unlocked: Achievement[];
    isNewBest: boolean;
  } | null>(null);
  const [saveError, setSaveError] = useState<string | null>(null);
  const roundStats = useRef({ chars: 0, correct: 0, seconds: 0, errors: 0 });

  useEffect(() => {
    if (phase !== "memorize" && phase !== "typing") return;
    const t = setInterval(() => setNow(Date.now()), 100);
    return () => clearInterval(t);
  }, [phase]);

  // memorize countdown -> hide passage
  useEffect(() => {
    if (phase === "memorize" && now >= phaseEnd && phaseEnd) {
      setPhase("typing");
      setStartAt(null);
    }
  }, [now, phase, phaseEnd]);

  // classic time limit
  useEffect(() => {
    if (mode === "classic" && phase === "typing" && startAt && now - startAt >= duration * 1000)
      finish(typed, errors, duration);
  }, [now]); // eslint-disable-line react-hooks/exhaustive-deps

  function newRound() {
    const c = pickChallenge(db.challenges, difficulty, challengeId);
    setTarget(c.text);
    setChallengeId(c.id);
    setTyped("");
    setErrors(0);
    setStartAt(null);
    setPhaseEnd(Date.now() + duration * 1000);
    setNow(Date.now());
    setPhase("memorize");
  }

  function start() {
    setSaved(null);
    setSaveError(null);
    setRounds([]);
    roundStats.current = { chars: 0, correct: 0, seconds: 0, errors: 0 };
    if (mode === "classic") {
      setTarget(buildPassage(db.challenges, difficulty, duration * 12));
      setTyped("");
      setErrors(0);
      setStartAt(null);
      setPhase("typing");
    } else {
      if (mode === "chaos") setKeyMap(makeKeyMap(scrambleCountFor(difficulty)));
      newRound();
    }
  }

  function save(r: Omit<Result, "id" | "createdAt" | "score" | "userId">) {
    if (!user) return;
    try {
      setSaved(store.saveResult({ ...r, userId: user.id }));
    } catch (e) {
      setSaveError((e as Error).message);
    }
    setPhase("done");
  }

  function finish(finalTyped: string, finalErrors: number, seconds: number) {
    const { correct } = compare(target, finalTyped);
    const wpm = calcWpm(finalTyped.length, seconds);
    const accuracy = calcAccuracy(correct, finalTyped.length);
    if (mode !== "memory") {
      save({ mode, wpm, accuracy, errors: finalErrors, duration: Math.round(seconds), rounds: 0 });
      return;
    }
    // Memory Rush round
    const s = roundStats.current;
    s.chars += finalTyped.length;
    s.correct += correct;
    s.seconds += seconds;
    s.errors += finalErrors;
    const passed = accuracy >= PASS_ACCURACY;
    const next = [...rounds, { round: rounds.length + 1, challengeId, accuracy, passed }];
    setRounds(next);
    if (passed) {
      newRound();
      return;
    }
    save({
      mode,
      wpm: calcWpm(s.chars, s.seconds),
      accuracy: calcAccuracy(s.correct, s.chars),
      errors: s.errors,
      duration: Math.round(s.seconds),
      rounds: next.filter((r) => r.passed).length,
      roundDetails: next,
    });
  }

  function onType(next: string, wasError: boolean) {
    if (mode !== "classic" && next.length < typed.length) return;
    const t0 = startAt ?? Date.now();
    if (!startAt) {
      setStartAt(t0);
      setNow(t0);
    }
    const e = errors + (wasError ? 1 : 0);
    setTyped(next);
    setErrors(e);
    if (next.length === target.length) finish(next, e, Math.max((Date.now() - t0) / 1000, 0.5));
  }

  const elapsed = startAt ? (now - startAt) / 1000 : 0;
  const live = useMemo(() => {
    const { correct } = compare(target, typed);
    return {
      wpm: calcWpm(typed.length, Math.max(elapsed, 1)),
      acc: calcAccuracy(correct, typed.length),
    };
  }, [typed, target, elapsed]);

  if (!user) {
    return (
      <div className="ink-card p-8">
        <h1 className="text-3xl font-bold">Pick a player first</h1>
        <Link to="/" className="ink-chip mt-4 inline-block">
          Go to players
        </Link>
      </div>
    );
  }

  return (
    <div className="space-y-8">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <p className="font-mono text-xs uppercase tracking-[0.3em] text-accent">
            @{user.username}
          </p>
          <h1 className="text-5xl font-extrabold">{cfg.name}</h1>
          <p className="text-muted-foreground">{cfg.blurb}</p>
        </div>
        {phase !== "setup" && phase !== "done" && (
          <button
            onClick={() => {
              setPhase("setup");
              setTyped("");
              setTarget("");
              setKeyMap(undefined);
              setRounds([]);
              setErrors(0);
              setStartAt(null);
            }}
            className="ink-chip hover:bg-secondary"
          >
            Quit game
          </button>
        )}
      </div>

      {phase === "setup" && (
        <div className="ink-card space-y-6 p-6">
          <Option
            label={cfg.durationLabel}
            value={duration}
            options={cfg.durations.map((d) => ({ v: d, l: formatDuration(d) }))}
            onChange={setDuration}
          />
          <Option
            label="Difficulty"
            value={difficulty}
            options={(["any", "easy", "medium", "hard"] as const).map((d) => ({ v: d, l: d }))}
            onChange={setDifficulty}
          />
          {mode === "memory" && (
            <p className="text-sm text-muted-foreground">
              Pass a round with at least {PASS_ACCURACY}% accuracy. One failed round ends the game.
            </p>
          )}
          {mode === "chaos" && (
            <p className="text-sm text-muted-foreground">
              Easy scrambles {CHAOS_SCRAMBLES.easy} letter keys, medium {CHAOS_SCRAMBLES.medium},
              hard {CHAOS_SCRAMBLES.hard}. Only inside InkSpeed — your real keyboard is untouched.
              Pick "any" for a random amount.
            </p>
          )}
          <button
            onClick={start}
            className="ink-chip bg-accent px-6 py-2 text-base text-accent-foreground"
          >
            Start
          </button>
        </div>
      )}

      {(phase === "memorize" || phase === "typing") && (
        <>
          <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
            {phase === "memorize" ? (
              <Stat
                label="Memorize"
                value={`${Math.max(0, Math.ceil((phaseEnd - now) / 1000))}s`}
                accent
              />
            ) : mode === "classic" ? (
              <Stat
                label="Time left"
                value={formatDuration(Math.max(0, duration - elapsed))}
                accent
              />
            ) : (
              <Stat label="Time" value={formatDuration(elapsed)} accent />
            )}
            <Stat label="WPM" value={live.wpm} />
            <Stat label="Accuracy" value={`${live.acc}%`} />
            {mode === "memory" ? (
              <Stat label="Round" value={rounds.length + 1} />
            ) : (
              <Stat label="Errors" value={errors} />
            )}
          </div>

          {phase === "memorize" ? (
            <div className="ink-card p-6 font-mono text-xl leading-relaxed">{target}</div>
          ) : (
            <TypingBox
              target={target}
              typed={typed}
              onType={onType}
              hidden={mode !== "classic"}
              restricted={mode !== "classic"}
              keyMap={mode === "chaos" ? keyMap : undefined}
            />
          )}
          {phase === "memorize" && (
            <button
              onClick={() => {
                setPhase("typing");
                setStartAt(null);
              }}
              className="ink-chip hover:bg-secondary"
            >
              I'm ready — hide it
            </button>
          )}
          {phase === "typing" && mode === "classic" && (
            <p className="text-sm text-muted-foreground">Timer starts on your first keystroke.</p>
          )}
          {mode === "chaos" && keyMap && phase === "typing" && <KeyLegend map={keyMap} />}
        </>
      )}

      {phase === "done" && (
        <div className="ink-card space-y-6 p-6">
          <h2 className="text-3xl font-bold">
            {saved?.isNewBest ? "New personal best!" : "Result saved"}
          </h2>
          {saveError && <p className="text-destructive">Could not save: {saveError}</p>}
          {saved && (
            <div className="grid grid-cols-2 gap-4 md:grid-cols-5">
              <Stat label="Score" value={saved.result.score} accent />
              <Stat label="WPM" value={saved.result.wpm} />
              <Stat label="Accuracy" value={`${saved.result.accuracy}%`} />
              <Stat label="Errors" value={saved.result.errors} />
              {mode === "memory" ? (
                <Stat label="Rounds" value={saved.result.rounds} />
              ) : (
                <Stat label="Duration" value={formatDuration(saved.result.duration)} />
              )}
            </div>
          )}
          {saved && saved.unlocked.length > 0 && (
            <div>
              <p className="font-mono text-xs uppercase tracking-widest text-accent">
                Achievements unlocked
              </p>
              <ul className="mt-2 flex flex-wrap gap-2">
                {saved.unlocked.map((a) => (
                  <li key={a.code} className="ink-chip bg-secondary">
                    {a.name} — {a.description}
                  </li>
                ))}
              </ul>
            </div>
          )}
          <div className="flex gap-2">
            <button onClick={start} className="ink-chip bg-accent text-accent-foreground">
              Play again
            </button>
            <button onClick={() => setPhase("setup")} className="ink-chip hover:bg-secondary">
              Change settings
            </button>
            <Link to="/history" className="ink-chip hover:bg-secondary">
              History
            </Link>
          </div>
        </div>
      )}
    </div>
  );
}

function Option<T extends string | number>({
  label,
  value,
  options,
  onChange,
}: {
  label: string;
  value: T;
  options: { v: T; l: string }[];
  onChange: (v: T) => void;
}) {
  return (
    <div>
      <p className="mb-2 font-mono text-xs uppercase tracking-widest text-muted-foreground">
        {label}
      </p>
      <div className="flex flex-wrap gap-2">
        {options.map((o) => (
          <button
            key={String(o.v)}
            onClick={() => onChange(o.v)}
            className={`ink-chip capitalize ${o.v === value ? "bg-primary text-primary-foreground" : "hover:bg-secondary"}`}
          >
            {o.l}
          </button>
        ))}
      </div>
    </div>
  );
}

export function Stat({
  label,
  value,
  accent,
}: {
  label: string;
  value: string | number;
  accent?: boolean;
}) {
  return (
    <div className="ink-card p-4">
      <p className="font-mono text-[10px] uppercase tracking-widest text-muted-foreground">
        {label}
      </p>
      <p className={`font-display text-3xl font-extrabold ${accent ? "text-accent" : ""}`}>
        {value}
      </p>
    </div>
  );
}

function KeyLegend({ map }: { map: Record<string, string> }) {
  // show only the scrambled keys: to get letter X, press key Y
  const reverse = Object.entries(map).reduce<Record<string, string>>(
    (acc, [k, v]) => (k === v ? acc : { ...acc, [v]: k }),
    {},
  );
  return (
    <div>
      <p className="mb-2 font-mono text-xs uppercase tracking-widest text-muted-foreground">
        To type ↑ press ↓
      </p>
      <div className="flex flex-wrap gap-1 font-mono text-xs">
        {Object.keys(reverse)
          .sort()
          .map((l) => (
            <div key={l} className="border border-foreground px-1.5 text-center">
              <div>{l}</div>
              <div className="text-accent">{reverse[l]}</div>
            </div>
          ))}
      </div>
    </div>
  );
}
