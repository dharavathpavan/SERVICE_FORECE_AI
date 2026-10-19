import { createBottomTabNavigator } from '@react-navigation/bottom-tabs';
import { NavigationContainer } from '@react-navigation/native';
import { Ionicons } from '@expo/vector-icons';
import React from 'react';
import { HomeScreen } from '../screens/HomeScreen';
import { AgentsScreen } from '../screens/AgentsScreen';
import { CallsScreen } from '../screens/CallsScreen';
import { ContactsScreen } from '../screens/ContactsScreen';
import { SettingsScreen } from '../screens/SettingsScreen';

const Tab = createBottomTabNavigator();

export function AppNavigator() {
  return (
    <NavigationContainer>
      <Tab.Navigator
        screenOptions={({ route }) => ({
          tabBarIcon: ({ focused, color, size }) => {
            const icons: Record<string, [string, string]> = {
              Home: ['home-outline', 'home'],
              Agents: ['hardware-chip-outline', 'hardware-chip'],
              Calls: ['call-outline', 'call'],
              Contacts: ['people-outline', 'people'],
              Settings: ['settings-outline', 'settings'],
            };
            const [outline, filled] = icons[route.name] ?? ['ellipse-outline', 'ellipse'];
            return <Ionicons name={(focused ? filled : outline) as any} size={size} color={color} />;
          },
          tabBarActiveTintColor: '#6C5CE7',
          tabBarInactiveTintColor: '#888',
          headerShown: false,
        })}
      >
        <Tab.Screen name="Home" component={HomeScreen} />
        <Tab.Screen name="Agents" component={AgentsScreen} />
        <Tab.Screen name="Calls" component={CallsScreen} />
        <Tab.Screen name="Contacts" component={ContactsScreen} />
        <Tab.Screen name="Settings" component={SettingsScreen} />
      </Tab.Navigator>
    </NavigationContainer>
  );
}
