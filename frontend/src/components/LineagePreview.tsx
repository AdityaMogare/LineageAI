const NODE_WIDTH = 190
const NODE_HEIGHT = 46
const NODE_GAP = 22
const PADDING = 12
const CANVAS_WIDTH = 560

export type LineagePreviewProps = {
  modelName: string
  inputDatasets: string[]
  /** Set when DataHub write-back will run on approval. */
  showDatahubNote?: boolean
}

/**
 * A dependency-free SVG lineage graph: input tables stacked on the left,
 * the generated model on the right, and an edge per input. The height grows
 * with the number of inputs so 1-5 tables all render without clipping.
 * SVG was chosen over a graph library because the topology is always a
 * fixed two-column fan-in, which does not justify a layout-engine dependency.
 */
export function LineagePreview({
  modelName,
  inputDatasets,
  showDatahubNote = false,
}: LineagePreviewProps) {
  if (inputDatasets.length === 0) return null

  const height =
    PADDING * 2 +
    inputDatasets.length * NODE_HEIGHT +
    (inputDatasets.length - 1) * NODE_GAP
  const outputX = CANVAS_WIDTH - NODE_WIDTH - PADDING
  const outputY = height / 2 - NODE_HEIGHT / 2

  return (
    <section
      aria-label="Lineage preview"
      className="mt-6 rounded-xl border border-slate-700 bg-slate-950/60 p-4"
    >
      <p className="mb-3 font-mono text-xs uppercase tracking-wider text-cyan-300">
        Lineage
      </p>
      <svg
        className="w-full"
        preserveAspectRatio="xMidYMid meet"
        role="img"
        aria-label={`Lineage graph: ${inputDatasets.join(', ')} feed ${modelName}`}
        viewBox={`0 0 ${CANVAS_WIDTH} ${height}`}
      >
        <defs>
          <marker
            id="lineage-arrow"
            markerHeight="6"
            markerWidth="7"
            orient="auto-start-reverse"
            refX="6"
            refY="3"
          >
            <path className="fill-slate-400" d="M0,0 L7,3 L0,6 Z" />
          </marker>
        </defs>

        {inputDatasets.map((dataset, index) => {
          const y = PADDING + index * (NODE_HEIGHT + NODE_GAP)
          const edgeStartX = PADDING + NODE_WIDTH
          const edgeStartY = y + NODE_HEIGHT / 2
          const edgeEndX = outputX - 8
          const edgeEndY = outputY + NODE_HEIGHT / 2
          const controlX = (edgeStartX + edgeEndX) / 2
          return (
            <g key={dataset}>
              <path
                className="fill-none stroke-slate-500"
                d={`M ${edgeStartX} ${edgeStartY} C ${controlX} ${edgeStartY}, ${controlX} ${edgeEndY}, ${edgeEndX} ${edgeEndY}`}
                markerEnd="url(#lineage-arrow)"
                strokeWidth={1.5}
              />
              <rect
                className="fill-sky-400/10 stroke-sky-400"
                height={NODE_HEIGHT}
                rx={10}
                width={NODE_WIDTH}
                x={PADDING}
                y={y}
              />
              <text
                className="fill-sky-200 font-mono text-sm"
                dominantBaseline="central"
                textAnchor="middle"
                x={PADDING + NODE_WIDTH / 2}
                y={y + NODE_HEIGHT / 2}
              >
                {dataset}
              </text>
            </g>
          )
        })}

        <rect
          className="fill-emerald-400/10 stroke-emerald-400"
          height={NODE_HEIGHT}
          rx={10}
          width={NODE_WIDTH}
          x={outputX}
          y={outputY}
        />
        <text
          className="fill-emerald-200 font-mono text-sm"
          dominantBaseline="central"
          textAnchor="middle"
          x={outputX + NODE_WIDTH / 2}
          y={outputY + NODE_HEIGHT / 2}
        >
          {modelName || 'generated_model'}
        </text>
      </svg>
      {showDatahubNote && (
        <p className="mt-3 text-xs text-slate-400">
          On approval, this lineage is written back to DataHub with the
          agent-generated tag and pull request URL.
        </p>
      )}
    </section>
  )
}
