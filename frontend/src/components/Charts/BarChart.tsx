/**
 * BarChart - 柱状图组件（赛博朋克主题）
 */

import { useEffect, useRef } from 'react';
import * as echarts from 'echarts';

interface BarChartProps {
  data: {
    labels: string[];
    values: number[];
  };
  title?: string;
  color?: string;
  height?: number;
  horizontal?: boolean;
}

export default function BarChart({ 
  data, 
  title, 
  color = '#ff00ff', 
  height = 300,
  horizontal = false,
}: BarChartProps) {
  const chartRef = useRef<HTMLDivElement>(null);
  const chartInstance = useRef<echarts.ECharts | null>(null);

  useEffect(() => {
    if (!chartRef.current) return;

    chartInstance.current = echarts.init(chartRef.current);

    const option: echarts.EChartsOption = {
      title: title ? {
        text: title,
        textStyle: {
          color: '#00f0ff',
          fontSize: 14,
          fontWeight: 'normal',
        },
        left: 'center',
        top: 10,
      } : undefined,
      grid: {
        left: horizontal ? '20%' : '10%',
        right: '10%',
        bottom: '15%',
        top: title ? '20%' : '10%',
        containLabel: true,
      },
      xAxis: {
        type: horizontal ? 'value' : 'category',
        data: horizontal ? undefined : data.labels,
        axisLine: {
          lineStyle: {
            color: 'rgba(255, 0, 255, 0.3)',
          },
        },
        axisLabel: {
          color: 'rgba(255, 0, 255, 0.8)',
          fontSize: 10,
        },
        splitLine: {
          show: horizontal,
          lineStyle: {
            color: 'rgba(255, 0, 255, 0.1)',
            type: 'dashed',
          },
        },
      },
      yAxis: {
        type: horizontal ? 'category' : 'value',
        data: horizontal ? data.labels : undefined,
        axisLine: {
          show: horizontal,
          lineStyle: {
            color: 'rgba(255, 0, 255, 0.3)',
          },
        },
        axisLabel: {
          color: 'rgba(255, 0, 255, 0.8)',
          fontSize: 10,
        },
        splitLine: {
          show: !horizontal,
          lineStyle: {
            color: 'rgba(255, 0, 255, 0.1)',
            type: 'dashed',
          },
        },
      },
      series: [
        {
          data: data.values,
          type: 'bar',
          itemStyle: {
            color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
              {
                offset: 0,
                color: color,
              },
              {
                offset: 1,
                color: `${color}80`,
              },
            ]),
            borderColor: color,
            borderWidth: 1,
            shadowColor: color,
            shadowBlur: 15,
          },
          barWidth: '60%',
        },
      ],
      tooltip: {
        trigger: 'axis',
        backgroundColor: 'rgba(0, 0, 0, 0.8)',
        borderColor: color,
        borderWidth: 1,
        textStyle: {
          color: '#ff00ff',
        },
        axisPointer: {
          type: 'shadow',
          shadowStyle: {
            color: `${color}20`,
          },
        },
      },
    };

    chartInstance.current.setOption(option);

    const handleResize = () => {
      chartInstance.current?.resize();
    };
    window.addEventListener('resize', handleResize);

    return () => {
      window.removeEventListener('resize', handleResize);
      chartInstance.current?.dispose();
    };
  }, [data, title, color, horizontal]);

  return (
    <div 
      ref={chartRef} 
      style={{ width: '100%', height: `${height}px` }}
      className="cyberpunk-chart"
    />
  );
}
