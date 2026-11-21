export function WorkspaceErrorFallback() {
  return (
    <main role="alert">
      <h1>Something went wrong</h1>
      <p>Please reload the workspace to continue.</p>
      <button onClick={() => window.location.reload()}>Reload workspace</button>
    </main>
  );
}
