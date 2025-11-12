import React from 'react';
import { View, Dimensions } from 'react-native';
import { LineChart as LineChartComponent } from 'react-native-chart-kit';
import { useTheme } from '../../contexts/ThemeContext';

interface LineChartProps {
  data: {
    labels: string[];
    datasets: Array<{
      data: number[];
      color?: (opacity: number) => string;
      strokeWidth?: number;
    }>;
  };
  width?: number;
  height?: number;
  withDots?: boolean;
  withInnerLines?: boolean;
  withOuterLines?: boolean;
  withVerticalLines?: boolean;
  withHorizontalLines?: boolean;
  style?: any;
}

const LineChart: React.FC<LineChartProps> = ({
  data,
  width = Dimensions.get('window').width - 32,
  height = 220,
  withDots = true,
  withInnerLines = true,
  withOuterLines = true,
  withVerticalLines = true,
  withHorizontalLines = true,
  style,
}) => {
  const { colors } = useTheme();

  const chartConfig = {
    backgroundColor: 'transparent',
    backgroundGradientFrom: 'transparent',
    backgroundGradientTo: 'transparent',
    decimalPlaces: 2,
    color: (opacity = 1) => `rgba(79, 70, 229, ${opacity})`,
    labelColor: (opacity = 1) => `rgba(${colors.textSecondary.replace('#', '')}, ${opacity})`,
    style: {
      borderRadius: 16,
    },
    propsForDots: {
      r: '4',
      strokeWidth: '2',
      stroke: colors.primary,
    },
    propsForLabels: {
      fontSize: 10,
      fontWeight: '500',
    },
  };

  return (
    <View style={style}>
      <LineChartComponent
        data={data}
        width={width}
        height={height}
        chartConfig={chartConfig}
        bezier={false}
        withDots={withDots}
        withInnerLines={withInnerLines}
        withOuterLines={withOuterLines}
        withVerticalLines={withVerticalLines}
        withHorizontalLines={withHorizontalLines}
        style={{
          marginVertical: 8,
          borderRadius: 16,
        }}
      />
    </View>
  );
};

export default LineChart;