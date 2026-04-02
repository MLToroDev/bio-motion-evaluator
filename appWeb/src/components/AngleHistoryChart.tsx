import { Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';

export function AngleHistoryChart({
  leftSeries,
  rightSeries,
}: {
  leftSeries: number[];
  rightSeries: number[];
}) {
  const n = Math.max(leftSeries.length, rightSeries.length);
  const data = Array.from({ length: n }, (_, i) => ({
    i,
    L: leftSeries[i] ?? null,
    R: rightSeries[i] ?? null,
  }));
  if (n === 0) {
    return <p className="bm-caption">Sin datos de historial aún.</p>;
  }
  return (
    <div style={{ width: '100%', height: 160 }}>
      <ResponsiveContainer>
        <LineChart data={data} margin={{ top: 4, right: 4, left: -20, bottom: 0 }}>
          <XAxis dataKey="i" hide />
          <YAxis domain={[0, 180]} width={32} tick={{ fill: '#8a9b93', fontSize: 10 }} />
          <Tooltip
            contentStyle={{ background: '#1e2421', border: '1px solid #2a302d', fontSize: 12 }}
            labelFormatter={(v) => `Muestra ${v}`}
          />
          <Line type="monotone" dataKey="L" name="Izq." stroke="#00e676" dot={false} strokeWidth={2} connectNulls />
          <Line type="monotone" dataKey="R" name="Der." stroke="#ffb300" dot={false} strokeWidth={2} connectNulls />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
