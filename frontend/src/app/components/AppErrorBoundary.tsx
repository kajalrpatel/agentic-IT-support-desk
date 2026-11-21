import type { ReactNode } from "react";
import { ErrorBoundary } from "react-error-boundary";
import { WorkspaceErrorFallback } from "./WorkspaceErrorFallback";

/** Functional application boundary; the library implements React's lifecycle bridge. */
export function AppErrorBoundary({ children }: { children: ReactNode }) {
  return (
    <ErrorBoundary
      FallbackComponent={WorkspaceErrorFallback}
      onError={() => {
        // Never log conversation content, tokens, or component props.
        console.error("SmartDesk could not render the workspace.");
      }}
    >
      {children}
    </ErrorBoundary>
  );
}
