import { json } from "@codemirror/lang-json";
import {
  ensureSyntaxTree,
  HighlightStyle,
  syntaxHighlighting,
  syntaxTree,
} from "@codemirror/language";
import { lintGutter, setDiagnostics, type Diagnostic } from "@codemirror/lint";
import {
  EditorState,
  RangeSet,
  StateEffect,
  StateField,
  type Range,
} from "@codemirror/state";
import { Decoration, EditorView, gutter, GutterMarker } from "@codemirror/view";
import { tags } from "@lezer/highlight";
import { basicSetup } from "codemirror";
import { useEffect, useImperativeHandle, useRef, type Ref } from "react";
import { confidenceLevel } from "../../shared/confidence";
import { locate } from "./review";

export interface JsonEditorHandle {
  text: () => string;
  format: () => void;
  /** Moves the cursor to the element at the JSON path, highlights its lines and focuses the editor. */
  reveal: (path: string) => boolean;
  goTo: (pos: number) => void;
}

interface Props {
  ref: Ref<JsonEditorHandle>;
  initial: string;
  /** Called 300 ms after the last change and when the editor loses focus. */
  onChange: (text: string) => void;
  confidence: Record<string, number>;
  diagnostics: Diagnostic[];
  describedBy: string;
}

class ConfidenceMarker extends GutterMarker {
  constructor(readonly elementClass: string) {
    super();
  }
}
const MARKERS = {
  low: new ConfidenceMarker("cm-conf-low"),
  medium: new ConfidenceMarker("cm-conf-medium"),
};

function confidenceMarks(
  state: EditorState,
  confidence: Record<string, number>,
) {
  const tree =
    ensureSyntaxTree(state, state.doc.length, 200) ?? syntaxTree(state);
  const read = (from: number, to: number) => state.sliceDoc(from, to);
  const marks: Range<GutterMarker>[] = [];
  for (const [path, value] of Object.entries(confidence)) {
    const level = confidenceLevel(value);
    if (level === "high") continue;
    const at = locate(tree, read, path);
    if (!at) continue;
    const last = state.doc.lineAt(at.to).number;
    for (let n = state.doc.lineAt(at.from).number; n <= last; n++)
      marks.push(MARKERS[level].range(state.doc.line(n).from));
  }
  return RangeSet.of(marks, true);
}

const setCurrent = StateEffect.define<{ from: number; to: number }>();
const currentLines = StateField.define({
  create: () => Decoration.none,
  update(lines, tr) {
    lines = lines.map(tr.changes);
    for (const effect of tr.effects.filter((e) => e.is(setCurrent))) {
      const { from, to } = effect.value;
      const decorations = [];
      for (let pos = from; pos <= to;) {
        const line = tr.state.doc.lineAt(pos);
        decorations.push(
          Decoration.line({ class: "cm-current-element" }).range(line.from),
        );
        pos = line.to + 1;
      }
      lines = Decoration.set(decorations);
    }
    return lines;
  },
  provide: (field) => EditorView.decorations.from(field),
});

// Token colours from DESIGN.md §2 (code-*), measured for contrast in §7.
const highlight = HighlightStyle.define([
  { tag: tags.propertyName, color: "var(--color-code-key)" },
  { tag: tags.string, color: "var(--color-code-string)" },
  {
    tag: [tags.number, tags.bool, tags.null],
    color: "var(--color-code-number)",
  },
  {
    tag: [tags.punctuation, tags.separator, tags.brace, tags.squareBracket],
    color: "var(--color-code-punct)",
  },
]);

const theme = EditorView.theme({
  "&": { height: "100%", fontSize: "var(--text-sm)" },
  "&.cm-focused": { outline: "none" },
  ".cm-scroller": { fontFamily: "var(--font-mono)", lineHeight: "1.6" },
  ".cm-content": { caretColor: "var(--color-accent)" },
  ".cm-gutters": {
    background: "var(--color-code-gutter)",
    color: "var(--color-code-line-no)",
    border: "0",
  },
  ".cm-conf-gutter .cm-gutterElement": { width: "0.5rem" },
  ".cm-conf-low": { background: "var(--pattern-low)" },
  ".cm-conf-medium": { background: "var(--pattern-medium)" },
  ".cm-current-element": { background: "var(--color-code-current)" },
  ".cm-activeLine": { background: "transparent" },
});

/** CodeMirror 6 (ADR-0011, ADR-0027) with the confidence margin and highlighting of the current element. */
export function JsonEditor({
  ref,
  initial,
  onChange,
  confidence,
  diagnostics,
  describedBy,
}: Props) {
  const hostRef = useRef<HTMLDivElement>(null);
  const viewRef = useRef<EditorView>(null);
  const onChangeRef = useRef(onChange);
  useEffect(() => {
    onChangeRef.current = onChange;
  });

  useEffect(() => {
    let timer: ReturnType<typeof setTimeout> | undefined;
    const flush = (view: EditorView) => {
      clearTimeout(timer);
      onChangeRef.current(view.state.doc.toString());
    };
    const marks = StateField.define({
      create: (state) => confidenceMarks(state, confidence),
      update: (value, tr) =>
        tr.docChanged ? confidenceMarks(tr.state, confidence) : value,
    });
    const view = new EditorView({
      parent: hostRef.current ?? undefined,
      state: EditorState.create({
        doc: initial,
        extensions: [
          basicSetup,
          json(),
          syntaxHighlighting(highlight),
          theme,
          lintGutter(),
          marks,
          gutter({
            class: "cm-conf-gutter",
            markers: (v) => v.state.field(marks),
          }),
          currentLines,
          EditorView.contentAttributes.of({
            "aria-label": "Edytor JSON",
            "aria-describedby": describedBy,
          }),
          EditorView.updateListener.of((update) => {
            if (update.docChanged) {
              clearTimeout(timer);
              timer = setTimeout(() => flush(update.view), 300);
            }
            if (update.focusChanged && !update.view.hasFocus)
              flush(update.view);
          }),
        ],
      }),
    });
    viewRef.current = view;
    return () => {
      clearTimeout(timer);
      view.destroy();
    };
  }, [initial, confidence, describedBy]);

  useEffect(() => {
    const view = viewRef.current;
    if (!view) return;
    const end = view.state.doc.length;
    // Diagnostics come from the last checked text; clamp in case the user typed since then.
    const clamped = diagnostics.map((d) => ({
      ...d,
      from: Math.min(d.from, end),
      to: Math.min(d.to, end),
    }));
    view.dispatch(setDiagnostics(view.state, clamped));
  }, [diagnostics]);

  useImperativeHandle(ref, () => {
    const view = () => viewRef.current as EditorView;
    const goTo = (pos: number, to = pos) => {
      const v = view();
      const from = Math.min(pos, v.state.doc.length);
      v.dispatch({
        selection: { anchor: from },
        effects: [
          setCurrent.of({ from, to: Math.min(to, v.state.doc.length) }),
          EditorView.scrollIntoView(from, { y: "start", yMargin: 48 }),
        ],
      });
      v.focus();
    };
    return {
      text: () => view().state.doc.toString(),
      format() {
        const v = view();
        try {
          const insert = JSON.stringify(
            JSON.parse(v.state.doc.toString()),
            null,
            2,
          );
          v.dispatch({ changes: { from: 0, to: v.state.doc.length, insert } });
        } catch {
          // The button is disabled on a syntax error; nothing to format.
        }
      },
      reveal(path) {
        const v = view();
        const state = v.state;
        const tree =
          ensureSyntaxTree(state, state.doc.length, 200) ?? syntaxTree(state);
        const at = locate(tree, (a, b) => state.sliceDoc(a, b), path);
        if (at) goTo(at.from, at.to);
        return Boolean(at);
      },
      goTo: (pos) => goTo(pos),
    };
  }, []);

  return <div className="review-editor" ref={hostRef} />;
}
