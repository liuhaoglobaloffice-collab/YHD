/**
 * RadarChart - 雷达图组件（赛博朋克主题）
 */

import { useEffect, useRef } from 'react';
import * as echarts from 'echarts';

interface RadarChartProps {
  data: {
    name: string;
    value: number[];
  }[];
  indicators: {
    name: string;
    max: number;
  }[];
  title?: string;
  height?: number;
}

export default function RadarChart({ 
  data, 
  indicators, 
  title, 
  height = 400 
}: RadarChartProps) {
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
      tooltip: {
        trigger: 'item',
        backgroundColor: 'rgba(0, 0, 0, 0.8)',
        borderColor: '#00f0ff',
        borderWidth: 1,
        textStyle: {
          color: '#00f0ff',
        },
      },
      legend: {
        bottom: 10,
        textStyle: {
          color: '#00f0ff',
        },
        data: data.map(d => d.name),
      },
      radar: {
        indicator: indicators,
        center: ['50%', '50%'],
        radius: '60%',
        axisName: {
          color: '#00f0ff',
          fontSize: 11,
        },
        splitArea: {
          areaStyle: {
            color: [
              'rgba(0, 240, 255, 0.05)',
              'rgba(0, 240, 255, 0.1)',
              'rgba(0, 240, 255, 0.05)',
              'rgba(0, 240, 255, 0.1)',
            ],
          },
        },
        axisLine: {
          lineStyle: {
            color: 'rgba(0, 240, 255, 0.3)',
          },
        },
        splitLine: {
          lineStyle: {
            color: 'rgba(0, 240, 255, 0.3)',
          },
        },
      },
      series: [
        {
          type: 'radar',
          emphasis: {
            lineStyle: {
              width: 4,
            },
          },
          data: data.map((item, index) => ({
            value: item.value,
            name: item.name,
            itemStyle: {
              color: index === 0 ? '#00f0ff' : '#ff00ff',
            },
            areaStyle: {
              color: index === 0 ? 'rgba(0, 240, 255, 0.3)' : 'rgba(255, 0, 255, 0.3)',
            },
            lineStyle: {
              color: index === 0 ? '#00f0ff' : '#ff00ff',
              width: 2,
              shadowColor: index === 0 ? '#00f0ff' : '#ff00ff',
              shadowBlur: 10,
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
  }, [data, indicators, title]);

  return (
    <div 
      ref={chartRef} 
      style={{ width: '100%', height: `${height}px` }}
      className="cyberpunk-chart"
    />
  );
}
