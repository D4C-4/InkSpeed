import { useEffect, useRef } from "react";
import { translateKey } from "@/lib/inkspeed";

interface Props {
  target: string;
  typed: string;
  onType: (next: string, wasError: boolean) => void;
  hidden?: boolean;
  keyMap?: Record<string, string> | undefined;
  disabled?: boolean;
  restricted?: boolean;
}

/** Captures keystrokes and renders correct/incorrect feedback over the target passage. */
export function TypingBox({ target, typed, onType, hidden, keyMap, disabled, restricted }: Props) {
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (!disabled) ref.current?.focus();
  }, [disabled]);

  function onKeyDown(e: React.KeyboardEvent) {
    if (disabled || e.ctrlKey || e.metaKey || e.altKey) return;
    if (e.key === "Backspace" && !restricted) {
      e.preventDefault();
      onType(typed.slice(0, -1), false);
      return;
    }
    if (
      restricted &&
      (e.key === "Backspace" ||
        e.key === "Delete" ||
        e.key === "ArrowLeft" ||
        e.key === "ArrowRight" ||
        e.key === "ArrowUp" ||
        e.key === "ArrowDown" ||
        e.key === "Home" ||
        e.key === "End")
    ) {
      e.preventDefault();
      return;
    }
    if (e.key.length !== 1) return;
    e.preventDefault();
    if (typed.length >= target.length) return;
    const ch = keyMap ? translateKey(e.key, keyMap) : e.key;
    onType(typed + ch, ch !== target[typed.length]);
  }

  const shown = hidden ? target.slice(0, Math.max(typed.length, 0)) : target;
  return (
    <div
      ref={ref}
      tabIndex={0}
      onKeyDown={onKeyDown}
      onPaste={(e) => restricted && e.preventDefault()}
      onCut={(e) => restricted && e.preventDefault()}
      onDrop={(e) => restricted && e.preventDefault()}
      onDragOver={(e) => restricted && e.preventDefault()}
      aria-label="Typing area"
      className="ink-card min-h-40 cursor-text break-all p-6 font-mono text-xl leading-relaxed outline-none focus:ring-2 focus:ring-ring"
    >
      {shown.split("").map((c, i) => {
        const t = typed[i];
        const cls = t === undefined ? "char-pending" : t === c ? "char-correct" : "char-wrong";
        return (
          <span key={i} className={`${cls} ${i === typed.length ? "caret" : ""}`}>
            {hidden && t !== undefined ? t : c}
          </span>
        );
      })}
      {(hidden || typed.length === target.length) && <span className="caret">&nbsp;</span>}
      {hidden && typed.length === 0 && (
        <span className="text-muted-foreground"> start typing from memory…</span>
      )}
    </div>
  );
}
