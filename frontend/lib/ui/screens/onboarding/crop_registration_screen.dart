import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../../../models/onboarding_data.dart';
import '../../../services/api_service.dart';
import '../../../services/auth_service.dart';
import '../main_navigation.dart';

class CropRegistrationScreen extends StatefulWidget {
  const CropRegistrationScreen({super.key});

  @override
  State<CropRegistrationScreen> createState() => _CropRegistrationScreenState();
}

class _CropRegistrationScreenState extends State<CropRegistrationScreen> {
  final _formKey = GlobalKey<FormState>();

  final List<String> cropTypes = ['Rice', 'Wheat', 'Maize', 'Cotton', 'Sugarcane'];
  String? selectedCrop;
  DateTime? selectedDate;
  final _varietyController = TextEditingController();
  final _fieldSizeController = TextEditingController();

  @override
  void dispose() {
    _varietyController.dispose();
    _fieldSizeController.dispose();
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
                  Expanded(child: Container(height: 4, decoration: BoxDecoration(color: primaryColor, borderRadius: BorderRadius.circular(2)))),
                ]),
                const SizedBox(height: 32),
                Text('Register Crop', style: Theme.of(context).textTheme.displayLarge?.copyWith(fontSize: 24)),
                const SizedBox(height: 8),
                Text('Select the crop currently cultivated in your field.', style: Theme.of(context).textTheme.bodyMedium),
                const SizedBox(height: 32),
                DropdownButtonFormField<String>(
                  decoration: const InputDecoration(labelText: 'Crop Type'),
                  initialValue: selectedCrop,
                  items: cropTypes.map((crop) => DropdownMenuItem(value: crop, child: Text(crop))).toList(),
                  onChanged: (val) => setState(() => selectedCrop = val),
                  validator: (value) => value == null ? 'Crop selection is required' : null,
                ),
                const SizedBox(height: 16),
                TextFormField(
                  controller: _varietyController,
                  decoration: const InputDecoration(labelText: 'Crop Variety', hintText: 'e.g., Basmati Rice'),
                ),
                const SizedBox(height: 16),
                TextFormField(
                  decoration: InputDecoration(
                    labelText: 'Sowing Date',
                    hintText: selectedDate == null ? 'Select date' : '${selectedDate!.day}/${selectedDate!.month}/${selectedDate!.year}',
                  ),
                  readOnly: true,
                  onTap: () async {
                    final date = await showDatePicker(
                      context: context,
                      initialDate: DateTime.now(),
                      firstDate: DateTime(2020),
                      lastDate: DateTime.now(),
                    );
                    if (date != null) setState(() => selectedDate = date);
                  },
                ),
                const SizedBox(height: 16),
                TextFormField(
                  controller: _fieldSizeController,
                  decoration: const InputDecoration(labelText: 'Field Size (Acres)', hintText: 'e.g., 5.0'),
                  keyboardType: TextInputType.number,
                ),
                const SizedBox(height: 40),
                Builder(
                  builder: (context) {
                    final auth = Provider.of<AuthService>(context, listen: false);
                    final onboarding = context.read<OnboardingData>();
                    final api = ApiService(auth);
                    return ElevatedButton(
                      onPressed: () async {
                        if (!_formKey.currentState!.validate()) return;
                        if (auth.isAuthenticated && onboarding.createdFarmId != null) {
                          await api.createCrop(
                            farmId: onboarding.createdFarmId!,
                            cropType: selectedCrop!,
                            cropVariety: _varietyController.text.trim().isEmpty ? null : _varietyController.text.trim(),
                            sowingDate: selectedDate != null ? '${selectedDate!.year}-${selectedDate!.month.toString().padLeft(2, '0')}-${selectedDate!.day.toString().padLeft(2, '0')}' : null,
                            fieldSize: _fieldSizeController.text.trim().isEmpty ? null : _fieldSizeController.text.trim(),
                          );
                        }
                        if (!context.mounted) return;
                        onboarding.reset();
                        Navigator.of(context).pushAndRemoveUntil(
                          MaterialPageRoute(builder: (context) => const MainNavigation()),
                          (route) => false,
                        );
                      },
                      child: const Text('Complete Onboarding'),
                    );
                  },
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}
