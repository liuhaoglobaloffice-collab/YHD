/**
 * LineChart - 趋势线图组件（赛博朋克主题）
 */

import { useEffect, useRef } from 'react';
import * as echarts from 'echarts';

interface LineChartProps {
  data: {
    labels: string[];
    values: number[];
  };
  title?: string;
  color?: string;
  height?: number;
}

export default function LineChart({ 
  data, 
  title, 
  color = '#00f0ff', 
  height = 300 
}: LineChartProps) {
  const chartRef = useRef<HTMLDivElement>(null);
  const chartInstance = useRef<echarts.ECharts | null>(null);

  useEffect(() => {
    if (!chartRef.current) return;

    // 初始化图表
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
        left: '10%',
        right: '10%',
        bottom: '15%',
        top: title ? '20%' : '10%',
        containLabel: true,
      },
      xAxis: {
        type: 'category',
        data: data.labels,
        axisLine: {
          lineStyle: {
            color: 'rgba(0, 240, 255, 0.3)',
          },
        },
        axisLabel: {
          color: 'rgba(0, 240, 255, 0.8)',
          fontSize: 10,
        },
        splitLine: {
          show: false,
        },
      },
      yAxis: {
        type: 'value',
        axisLine: {
          show: false,
        },
        axisLabel: {
          color: 'rgba(0, 240, 255, 0.8)',
          fontSize: 10,
        },
        splitLine: {
          lineStyle: {
            color: 'rgba(0, 240, 255, 0.1)',
            type: 'dashed',
          },
        },
      },
      series: [
        {
          data: data.values,
          type: 'line',
          smooth: true,
          symbol: 'circle',
          symbolSize: 6,
          lineStyle: {
            color: color,
            width: 2,
            shadowColor: color,
            shadowBlur: 10,
          },
          itemStyle: {
            color: color,
            borderColor: color,
            borderWidth: 2,
            shadowColor: color,
            shadowBlur: 10,
          },
          areaStyle: {
            color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
              {
                offset: 0,
                color: `${color}40`,
              },
              {
                offset: 1,
                color: `${color}05`,
              },
            ]),
          },
        },
      ],
      tooltip: {
        trigger: 'axis',
        backgroundColor: 'rgba(0, 0, 0, 0.8)',
        borderColor: color,
        borderWidth: 1,
        textStyle: {
          color: '#00f0ff',
        },
      },
    };

    chartInstance.current.setOption(option);

    // 响应式调整
    const handleResize = () => {
      chartInstance.current?.resize();
    };
    window.addEventListener('resize', handleResize);

    return () => {
      window.removeEventListener('resize', handleResize);
      chartInstance.current?.dispose();
    };
  }, [data, title, color]);

  return (
    <div 
      ref={chartRef} 
      style={{ width: '100%', height: `${height}px` }}
      className="cyberpunk-chart"
    />
  );
}
