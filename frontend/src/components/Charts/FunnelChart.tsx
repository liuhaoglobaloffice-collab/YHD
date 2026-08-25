/**
 * FunnelChart - 销售漏斗图（赛博朋克主题）
 */

import { useEffect, useRef } from 'react';
import * as echarts from 'echarts';

interface FunnelChartProps {
  data: {
    name: string;
    value: number;
  }[];
  title?: string;
  height?: number;
}

export default function FunnelChart({ 
  data, 
  title, 
  height = 400 
}: FunnelChartProps) {
  const chartRef = useRef<HTMLDivElement>(null);
  const chartInstance = useRef<echarts.ECharts | null>(null);

  useEffect(() => {
    if (!chartRef.current) return;

    chartInstance.current = echarts.init(chartRef.current);

    // 赛博朋克漏斗渐变色
    const colors = [
      '#00f0ff',
      '#00d4ff',
      '#00b8ff',
      '#009cff',
      '#0080ff',
      '#0064ff',
    ];

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
      tooltip: {
        trigger: 'item',
        formatter: '{b}: {c} ({d}%)',
        backgroundColor: 'rgba(0, 0, 0, 0.8)',
        borderColor: '#00f0ff',
        borderWidth: 1,
        textStyle: {
          color: '#00f0ff',
        },
      },
      series: [
        {
          type: 'funnel',
          left: '10%',
          right: '10%',
          top: title ? '15%' : '5%',
          bottom: '5%',
          width: '80%',
          min: 0,
          max: Math.max(...data.map(d => d.value)),
          minSize: '0%',
          maxSize: '100%',
          sort: 'descending',
          gap: 2,
          label: {
            show: true,
            position: 'inside',
            color: '#000',
            fontSize: 12,
            formatter: '{b}: {c}',
          },
          labelLine: {
            show: false,
          },
          itemStyle: {
            borderColor: '#000',
            borderWidth: 2,
            shadowBlur: 20,
          },
          emphasis: {
            label: {
              fontSize: 14,
              fontWeight: 'bold',
            },
            itemStyle: {
              shadowBlur: 30,
            },
          },
          data: data.map((item, index) => ({
            value: item.value,
            name: item.name,
            itemStyle: {
              color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
                {
                  offset: 0,
                  color: colors[index % colors.length],
                },
                {
                  offset: 1,
                  color: `${colors[index % colors.length]}80`,
                },
              ]),
              shadowColor: colors[index % colors.length],
            },
          })),
        },
      ],
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
  }, [data, title]);

  return (
    <div 
      ref={chartRef} 
      style={{ width: '100%', height: `${height}px` }}
      className="cyberpunk-chart"
    />
  );
}
