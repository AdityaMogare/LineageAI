function App() {
  return (
    <main className="mx-auto flex min-h-screen max-w-5xl items-center px-6 py-16">
      <section className="max-w-3xl">
        <p className="mb-4 font-mono text-sm uppercase tracking-[0.3em] text-cyan-300">
          Metadata-aware development
        </p>
        <h1 className="text-5xl font-semibold tracking-tight text-white md:text-7xl">
          Build dbt models with lineage, not guesses.
        </h1>
        <p className="mt-6 max-w-2xl text-lg leading-8 text-slate-300">
          LineageAI grounds Kimi K3 in DataHub metadata, validates generated SQL
          against DuckDB, and pauses before publishing a reviewed pull request.
        </p>
        <div className="mt-10 rounded-2xl border border-slate-700 bg-slate-900/70 p-6">
          <p className="text-sm text-slate-400">Agent workspace coming online</p>
          <div className="mt-4 h-2 overflow-hidden rounded-full bg-slate-800">
            <div className="h-full w-1/3 rounded-full bg-cyan-400" />
          </div>
        </div>
      </section>
    </main>
  )
}

export default App
