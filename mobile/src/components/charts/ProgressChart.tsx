import React from 'react';
import { View, Dimensions, StyleSheet } from 'react-native';
import { ProgressChart as ProgressChartComponent } from 'react-native-chart-kit';
import { useTheme } from '../../contexts/ThemeContext';

interface ProgressChartProps {
  data: {
    labels: string[];
    data: number[];
  };
  width?: number;
  height?: number;
  strokeWidth?: number;
  radius?: number;
  style?: any;
}

const ProgressChart: React.FC<ProgressChartProps> = ({
  data,
  width = Dimensions.get('window').width - 32,
  height = 220,
  strokeWidth = 16,
  radius = 32,
  style,
}) => {
  const { colors } = useTheme();

  const chartConfig = {
    backgroundColor: 'transparent',
    backgroundGradientFrom: 'transparent',
    backgroundGradientTo: 'transparent',
    color: (opacity = 1) => `rgba(79, 70, 229, ${opacity})`,
    labelColor: (opacity = 1) => `rgba(${colors.textSecondary.replace('#', '')}, ${opacity})`,
    style: {
      borderRadius: 16,
    },
    propsForLabels: {
      fontSize: 12,
      fontWeight: '500',
    },
  };

  return (
    <View style={[styles.container, style]}>
      <ProgressChartComponent
        data={data}
        width={width}
        height={height}
        strokeWidth={strokeWidth}
        radius={radius}
        chartConfig={chartConfig}
        hideLegend={false}
        style={{
          borderRadius: 16,
        }}
      />
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    alignItems: 'center',
  },
});

export default ProgressChart;