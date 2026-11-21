import { useState } from "react";
import type { FormJson } from "./form";
import { FormPreview } from "./FormPreview";
import wzorzec1 from "./fixtures/wzorzec-1.json";
import wzorzec5 from "./fixtures/wzorzec-5.json";

const forms: Record<string, FormJson> = {
  "Wzorzec 1": wzorzec1,
  "Wzorzec 5": wzorzec5,
};

// shortcut: temporary dev route with reference fixtures, replaced by the job result in #54.
export function FormPreviewDemo() {
  const [name, setName] = useState("Wzorzec 1");
  return (
    <main className="eu-demo">
      <div role="group" aria-label="Wzorzec formularza">
        {Object.keys(forms).map((n) => (
          <button
            key={n}
            type="button"
            aria-pressed={n === name}
            onClick={() => setName(n)}
          >
            {n}
          </button>
        ))}
      </div>
      <FormPreview key={name} form={forms[name]} />
    </main>
  );
}
