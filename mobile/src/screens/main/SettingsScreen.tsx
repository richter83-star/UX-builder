import React from 'react';
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  TouchableOpacity,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import Icon from 'react-native-vector-icons/MaterialIcons';
import { useTheme } from '../../contexts/ThemeContext';
import { useAuth } from '../../contexts/AuthContext';

const SettingsScreen: React.FC = ({ navigation }: any) => {
  const { theme, colors } = useTheme();
  const { logout, authState } = useAuth();

  const handleLogout = async () => {
    try {
      await logout();
    } catch (error) {
      console.error('Logout error:', error);
    }
  };

  const settingsItems = [
    {
      icon: 'person',
      title: 'Profile',
      subtitle: 'Manage your profile information',
      onPress: () => navigation.navigate('ProfileSettings'),
    },
    {
      icon: 'security',
      title: 'Risk Management',
      subtitle: 'Configure risk settings and limits',
      onPress: () => navigation.navigate('RiskSettings'),
    },
    {
      icon: 'notifications',
      title: 'Notifications',
      subtitle: 'Manage notification preferences',
      onPress: () => navigation.navigate('NotificationSettings'),
    },
    {
      icon: 'palette',
      title: 'Appearance',
      subtitle: 'Theme and display settings',
      onPress: () => console.log('Appearance settings'),
    },
    {
      icon: 'info',
      title: 'About',
      subtitle: 'App version and information',
      onPress: () => navigation.navigate('About'),
    },
  ];

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
    profileSection: {
      backgroundColor: colors.surface,
      borderRadius: theme.borderRadius.lg,
      padding: theme.spacing.lg,
      marginBottom: theme.spacing.lg,
      alignItems: 'center',
    },
    profileIcon: {
      width: 80,
      height: 80,
      borderRadius: 40,
      backgroundColor: colors.primary,
      justifyContent: 'center',
      alignItems: 'center',
      marginBottom: theme.spacing.md,
    },
    profileEmail: {
      fontSize: theme.typography.h3.fontSize,
      fontWeight: theme.typography.h3.fontWeight as any,
      color: colors.text,
      marginBottom: theme.spacing.xs,
    },
    profileRisk: {
      fontSize: theme.typography.body.fontSize,
      color: colors.textSecondary,
      textTransform: 'capitalize',
    },
    settingsSection: {
      backgroundColor: colors.surface,
      borderRadius: theme.borderRadius.lg,
      marginBottom: theme.spacing.lg,
    },
    settingItem: {
      flexDirection: 'row',
      alignItems: 'center',
      padding: theme.spacing.md,
      borderBottomWidth: 1,
      borderBottomColor: colors.border,
    },
    settingItemLast: {
      borderBottomWidth: 0,
    },
    settingIcon: {
      width: 40,
      height: 40,
      borderRadius: 20,
      backgroundColor: `${colors.primary}20`,
      justifyContent: 'center',
      alignItems: 'center',
      marginRight: theme.spacing.md,
    },
    settingContent: {
      flex: 1,
    },
    settingTitle: {
      fontSize: theme.typography.body.fontSize,
      fontWeight: '600',
      color: colors.text,
      marginBottom: theme.spacing.xs,
    },
    settingSubtitle: {
      fontSize: theme.typography.caption.fontSize,
      color: colors.textSecondary,
    },
    settingArrow: {
      color: colors.textSecondary,
    },
    logoutSection: {
      backgroundColor: colors.surface,
      borderRadius: theme.borderRadius.lg,
    },
    logoutButton: {
      flexDirection: 'row',
      alignItems: 'center',
      justifyContent: 'center',
      padding: theme.spacing.md,
    },
    logoutIcon: {
      marginRight: theme.spacing.sm,
      color: colors.error,
    },
    logoutText: {
      fontSize: theme.typography.body.fontSize,
      fontWeight: '600',
      color: colors.error,
    },
  });

  return (
    <SafeAreaView style={styles.container}>
      <ScrollView style={styles.content}>
        <View style={styles.header}>
          <Text style={styles.title}>Settings</Text>
          <Text style={styles.subtitle}>Manage your app preferences</Text>
        </View>

        <View style={styles.profileSection}>
          <View style={styles.profileIcon}>
            <Icon name="person" size={40} color={colors.background} />
          </View>
          <Text style={styles.profileEmail}>{authState.user?.email}</Text>
          <Text style={styles.profileRisk}>
            {authState.user?.risk_profile} Risk Profile
          </Text>
        </View>

        <View style={styles.settingsSection}>
          {settingsItems.map((item, index) => (
            <TouchableOpacity
              key={item.title}
              style={[
                styles.settingItem,
                index === settingsItems.length - 1 && styles.settingItemLast
              ]}
              onPress={item.onPress}
            >
              <View style={styles.settingIcon}>
                <Icon name={item.icon as any} size={20} color={colors.primary} />
              </View>
              <View style={styles.settingContent}>
                <Text style={styles.settingTitle}>{item.title}</Text>
                <Text style={styles.settingSubtitle}>{item.subtitle}</Text>
              </View>
              <Icon name="chevron-right" size={20} style={styles.settingArrow} />
            </TouchableOpacity>
          ))}
        </View>

        <View style={styles.logoutSection}>
          <TouchableOpacity style={styles.logoutButton} onPress={handleLogout}>
            <Icon name="logout" size={20} style={styles.logoutIcon} />
            <Text style={styles.logoutText}>Log Out</Text>
          </TouchableOpacity>
        </View>
      </ScrollView>
    </SafeAreaView>
  );
};

export default SettingsScreen;