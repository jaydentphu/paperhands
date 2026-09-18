/** PRD.md section 9, non-negotiable: "The dashboard labels every number
 * 'simulated, conservative fills.'" Required wherever a dollar P&L figure
 * is shown (see docs/design/STYLE_GUIDE.md's honesty-label section). */
export function SimulatedNote({ className = '' }: { className?: string }) {
  return (
    <div className={`simulated-note ${className}`.trim()}>
      Paperhands never connects to a broker. Every fill is simulated at the
      conservative side of the spread.
    </div>
  );
}
