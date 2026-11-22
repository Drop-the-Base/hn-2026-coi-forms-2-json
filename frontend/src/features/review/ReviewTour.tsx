import {
  useCallback,
  useLayoutEffect,
  useRef,
  useState,
  type KeyboardEvent,
} from "react";
import { formatConfidence, REVIEW_THRESHOLD } from "../../shared/confidence";
import { plural } from "./review";

interface Step {
  /** Elements with this word in data-tour; the ring goes around all visible ones. */
  target: string;
  /** Only the first visible one, e.g. one marked element out of many. */
  first?: boolean;
  title: string;
  text: string;
}

const STEPS: Step[] = [
  {
    target: "ocena",
    title: "Ocena ogólna",
    text: "Liczba od 0 do 1 mówi, jak pewny jest cały wynik. Obok widzisz, ile elementów trzeba poprawić albo sprawdzić.",
  },
  {
    target: "pewnosc",
    first: true,
    title: "Pewność przy elementach",
    text: `Pasek na marginesie oznacza element do sprawdzenia: pełny czerwony to niska pewność, kreskowany to średnia. Sprawdzasz wszystko poniżej ${formatConfidence(REVIEW_THRESHOLD)}.`,
  },
  {
    target: "problemy",
    title: "Lista problemów",
    text: "Kliknij problem, a pokażemy ten element do poprawy. Klawisz F8 przechodzi do następnego. Są tu też uwagi o dostępności, prostym języku i danych osobowych, jeśli je znaleźliśmy.",
  },
  {
    target: "oryginal",
    title: "Oryginał obok",
    text: "Zakładka „Oryginał” pokazuje wgrany dokument. Otwórz ją w jednej kolumnie, a w drugiej porównasz wynik.",
  },
  {
    target: "podglad",
    title: "Podgląd formularza",
    text: "Tak wnioskodawca zobaczy e-usługę. Przycisk „Drukuj / zapisz PDF” zapisze cały formularz.",
  },
  {
    target: "edycja",
    title: "Edycja",
    text: "W widoku „Pole” poprawiasz wybrany element w zwykłym formularzu. W zakładce „JSON” zmieniasz kod wprost.",
  },
  {
    target: "pobierz",
    title: "Pobranie",
    text: "Gdy wszystko się zgadza, pobierz poprawiony JSON. Przycisk nie działa, dopóki JSON ma błędy.",
  },
];

const shown = (el: Element) =>
  "checkVisibility" in el ? el.checkVisibility() : true; // jsdom has no layout
function targets(step: Step) {
  const all = [
    ...document.querySelectorAll(`[data-tour~="${step.target}"]`),
  ].filter(shown);
  return step.first ? all.slice(0, 1) : all;
}

interface Box {
  top: number;
  left: number;
  right: number;
  bottom: number;
}
const GAP = 12;
const EDGE = 16;

/** Card position next to the target: below, above, right, left, else inside its bottom-right corner. */
export function place(t: Box, w: number, h: number, vw: number, vh: number) {
  const x = (left: number) => Math.max(EDGE, Math.min(left, vw - w - EDGE));
  const y = (top: number) => Math.max(EDGE, Math.min(top, vh - h - EDGE));
  if (t.bottom + GAP + h <= vh - EDGE)
    return { top: t.bottom + GAP, left: x(t.left) };
  if (t.top - GAP - h >= EDGE) return { top: t.top - GAP - h, left: x(t.left) };
  if (t.right + GAP + w <= vw - EDGE)
    return { top: y(t.top), left: t.right + GAP };
  if (t.left - GAP - w >= EDGE)
    return { top: y(t.top), left: t.left - GAP - w };
  return { top: y(t.bottom - h - EDGE), left: x(t.right - w - EDGE) };
}

/** Opens as a modal and returns focus to where it was when the dialog goes away. */
function modal(el: HTMLDialogElement, focus: string) {
  const back = document.activeElement as HTMLElement | null;
  el.showModal();
  el.querySelector<HTMLElement>(focus)?.focus();
  return () => back?.focus();
}
const tourRef = (el: HTMLDialogElement | null) =>
  el ? modal(el, ".tour__next") : undefined;

// Answered once per page load; a refresh asks again (product decision, #188: no storage).
let asked = false;

/** Guided tour of the review screen (#188, FR-T1): first a question, then a spotlight per step. */
export function ReviewTour() {
  const [state, setState] = useState<"prompt" | number | null>(() =>
    asked ? null : "prompt",
  );
  const [steps, setSteps] = useState(STEPS);
  const hole = useRef<HTMLDivElement>(null);
  const card = useRef<HTMLDivElement>(null);
  const next = useRef<HTMLButtonElement>(null);
  const step = typeof state === "number" ? steps[state] : undefined;

  const available = () => setSteps(STEPS.filter((s) => targets(s).length));
  // Stable callback refs: a new one each render would reopen the dialog and move the focus.
  const promptRef = useCallback((el: HTMLDialogElement | null) => {
    if (!el) return;
    setSteps(STEPS.filter((s) => targets(s).length));
    return modal(el, ".btn--primary");
  }, []);
  const close = () => {
    asked = true;
    setState(null);
  };
  const go = (index: number) => {
    setState(index);
    if (index === 0) next.current?.focus(); // "Wstecz" turns disabled under the focus
  };
  const onKeyDown = (e: KeyboardEvent) => {
    if (e.key !== "Escape") return;
    e.preventDefault();
    close();
  };

  useLayoutEffect(() => {
    if (!step) return;
    targets(step)[0]?.scrollIntoView?.({ block: "nearest", inline: "nearest" });
    function measure() {
      if (!step || !hole.current || !card.current) return;
      // A confidence mark sits in the margin, outside its element's box.
      const rects = targets(step)
        .flatMap((el) => [el, ...el.querySelectorAll(":scope > .mark")])
        .map((el) => el.getBoundingClientRect());
      const vw = window.innerWidth;
      const vh = window.innerHeight;
      // The union of the targets, cut to the viewport (tall panes go past it).
      const t = {
        top: Math.max(0, Math.min(...rects.map((r) => r.top)) - 4),
        left: Math.max(0, Math.min(...rects.map((r) => r.left)) - 4),
        right: Math.min(vw, Math.max(...rects.map((r) => r.right)) + 4),
        bottom: Math.min(vh, Math.max(...rects.map((r) => r.bottom)) + 4),
      };
      Object.assign(hole.current.style, {
        top: `${t.top}px`,
        left: `${t.left}px`,
        width: `${Math.max(0, t.right - t.left)}px`,
        height: `${Math.max(0, t.bottom - t.top)}px`,
      });
      const at = place(
        t,
        card.current.offsetWidth,
        card.current.offsetHeight,
        vw,
        vh,
      );
      card.current.style.top = `${at.top}px`;
      card.current.style.left = `${at.left}px`;
    }
    measure();
    window.addEventListener("resize", measure);
    document.addEventListener("scroll", measure, true);
    return () => {
      window.removeEventListener("resize", measure);
      document.removeEventListener("scroll", measure, true);
    };
  }, [step]);

  return (
    <>
      <button
        className="btn btn--ghost btn--sm"
        type="button"
        aria-haspopup="dialog"
        onClick={() => {
          available();
          setState(0);
        }}
      >
        <span className="tour__q" aria-hidden="true">
          ?
        </span>
        Samouczek
      </button>
      {state === "prompt" && (
        <dialog
          ref={promptRef}
          className="dialog"
          aria-labelledby="tour-ask-h"
          aria-describedby="tour-ask-p"
          onKeyDown={onKeyDown}
          onCancel={(e) => {
            e.preventDefault();
            close();
          }}
        >
          <h2 id="tour-ask-h">Pierwszy raz na tym ekranie?</h2>
          <p id="tour-ask-p">
            Krótki samouczek pokaże, co gdzie jest. Zajmie mniej niż minutę.
          </p>
          <div className="dialog__actions">
            <button
              className="btn btn--secondary"
              type="button"
              onClick={close}
            >
              Pomiń
            </button>
            <button
              className="btn btn--primary"
              type="button"
              onClick={() => setState(0)}
            >
              Pokaż samouczek (
              {plural(steps.length, ["krok", "kroki", "kroków"])})
            </button>
          </div>
        </dialog>
      )}
      {step && typeof state === "number" && (
        <dialog
          ref={tourRef}
          className="tour"
          aria-labelledby="tour-h"
          aria-describedby="tour-p"
          onKeyDown={onKeyDown}
          onCancel={(e) => {
            e.preventDefault();
            close();
          }}
        >
          <div className="tour__hole" ref={hole}></div>
          <div className="tour__card" ref={card}>
            <p className="tour__pos" aria-live="polite">
              Krok {state + 1} z {steps.length}
              <span className="visually-hidden">: {step.title}</span>
            </p>
            <h2 id="tour-h">{step.title}</h2>
            <p id="tour-p">{step.text}</p>
            <div className="tour__actions">
              <button
                className="btn btn--ghost btn--sm tour__skip"
                type="button"
                onClick={close}
              >
                Pomiń samouczek
              </button>
              <button
                className="btn btn--secondary btn--sm"
                type="button"
                disabled={state === 0}
                onClick={() => go(state - 1)}
              >
                Wstecz
              </button>
              <button
                ref={next}
                className="btn btn--primary btn--sm tour__next"
                type="button"
                onClick={() =>
                  state === steps.length - 1 ? close() : go(state + 1)
                }
              >
                {state === steps.length - 1 ? "Zakończ" : "Dalej"}
              </button>
            </div>
          </div>
        </dialog>
      )}
    </>
  );
}
