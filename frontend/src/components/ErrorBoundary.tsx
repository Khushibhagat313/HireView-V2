import { Component, type ErrorInfo, type ReactNode } from "react";

/** Last line of defence: a readable page with a way out instead of a blank screen. */
export class ErrorBoundary extends Component<{ children: ReactNode }, { failed: boolean }> {
  state = { failed: false };

  static getDerivedStateFromError() {
    return { failed: true };
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    console.error("HireView crashed", error, info.componentStack);
  }

  render() {
    if (!this.state.failed) return this.props.children;
    return (
      <main className="mx-auto grid min-h-screen max-w-[480px] content-center justify-items-start gap-4 px-5 py-12">
        <span className="hand text-[18px]">Well, that's a smudge.</span>
        <h1 className="font-serif text-[30px] leading-tight font-semibold tracking-[-0.02em]">Something on this page broke.</h1>
        <p className="text-pencil">Your job description draft is saved. Reloading usually fixes it.</p>
        <button type="button" className="btn mt-2" onClick={() => window.location.reload()}>
          Reload HireView
        </button>
      </main>
    );
  }
}
