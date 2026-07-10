import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../../../models/onboarding_data.dart';
import '../../../services/api_service.dart';
import '../../../services/auth_service.dart';
import 'crop_registration_screen.dart';

class FarmProfileScreen extends StatefulWidget {
  const FarmProfileScreen({super.key});

  @override
  State<FarmProfileScreen> createState() => _FarmProfileScreenState();
}

class _FarmProfileScreenState extends State<FarmProfileScreen> {
  final _formKey = GlobalKey<FormState>();
  final _nameController = TextEditingController();
  final _villageController = TextEditingController();
  final _districtController = TextEditingController();
  final _stateController = TextEditingController();
  final _areaController = TextEditingController();

  @override
  void dispose() {
    _nameController.dispose();
    _villageController.dispose();
    _districtController.dispose();
    _stateController.dispose();
    _areaController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final primaryColor = Theme.of(context).primaryColor;

    return Scaffold(
      appBar: AppBar(title: const Text('Setup Account')),
      body: SafeArea(
        child: SingleChildScrollView(
          padding: const EdgeInsets.symmetric(horizontal: 24.0, vertical: 16.0),
          child: Form(
            key: _formKey,
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                Row(children: [
                  Expanded(child: Container(height: 4, decoration: BoxDecoration(color: primaryColor, borderRadius: BorderRadius.circular(2)))),
                  const SizedBox(width: 8),
                  Expanded(child: Container(height: 4, decoration: BoxDecoration(color: Colors.grey.shade300, borderRadius: BorderRadius.circular(2)))),
                ]),
                const SizedBox(height: 32),
                Text('Farm Profile', style: Theme.of(context).textTheme.displayLarge?.copyWith(fontSize: 24)),
                const SizedBox(height: 8),
                Text('Enter details about your land to calibrate decision algorithms.', style: Theme.of(context).textTheme.bodyMedium),
                const SizedBox(height: 32),
                TextFormField(
                  controller: _nameController,
                  decoration: const InputDecoration(labelText: 'Farm Name', hintText: 'e.g., North Valley Field'),
                  validator: (value) => value == null || value.isEmpty ? 'Farm name is required' : null,
                ),
                const SizedBox(height: 16),
                TextFormField(
                  controller: _villageController,
                  decoration: const InputDecoration(labelText: 'Village', hintText: 'e.g., Greenfield Village'),
                ),
                const SizedBox(height: 16),
                Row(
                  children: [
                    Expanded(child: TextFormField(controller: _districtController, decoration: const InputDecoration(labelText: 'District'))),
                    const SizedBox(width: 16),
                    Expanded(child: TextFormField(controller: _stateController, decoration: const InputDecoration(labelText: 'State'))),
                  ],
                ),
                const SizedBox(height: 16),
                TextFormField(
                  controller: _areaController,
                  decoration: const InputDecoration(labelText: 'Farm Area (Acres)', hintText: 'e.g., 12.5'),
                  keyboardType: TextInputType.number,
                  validator: (value) => value == null || value.isEmpty ? 'Area is required' : null,
                ),
                const SizedBox(height: 40),
                ElevatedButton(
                  onPressed: () async {
                    if (!_formKey.currentState!.validate()) return;

                    OnboardingData.farmName = _nameController.text.trim();
                    OnboardingData.farmVillage = _villageController.text.trim();
                    OnboardingData.farmDistrict = _districtController.text.trim();
                    OnboardingData.farmState = _stateController.text.trim();
                    OnboardingData.farmArea = double.tryParse(_areaController.text);

                    // Create farm via API
                    final auth = Provider.of<AuthService>(context, listen: false);
                    final api = ApiService(auth);
                    if (auth.isAuthenticated) {
                      final farm = await api.createFarm(
                        name: OnboardingData.farmName!,
                        village: OnboardingData.farmVillage?.isNotEmpty == true ? OnboardingData.farmVillage : null,
                        district: OnboardingData.farmDistrict?.isNotEmpty == true ? OnboardingData.farmDistrict : null,
                        state: OnboardingData.farmState?.isNotEmpty == true ? OnboardingData.farmState : null,
                        area: OnboardingData.farmArea,
                      );
                      if (farm != null) OnboardingData.createdFarmId = farm.id;
                    }

                    if (mounted) {
                      Navigator.push(context, MaterialPageRoute(builder: (context) => const CropRegistrationScreen()));
                    }
                  },
                  child: const Text('Continue'),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}
