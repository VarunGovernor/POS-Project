export function LoadingPanel({ title }: { title: string }) {
  return (
    <main>
      <section className="shell panel">
        <h1>{title}</h1>
        <div className="status-grid" aria-label={`Loading ${title}`}>
          <div className="skeleton" />
          <div className="skeleton" />
          <div className="skeleton" />
        </div>
      </section>
    </main>
  );
}
