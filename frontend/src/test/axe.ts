import axe from "axe-core";

/** WCAG 2.1 A/AA violations on the rendered page, as "rule: selectors" lines (ADR-0033). */
export async function axeViolations() {
  const { violations } = await axe.run(document, {
    runOnly: ["wcag2a", "wcag2aa", "wcag21a", "wcag21aa", "best-practice"],
    // jsdom has no layout, so contrast is checked on the tokens by design/kontrast.py.
    rules: { "color-contrast": { enabled: false } },
  });
  return violations.map(
    (v) => `${v.id}: ${v.nodes.map((n) => n.target.join(" ")).join(", ")}`,
  );
}
