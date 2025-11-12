import React from 'react';
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import Icon from 'react-native-vector-icons/MaterialIcons';
import { useTheme } from '../../contexts/ThemeContext';

const ProfileSettingsScreen: React.FC = () => {
  const { theme, colors } = useTheme();

  const styles = StyleSheet.create({
    container: {
      flex: 1,
      backgroundColor: colors.background,
    },
    content: {
      flex: 1,
      padding: theme.spacing.lg,
    },
    header: {
      marginBottom: theme.spacing.lg,
    },
    title: {
      fontSize: theme.typography.h2.fontSize,
      fontWeight: theme.typography.h2.fontWeight as any,
      color: colors.text,
      marginBottom: theme.spacing.sm,
    },
    subtitle: {
      fontSize: theme.typography.body.fontSize,
      color: colors.textSecondary,
    },
    placeholder: {
      flex: 1,
      justifyContent: 'center',
      alignItems: 'center',
    },
    placeholderIcon: {
      marginBottom: theme.spacing.md,
    },
    placeholderText: {
      fontSize: theme.typography.body.fontSize,
      color: colors.textSecondary,
      textAlign: 'center',
    },
  });

  return (
    <SafeAreaView style={styles.container}>
      <ScrollView style={styles.content}>
        <View style={styles.header}>
          <Text style={styles.title}>Profile Settings</Text>
          <Text style={styles.subtitle}>Manage your profile information</Text>
        </View>

        <View style={styles.placeholder}>
          <Icon name="person" size={64} color={colors.textSecondary} style={styles.placeholderIcon} />
          <Text style={styles.placeholderText}>
            Profile settings implementation coming soon...
          </Text>
        </View>
      </ScrollView>
    </SafeAreaView>
  );
};

export default ProfileSettingsScreen;