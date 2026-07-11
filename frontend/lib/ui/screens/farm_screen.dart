import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:provider/provider.dart';
import '../../models/farm.dart';
import '../../models/crop.dart';
import '../../services/api_service.dart';
import '../../services/auth_service.dart';

class FarmScreen extends StatefulWidget {
  const FarmScreen({super.key});

  @override
  State<FarmScreen> createState() => _FarmScreenState();
}

class _FarmScreenState extends State<FarmScreen> {
  List<AppFarm> _farms = [];
  List<AppCrop> _crops = [];
  bool _isLoading = true;
  AppFarm? _selectedFarm;

  @override
  void initState() {
    super.initState();
    _loadData();
  }

  Future<void> _loadData() async {
    final auth = Provider.of<AuthService>(context, listen: false);
    final api = ApiService(auth);
    final farms = await api.listFarms();
    final crops = await api.listCrops();
    if (mounted) {
      setState(() {
        _farms = farms;
        _crops = crops;
        _isLoading = false;
        if (_farms.isNotEmpty && _selectedFarm == null) {
          _selectedFarm = _farms.first;
        }
      });
    }
  }

  List<AppCrop> _cropsForFarm(int farmId) =>
      _crops.where((c) => c.farmId == farmId).toList();

  void _showAddFarmDialog() {
    final nameCtrl = TextEditingController();
    final villageCtrl = TextEditingController();
    final districtCtrl = TextEditingController();
    final stateCtrl = TextEditingController();
    final areaCtrl = TextEditingController();

    showDialog(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Add Farm'),
        content: SingleChildScrollView(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              TextField(controller: nameCtrl, decoration: const InputDecoration(labelText: 'Farm Name *')),
              const SizedBox(height: 12),
              TextField(controller: villageCtrl, decoration: const InputDecoration(labelText: 'Village')),
              const SizedBox(height: 12),
              Row(
                children: [
                  Expanded(child: TextField(controller: districtCtrl, decoration: const InputDecoration(labelText: 'District'))),
                  const SizedBox(width: 12),
                  Expanded(child: TextField(controller: stateCtrl, decoration: const InputDecoration(labelText: 'State'))),
                ],
              ),
              const SizedBox(height: 12),
              TextField(
                controller: areaCtrl,
                decoration: const InputDecoration(labelText: 'Area (Acres)', hintText: 'e.g., 10.0'),
                keyboardType: const TextInputType.numberWithOptions(decimal: true),
                inputFormatters: [FilteringTextInputFormatter.allow(RegExp(r'[0-9.]'))],
              ),
            ],
          ),
        ),
        actions: [
          TextButton(onPressed: () => Navigator.pop(ctx), child: const Text('Cancel')),
          ElevatedButton(
            onPressed: () async {
              if (nameCtrl.text.trim().isEmpty) return;
              final auth = Provider.of<AuthService>(context, listen: false);
              final api = ApiService(auth);
              final farm = await api.createFarm(
                name: nameCtrl.text.trim(),
                village: villageCtrl.text.trim().isEmpty ? null : villageCtrl.text.trim(),
                district: districtCtrl.text.trim().isEmpty ? null : districtCtrl.text.trim(),
                state: stateCtrl.text.trim().isEmpty ? null : stateCtrl.text.trim(),
                area: double.tryParse(areaCtrl.text),
              );
              if (farm != null) {
                setState(() => _farms.add(farm));
                _loadData();
              }
              if (ctx.mounted) Navigator.pop(ctx);
            },
            child: const Text('Create'),
          ),
        ],
      ),
    );
  }

  void _showAddCropDialog(int farmId) {
    final typeCtrl = TextEditingController();
    final varietyCtrl = TextEditingController();
    final sizeCtrl = TextEditingController();

    showDialog(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Add Crop'),
        content: SingleChildScrollView(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              TextField(controller: typeCtrl, decoration: const InputDecoration(labelText: 'Crop Type *', hintText: 'e.g., Rice, Wheat')),
              const SizedBox(height: 12),
              TextField(controller: varietyCtrl, decoration: const InputDecoration(labelText: 'Variety', hintText: 'e.g., Basmati')),
              const SizedBox(height: 12),
              TextField(
                controller: sizeCtrl,
                decoration: const InputDecoration(labelText: 'Field Size (Acres)', hintText: 'e.g., 2.5'),
                keyboardType: const TextInputType.numberWithOptions(decimal: true),
                inputFormatters: [FilteringTextInputFormatter.allow(RegExp(r'[0-9.]'))],
              ),
            ],
          ),
        ),
        actions: [
          TextButton(onPressed: () => Navigator.pop(ctx), child: const Text('Cancel')),
          ElevatedButton(
            onPressed: () async {
              if (typeCtrl.text.trim().isEmpty) return;
              final auth = Provider.of<AuthService>(context, listen: false);
              final api = ApiService(auth);
              final crop = await api.createCrop(
                farmId: farmId,
                cropType: typeCtrl.text.trim(),
                cropVariety: varietyCtrl.text.trim().isEmpty ? null : varietyCtrl.text.trim(),
                fieldSize: sizeCtrl.text.trim().isEmpty ? null : sizeCtrl.text.trim(),
              );
              if (crop != null) _loadData();
              if (ctx.mounted) Navigator.pop(ctx);
            },
            child: const Text('Add'),
          ),
        ],
      ),
    );
  }

  void _confirmDeleteFarm(AppFarm farm) {
    showDialog(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Delete Farm'),
        content: Text('Delete "${farm.name}" and all its crops?'),
        actions: [
          TextButton(onPressed: () => Navigator.pop(ctx), child: const Text('Cancel')),
          ElevatedButton(
            style: ElevatedButton.styleFrom(backgroundColor: const Color(0xFFD90429), foregroundColor: Colors.white),
            onPressed: () async {
              final auth = Provider.of<AuthService>(context, listen: false);
              final api = ApiService(auth);
              await api.deleteFarm(farm.id);
              setState(() {
                _farms.removeWhere((f) => f.id == farm.id);
                _crops.removeWhere((c) => c.farmId == farm.id);
                if (_selectedFarm?.id == farm.id) _selectedFarm = _farms.isNotEmpty ? _farms.first : null;
              });
              if (ctx.mounted) Navigator.pop(ctx);
            },
            child: const Text('Delete'),
          ),
        ],
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final borderLight = Colors.grey.shade200;

    return Scaffold(
      backgroundColor: Colors.white,
      appBar: AppBar(
        title: const Text('My Farms'),
        actions: [
          IconButton(
            icon: const Icon(Icons.add),
            onPressed: _showAddFarmDialog,
          ),
        ],
      ),
      body: _isLoading
          ? const Center(child: CircularProgressIndicator())
          : _farms.isEmpty
              ? Center(
                  child: Column(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      Icon(Icons.landscape, size: 80, color: Colors.grey.shade300),
                      const SizedBox(height: 16),
                      Text('No farms yet', style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold, color: Colors.grey.shade600)),
                      const SizedBox(height: 8),
                      Text('Tap + to add your first farm', style: TextStyle(color: Colors.grey.shade500)),
                    ],
                  ),
                )
              : SingleChildScrollView(
                  padding: const EdgeInsets.all(16),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      // Farm selector chips
                      SizedBox(
                        height: 40,
                        child: ListView.separated(
                          scrollDirection: Axis.horizontal,
                          itemCount: _farms.length,
                          separatorBuilder: (_, __) => const SizedBox(width: 8),
                          itemBuilder: (ctx, i) {
                            final farm = _farms[i];
                            final selected = _selectedFarm?.id == farm.id;
                            return FilterChip(
                              label: Text(farm.name),
                              selected: selected,
                              onSelected: (_) => setState(() => _selectedFarm = farm),
                              selectedColor: Theme.of(context).primaryColor,
                              labelStyle: TextStyle(
                                color: selected ? Colors.white : Colors.black,
                                fontWeight: FontWeight.w600,
                              ),
                            );
                          },
                        ),
                      ),

                      if (_selectedFarm != null) ...[
                        const SizedBox(height: 20),

                        // Farm details card
                        Container(
                          padding: const EdgeInsets.all(16),
                          decoration: BoxDecoration(
                            border: Border.all(color: borderLight),
                            borderRadius: BorderRadius.circular(8),
                          ),
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Row(
                                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                                children: [
                                  Text(
                                    _selectedFarm!.name,
                                    style: const TextStyle(fontSize: 18, fontWeight: FontWeight.bold),
                                  ),
                                  PopupMenuButton<String>(
                                    onSelected: (v) {
                                      if (v == 'delete') _confirmDeleteFarm(_selectedFarm!);
                                    },
                                    itemBuilder: (_) => [
                                      const PopupMenuItem(value: 'delete', child: Text('Delete Farm', style: TextStyle(color: Color(0xFFD90429)))),
                                    ],
                                  ),
                                ],
                              ),
                              const SizedBox(height: 8),
                              Text(
                                _selectedFarm!.locationText,
                                style: TextStyle(color: Colors.grey.shade600),
                              ),
                              if (_selectedFarm!.area != null) ...[
                                const SizedBox(height: 4),
                                Text(
                                  '${_selectedFarm!.area} ${_selectedFarm!.areaUnit}',
                                  style: TextStyle(color: Colors.grey.shade600),
                                ),
                              ],
                            ],
                          ),
                        ),

                        const SizedBox(height: 24),

                        // Crops section
                        Row(
                          mainAxisAlignment: MainAxisAlignment.spaceBetween,
                          children: [
                            Text(
                              'CROPS',
                              style: TextStyle(
                                fontSize: 11, fontWeight: FontWeight.w700,
                                color: Colors.grey.shade500, letterSpacing: 1.5,
                              ),
                            ),
                            IconButton(
                              icon: const Icon(Icons.add_circle_outline, size: 20),
                              onPressed: () => _showAddCropDialog(_selectedFarm!.id),
                            ),
                          ],
                        ),
                        const SizedBox(height: 8),

                        ..._cropsForFarm(_selectedFarm!.id).map((crop) => Container(
                              margin: const EdgeInsets.only(bottom: 8),
                              padding: const EdgeInsets.all(14),
                              decoration: BoxDecoration(
                                border: Border.all(color: borderLight),
                                borderRadius: BorderRadius.circular(8),
                              ),
                              child: Row(
                                children: [
                                  Icon(Icons.eco, color: Theme.of(context).primaryColor, size: 24),
                                  const SizedBox(width: 14),
                                  Expanded(
                                    child: Column(
                                      crossAxisAlignment: CrossAxisAlignment.start,
                                      children: [
                                        Text(crop.cropType, style: const TextStyle(fontWeight: FontWeight.w600, fontSize: 15)),
                                        if (crop.cropVariety != null && crop.cropVariety!.isNotEmpty)
                                          Text(crop.cropVariety!, style: TextStyle(color: Colors.grey.shade500, fontSize: 13)),
                                      ],
                                    ),
                                  ),
                                  if (crop.fieldSize != null)
                                    Text('${crop.fieldSize} Ac', style: TextStyle(color: Colors.grey.shade500, fontSize: 13)),
                                  const SizedBox(width: 8),
                                  PopupMenuButton<String>(
                                    onSelected: (v) async {
                                      if (v == 'delete') {
                                        final auth = Provider.of<AuthService>(context, listen: false);
                                        final api = ApiService(auth);
                                        await api.deleteCrop(crop.id);
                                        _loadData();
                                      }
                                    },
                                    itemBuilder: (_) => [
                                      const PopupMenuItem(value: 'delete', child: Text('Delete', style: TextStyle(color: Color(0xFFD90429)))),
                                    ],
                                  ),
                                ],
                              ),
                            )),

                        if (_cropsForFarm(_selectedFarm!.id).isEmpty)
                          Container(
                            padding: const EdgeInsets.all(24),
                            decoration: BoxDecoration(
                              border: Border.all(color: borderLight, style: BorderStyle.solid),
                              borderRadius: BorderRadius.circular(8),
                            ),
                            child: Center(
                              child: Text('No crops yet. Tap + to add one.', style: TextStyle(color: Colors.grey.shade500)),
                            ),
                          ),
                      ],
                    ],
                  ),
                ),
    );
  }
}
