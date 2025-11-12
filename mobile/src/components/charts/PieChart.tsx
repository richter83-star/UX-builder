import React from 'react';
import { View, Dimensions, StyleSheet } from 'react-native';
import { PieChart as PieChartComponent } from 'react-native-chart-kit';
import { useTheme } from '../../contexts/ThemeContext';

interface PieChartProps {
  data: Array<{
    name: string;
    population: number;
    color: string;
    legendFontColor?: string;
    legendFontSize?: number;
  }>;
  width?: number;
  height?: number;
  showLegend?: boolean;
  style?: any;
}

const PieChart: React.FC<PieChartProps> = ({
  data,
  width = Dimensions.get('window').width - 32,
  height = 220,
  showLegend = true,
  style,
}) => {
  const { colors } = useTheme();

  const chartConfig = {
    color: (opacity = 1) => `rgba(255, 255, 255, ${opacity})`,
  };

  return (
    <View style={[styles.container, style]}>
      <PieChartComponent
        data={data}
        width={width}
        height={height}
        chartConfig={chartConfig}
        accessor="population"
        backgroundColor="transparent"
        paddingLeft="15"
        center={[width / 4, 0]}
        absolute
        hasLegend={showLegend}
        legendFontSize={12}
        legendFontColor={colors.textSecondary}
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

export default PieChart;