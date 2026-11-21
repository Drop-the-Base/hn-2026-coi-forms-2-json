import { Component, type ReactNode } from "react";

interface Props {
  form: unknown;
  children: ReactNode;
}

// A schema-valid JSON can still lack fields the preview needs (e.g. `flow`); the editor must survive that.
export class PreviewBoundary extends Component<
  Props,
  { form: unknown; failed: boolean }
> {
  state = { form: this.props.form, failed: false };

  static getDerivedStateFromError() {
    return { failed: true };
  }

  static getDerivedStateFromProps(props: Props, state: { form: unknown }) {
    return props.form === state.form
      ? null
      : { form: props.form, failed: false };
  }

  render() {
    return this.state.failed ? (
      <div className="alert alert--warning review-alert" role="status">
        <span className="i i-alert" aria-hidden="true"></span>
        <p>
          Podglądu nie da się pokazać: w JSON-ie brakuje części, których
          potrzebuje formularz (np. <code>flow</code> albo <code>field</code>).
        </p>
      </div>
    ) : (
      this.props.children
    );
  }
}
