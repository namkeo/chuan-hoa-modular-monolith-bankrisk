import React, { Component, ErrorInfo, ReactNode } from "react";

interface Props {
  children: ReactNode;
}

interface State {
  hasError: boolean;
  error: Error | null;
}

export class ErrorBoundary extends Component<Props, State> {
  public state: State = {
    hasError: false,
    error: null,
  };

  public static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  public componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error("React ErrorBoundary caught an unhandled error:", error, errorInfo);
  }

  public render() {
    if (this.state.hasError) {
      return (
        <div style={{ padding: 32, display: "flex", justifyContent: "center", alignItems: "center", minHeight: "60vh" }}>
          <div className="card" style={{ maxWidth: 600, width: "100%", padding: 24, textAlign: "center" }}>
            <div style={{ fontSize: 48, marginBottom: 12 }}>⚠️</div>
            <h3 style={{ margin: "0 0 8px 0", color: "#c62828" }}>Đã xảy ra lỗi hiển thị giao diện</h3>
            <p style={{ color: "#64748b", fontSize: 14, marginBottom: 16 }}>
              {this.state.error?.message || "Không thể tải giao diện cho thành phần này."}
            </p>
            <div style={{ background: "#f8fafc", padding: 12, borderRadius: 6, textAlign: "left", fontSize: 12, fontFamily: "monospace", overflowX: "auto", marginBottom: 20 }}>
              {this.state.error?.stack || String(this.state.error)}
            </div>
            <button
              className="btn primary"
              onClick={() => {
                this.setState({ hasError: false, error: null });
                window.location.reload();
              }}
            >
              🔄 Tải lại trang (Refresh)
            </button>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}
