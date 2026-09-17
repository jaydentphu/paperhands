/** Pager dots for switching between the watchlist's tickers, same pattern
 * as the mockup's `dots` (widens and accents the active one). */
export function TickerDots({
  tickers,
  selected,
  onSelect,
}: {
  tickers: string[];
  selected: string;
  onSelect: (ticker: string) => void;
}) {
  if (tickers.length <= 1) return null;

  return (
    <div className="ticker-dots">
      {tickers.map((ticker) => (
        <button
          key={ticker}
          type="button"
          aria-label={`Show ${ticker}`}
          onClick={() => onSelect(ticker)}
          className={
            ticker === selected ? 'ticker-dots__dot ticker-dots__dot--active' : 'ticker-dots__dot'
          }
        />
      ))}
    </div>
  );
}
