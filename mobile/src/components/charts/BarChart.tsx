import React from 'react';
import { View, Dimensions } from 'react-native';
import { BarChart as BarChartComponent } from 'react-native-chart-kit';
import { useTheme } from '../../contexts/ThemeContext';

interface BarChartProps {
  data: {
    labels: string[];
    datasets: Array<{
      data: number[];
      color?: (opacity: number) => string;
    }>;
  };
  width?: number;
  height?: number;
  withInnerLines?: boolean;
  withOuterLines?: boolean;
  withVerticalLines?: boolean;
  withHorizontalLines?: boolean;
  style?: any;
}

const BarChart: React.FC<BarChartProps> = ({
  data,
  width = Dimensions.get('window').width - 32,
  height = 220,
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
    propsForLabels: {
      fontSize: 10,
      fontWeight: '500',
    },
  };

  return (
    <View style={style}>
      <BarChartComponent
        data={data}
        width={width}
        height={height}
        chartConfig={chartConfig}
        withInnerLines={withInnerLines}
        withOuterLines={withOuterLines}
        withVerticalLines={withVerticalLines}
        withHorizontalLines={withHorizontalLines}
        style={{
          marginVertical: 8,
          borderRadius: 16,
        }}
        showBarTops={false}
        fromZero={true}
      />
    </View>
  );
};

export default BarChart;