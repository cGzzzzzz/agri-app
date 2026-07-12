import 'package:flutter/material.dart';
import 'package:geolocator/geolocator.dart';

class LocationResult {
  final Position? position;
  final bool gpsEnabled;
  final LocationPermission permission;

  const LocationResult({this.position, required this.gpsEnabled, required this.permission});

  bool get hasLocation => position != null;
}

class LocationService {
  static Future<LocationResult> getResult() async {
    bool serviceEnabled = await Geolocator.isLocationServiceEnabled();
    if (!serviceEnabled) {
      return const LocationResult(gpsEnabled: false, permission: LocationPermission.denied);
    }

    LocationPermission permission = await Geolocator.checkPermission();
    if (permission == LocationPermission.denied) {
      permission = await Geolocator.requestPermission();
      if (permission == LocationPermission.denied) {
        return const LocationResult(gpsEnabled: true, permission: LocationPermission.denied);
      }
    }

    if (permission == LocationPermission.deniedForever) {
      return const LocationResult(gpsEnabled: true, permission: LocationPermission.deniedForever);
    }

    try {
      final position = await Geolocator.getCurrentPosition(
        locationSettings: const LocationSettings(
          accuracy: LocationAccuracy.low,
          timeLimit: Duration(seconds: 10),
        ),
      );
      return LocationResult(position: position, gpsEnabled: true, permission: permission);
    } catch (e) {
      return LocationResult(gpsEnabled: true, permission: permission);
    }
  }

  static Future<Position?> getCurrentLocation() async {
    final result = await getResult();
    return result.position;
  }

  static Future<void> showLocationDisabledDialog(BuildContext context, {VoidCallback? onRetry}) async {
    return showDialog(
      context: context,
      barrierDismissible: false,
      builder: (ctx) => AlertDialog(
        icon: Icon(Icons.location_off_outlined, size: 48, color: Colors.orange.shade700),
        title: const Text('Location Disabled'),
        content: const Text(
          'Location services are turned off. AgriAI needs your location to provide accurate weather data and farm advisories.',
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(ctx),
            child: const Text('Cancel'),
          ),
          ElevatedButton.icon(
            icon: const Icon(Icons.settings, size: 18),
            label: const Text('Enable Location'),
            onPressed: () async {
              Navigator.pop(ctx);
              await Geolocator.openLocationSettings();
              if (context.mounted && onRetry != null) {
                Future.delayed(const Duration(seconds: 2), onRetry);
              }
            },
          ),
        ],
      ),
    );
  }

  static Future<void> showPermissionDeniedForeverDialog(BuildContext context) async {
    return showDialog(
      context: context,
      barrierDismissible: false,
      builder: (ctx) => AlertDialog(
        icon: Icon(Icons.location_disabled, size: 48, color: Colors.red.shade400),
        title: const Text('Permission Denied'),
        content: const Text(
          'Location permission was permanently denied. Please enable it in app settings.',
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(ctx),
            child: const Text('Cancel'),
          ),
          ElevatedButton.icon(
            icon: const Icon(Icons.open_in_new, size: 18),
            label: const Text('Open Settings'),
            onPressed: () {
              Navigator.pop(ctx);
              Geolocator.openAppSettings();
            },
          ),
        ],
      ),
    );
  }
}
