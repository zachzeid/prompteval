import {
  Radar,
  RadarChart as RechartsRadarChart,
  PolarGrid,
  PolarAngleAxis,
  PolarRadiusAxis,
  ResponsiveContainer,
  Tooltip,
} from 'recharts';
import type { HeuristicAnalysis } from '../api/types';

interface RadarChartProps {
  analysis: HeuristicAnalysis;
}

export default function RadarChart({ analysis }: RadarChartProps) {
  const data = [
    { dimension: 'Clarity', score: analysis.clarity.score, fullMark: 100 },
    { dimension: 'Specificity', score: analysis.specificity.score, fullMark: 100 },
    { dimension: 'Structure', score: analysis.structure.score, fullMark: 100 },
    { dimension: 'Completeness', score: analysis.completeness.score, fullMark: 100 },
    { dimension: 'Output Format', score: analysis.output_format.score, fullMark: 100 },
    { dimension: 'Guardrails', score: analysis.guardrails.score, fullMark: 100 },
  ];

  return (
    <ResponsiveContainer width="100%" height={300}>
      <RechartsRadarChart data={data}>
        <PolarGrid />
        <PolarAngleAxis
          dataKey="dimension"
          tick={{ fontSize: 12, fill: '#6b7280' }}
        />
        <PolarRadiusAxis
          angle={30}
          domain={[0, 100]}
          tick={{ fontSize: 10, fill: '#9ca3af' }}
        />
        <Radar
          name="Score"
          dataKey="score"
          stroke="#3b82f6"
          fill="#3b82f6"
          fillOpacity={0.3}
          strokeWidth={2}
        />
        <Tooltip
          formatter={(value: number) => [`${value}/100`, 'Score']}
          contentStyle={{
            backgroundColor: 'white',
            border: '1px solid #e5e7eb',
            borderRadius: '8px',
            padding: '8px 12px',
          }}
        />
      </RechartsRadarChart>
    </ResponsiveContainer>
  );
}
