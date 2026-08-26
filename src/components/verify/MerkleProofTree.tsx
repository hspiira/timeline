import type { components } from '@/lib/timeline-api'

type MerkleProofResponse = components['schemas']['MerkleProofResponse']

const NODE_R = 24
const GAP = 40
const LABEL_GAP = 8

function truncate(s: string, n = 10) {
  return s.length <= n ? s : `${s.slice(0, n)}…`
}

interface MerkleProofTreeProps {
  proof: MerkleProofResponse
  className?: string
}

/**
 * Renders an interactive SVG view of the Merkle proof path: root (blue), path nodes (amber), leaf (green) with "YOU ARE HERE".
 */
export function MerkleProofTree({ proof, className }: MerkleProofTreeProps) {
  const { leaf_hash, root_hash, steps } = proof
  const pathCount = steps.length
  const totalNodes = 1 + pathCount + 1 // leaf + path nodes + root
  const width = 200
  const height = totalNodes * (NODE_R * 2 + GAP) - GAP + LABEL_GAP * 4

  const nodeY = (i: number) => NODE_R + LABEL_GAP + i * (NODE_R * 2 + GAP)
  const cx = width / 2

  return (
    <div className={className}>
      <h3 className="text-sm font-semibold text-foreground mb-2">Proof path (tree)</h3>
      <svg
        viewBox={`0 0 ${width} ${height}`}
        role="img"
        className="w-full max-w-md h-auto block"
        aria-label="Merkle proof path from leaf to root"
      >
        {/* Root */}
        <g>
          <circle
            cx={cx}
            cy={nodeY(0)}
            r={NODE_R}
            className="fill-primary/20 stroke-primary stroke-2"
          />
          <text
            x={cx}
            y={nodeY(0) + 5}
            textAnchor="middle"
            className="text-[10px] font-medium fill-primary"
          >
            Root
          </text>
          <text
            x={cx}
            y={nodeY(0) + NODE_R + LABEL_GAP}
            textAnchor="middle"
            className="text-[9px] font-mono fill-muted-foreground"
          >
            {truncate(root_hash, 12)}
          </text>
        </g>

        {/* Path nodes */}
        {steps.map((step, i) => {
          const y = nodeY(i + 1)
          return (
            <g key={i}>
              <line
                x1={cx}
                y1={nodeY(i) + NODE_R}
                x2={cx}
                y2={y - NODE_R}
                className="stroke-border stroke-[2]"
              />
              <circle
                cx={cx}
                cy={y}
                r={NODE_R}
                className="fill-status-warn/20 stroke-status-warn stroke-2"
              />
              <text
                x={cx}
                y={y + 5}
                textAnchor="middle"
                className="text-[10px] font-medium fill-status-warn"
              >
                Path
              </text>
              <text
                x={cx}
                y={y + NODE_R + LABEL_GAP}
                textAnchor="middle"
                className="text-[9px] font-mono fill-muted-foreground"
              >
                {truncate(step.sibling_hash, 12)}
              </text>
            </g>
          )
        })}

        {/* Line from last path node (or root) to leaf */}
        <line
          x1={cx}
          y1={pathCount > 0 ? nodeY(pathCount) + NODE_R : nodeY(0) + NODE_R}
          x2={cx}
          y2={nodeY(pathCount + 1) - NODE_R}
          className="stroke-border stroke-[2]"
        />
        <g>
          <circle
            cx={cx}
            cy={nodeY(pathCount + 1)}
            r={NODE_R}
            className="fill-status-ok/20 stroke-status-ok stroke-2"
          />
          <text
            x={cx}
            y={nodeY(pathCount + 1) - 2}
            textAnchor="middle"
            className="text-[9px] font-medium fill-status-ok"
          >
            YOU ARE
          </text>
          <text
            x={cx}
            y={nodeY(pathCount + 1) + 6}
            textAnchor="middle"
            className="text-[9px] font-medium fill-status-ok"
          >
            HERE
          </text>
          <text
            x={cx}
            y={nodeY(pathCount + 1) + NODE_R + LABEL_GAP}
            textAnchor="middle"
            className="text-[9px] font-mono fill-muted-foreground"
          >
            {truncate(leaf_hash, 12)}
          </text>
        </g>
      </svg>
    </div>
  )
}
