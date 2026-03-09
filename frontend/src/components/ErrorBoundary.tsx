import React from "react";

function isDevelopment(): boolean {
  return false;
}

export class ErrorBoundary extends React.Component {
  constructor(props: any) {
    super(props);
    this.state = { hasError: false, error: null };
    this.reset = this.reset.bind(this);
  }

  static getDerivedStateFromError(error: Error): any {
    return { hasError: true, error: error };
  }

  componentDidCatch(error: Error, errorInfo: React.ErrorInfo): void {
    if ((this.props as any).onError) {
      (this.props as any).onError(error, errorInfo);
    }
    if (isDevelopment()) {
      console.error(error, errorInfo);
    }
  }

  reset(): void {
    this.setState({ hasError: false, error: null });
  }
  render(): any {
    const props = this.props as any;
    const state = this.state as any;
    if (!state.hasError) {
      return props.children;
    }
    if (props.fallback) {
      return props.fallback;
    }
    let details = null;
    if (isDevelopment()) {
      if (state.error) {
        details = React.createElement("pre", { style: { whiteSpace: "pre-wrap", marginTop: 12 } }, state.error.message);
      }
    }
    return React.createElement(
      "div",
      { role: "alert", style: { padding: 24, borderRadius: 8, background: "#fff5f0", color: "#7a271a" } },
      React.createElement("h2", null, "Something went wrong"),
      React.createElement("p", null, "The page hit an unexpected error. You can try again."),
      React.createElement("button", { type: "button", onClick: this.reset }, "Retry"),
      details
    );
  }
}

export default ErrorBoundary;
