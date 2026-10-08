import { Component } from "react";

/** Catches a crash inside any page so the whole app does not turn into a blank screen. */
export default class ErrorBoundary extends Component {
  state = { failed: false };

  static getDerivedStateFromError() {
    return { failed: true };
  }

  componentDidCatch(error) {
    console.error("Page crashed:", error);
  }

  render() {
    if (!this.state.failed) return this.props.children;
    return (
      <div className="pl-fallback">
        <h2>Something went wrong on this page</h2>
        <p>The rest of the app is fine. You can try again or go back to the dashboard.</p>
        <div className="pl-actions">
          <button className="pl-btn" onClick={() => this.setState({ failed: false })}>Try again</button>
          <a className="pl-btn pl-ghost" href="/">Go to dashboard</a>
        </div>
      </div>
    );
  }
}