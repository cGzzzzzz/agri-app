# ML Model Training Guide

This document covers how to train the disease classification and severity estimation models used by AgriAI.

---

## Overview

AgriAI uses 5 ONNX models for plant disease diagnosis:

| Model | Architecture | Task | Classes |
|-------|-------------|------|---------|
| Rice_disease_model | EfficientNet-B0 + CBAM | Multi-class classification | 5 diseases |
| Tomato_disease_model | EfficientNet-B0 + CBAM | Multi-class classification | 10 diseases |
| Potato_disease_model | EfficientNet-B0 + CBAM | Multi-class classification | 3 classes |
| Pepper_disease_model | EfficientNet-B0 + CBAM | Multi-class classification | 2 classes |
| severity_estimator | EfficientNet-B0 dual-head | Regression (0-3 severity) | 4 severity levels |

All models are trained on the **PlantVillage** dataset (Kaggle) and exported to ONNX format for inference.

---

## Prerequisites

### Hardware

| Resource | Minimum | Recommended |
|----------|---------|-------------|
| RAM | 8 GB | 16+ GB |
| GPU | None (CPU training works) | NVIDIA GPU with CUDA |
| Disk | 5 GB free | 10+ GB free |

### Software

- Python 3.10+
- CUDA toolkit (if using GPU)

### Python dependencies (already in requirements.txt)

```
torch>=2.1.0
torchvision>=0.16.0
timm>=0.9.12
numpy>=1.26.0
Pillow>=10.0.0
scipy>=1.11.0
tqdm
```

Additional dependency for dataset download:

```
pip install kagglehub
```

You need a [Kaggle account](https://www.kaggle.com/account/login) and API token (`~/.kaggle/kaggle.json`) for automatic dataset download.

---

## Step 1: Prepare the Dataset

The PlantVillage dataset contains ~54,000 images of healthy and diseased plant leaves across 14 crop species. This script downloads it from Kaggle and organizes it into train/val/test splits.

```bash
cd backend

# Activate your virtual environment
python -m venv .venv
.venv\Scripts\activate          # Windows
# source .venv/bin/activate     # Linux/Mac

# Install dependencies
pip install -r requirements.txt
pip install kagglehub

# Download and prepare data
python -m app.models_ml.training.prepare_plantvillage
```

This will:
1. Download the PlantVillage dataset from Kaggle (~2 GB)
2. Download a separate rice disease dataset
3. Map Kaggle class names to our internal naming convention
4. Split data into 80% train / 10% val / 10% test
5. Save prepared data to `data/prepared/`

### Output structure

```
data/prepared/
  Rice/
    train/
      Bacterial Leaf Blight/
      Brown Spot/
      Rice Blast/
      Leaf Smut/
      Tungro/
    val/
    test/
  Tomato/
    train/
      Bacterial Spot/
      Early Blight/
      ...
    val/
    test/
  Potato/
    ...
  Pepper/
    ...
```

---

## Step 2: Train the Models

### Train all models

```bash
python -m app.models_ml.training.run_training --epochs 30 --device cuda
```

### Train a specific crop

```bash
python -m app.models_ml.training.run_training --crop Rice --epochs 30 --device cuda
```

### Train only the severity model

```bash
python -m app.models_ml.training.run_training --severity-only --epochs 30 --device cuda
```

### Skip severity training (disease classifiers only)

```bash
python -m app.models_ml.training.run_training --skip-severity --epochs 30 --device cuda
```

### CLI arguments

| Argument | Default | Description |
|----------|---------|-------------|
| `--data-dir` | `data/prepared` | Path to prepared dataset |
| `--output-dir` | `artifacts` | Where to save ONNX models |
| `--crop` | all available | Specific crop(s) to train |
| `--epochs` | 20 | Number of training epochs |
| `--batch-size` | 32 | Batch size |
| `--learning-rate` | 0.0001 | Learning rate |
| `--device` | `cpu` | `cpu` or `cuda` |
| `--severity-only` | false | Only train severity model |
| `--skip-severity` | false | Skip severity model |

---

## Step 3: Verify Output

After training completes, models are saved to `backend/artifacts/`:

```
artifacts/
  Rice_disease_model/
    1.0.0/
      model.onnx            # Trained model
      metadata.json         # Metrics, class names, config
      training_metadata.json
  Tomato_disease_model/
    1.0.0/
      model.onnx
      ...
  Potato_disease_model/
    1.0.0/
      ...
  Pepper_disease_model/
    1.0.0/
      ...
  severity_estimator/
    1.0.0/
      model.onnx
      ...
```

The backend automatically loads these ONNX models at startup via the model registry.

---

## Training Details

### Disease Classifier (DiseaseTrainer)

- **Architecture**: EfficientNet-B0 backbone with CBAM (Convolutional Block Attention Module)
- **Input**: 224x224 RGB images, normalized with ImageNet mean/std
- **Optimizer**: AdamW with weight decay 1e-5
- **Scheduler**: ReduceLROnPlateau (factor 0.5, patience 3)
- **Early stopping**: patience 5 epochs
- **Loss**: CrossEntropyLoss
- **Export**: ONNX format with dynamic batch dimension

### Severity Model (SeverityTrainer)

- **Architecture**: EfficientNet-B0 backbone with dual classification + regression heads
- **Input**: 224x224 RGB images
- **Output**: Severity level (0=none, 1=low, 2=moderate, 3=high)
- **Loss**: Combined classification loss + ordinal regression loss
- **Export**: ONNX format

### Severity Mapping

Diseases are mapped to severity levels based on agricultural impact:

| Severity | Diseases |
|----------|----------|
| High (3) | Rice Blast, Tungro, Late Blight, Yellow Leaf Curl Virus, Northern Leaf Blight, Black Rot, Gray Leaf Spot |
| Moderate (2) | Bacterial Leaf Blight, Bacterial Spot, Early Blight, Leaf Mold, Septoria Leaf Spot, Target Spot, Tomato Mosaic Virus, Common Rust, Leaf Blight, Spider Mites, Powdery Mildew |
| Low (1) | Brown Spot, Leaf Smut |
| None (0) | All Healthy classes |

---

## Supported Crops

| Crop | Diseases | Dataset Source |
|------|----------|---------------|
| Rice | Bacterial Leaf Blight, Brown Spot, Rice Blast, Leaf Smut, Tungro | Rice Leaf Disease Dataset (Kaggle) |
| Tomato | Bacterial Spot, Early Blight, Late Blight, Leaf Mold, Septoria Leaf Spot, Spider Mites, Target Spot, Yellow Leaf Curl Virus, Tomato Mosaic Virus, Healthy | PlantVillage (Kaggle) |
| Potato | Early Blight, Late Blight, Healthy | PlantVillage (Kaggle) |
| Pepper | Bacterial Spot, Healthy | PlantVillage (Kaggle) |

### Additional crops (data mapping exists but no trained models yet)

Corn, Grape, Apple, Cherry, Orange, Peach, Blueberry, Squash — class mappings are defined in `prepare_plantvillage.py` but these crops are not trained by default. To add them, ensure their PlantVillage data is available and include them in the `--crop` argument.

---

## Retraining Workflow

When retraining:

1. Delete old artifacts: `rm -rf artifacts/`
2. Prepare data (only needed once): `python -m app.models_ml.training.prepare_plantvillage`
3. Train: `python -m app.models_ml.training.run_training --epochs 30 --device cuda`
4. Verify new models in `artifacts/`
5. Rebuild Docker image if deploying: `docker-compose build backend`

---

## Troubleshooting

### "No training data found"

Run `prepare_plantvillage` first. Check that `data/prepared/` exists and contains crop subdirectories.

### "CUDA out of memory"

Reduce batch size:
```bash
python -m app.models_ml.training.run_training --batch-size 16 --device cuda
```

Or train on CPU (slower but works):
```bash
python -m app.models_ml.training.run_training --batch-size 32 --device cpu
```

### Kaggle download fails

Ensure `~/.kaggle/kaggle.json` exists and has your API credentials. Get yours at https://www.kaggle.com/settings.

### Import errors during training

Make sure all dependencies are installed:
```bash
pip install -r requirements.txt
```

The training code uses lazy imports for torch/timm so the backend can run without GPU dependencies installed.

---

## Architecture Reference

```
Input Image (224x224)
        |
  EfficientNet-B0 Backbone (pretrained on ImageNet)
        |
    CBAM Attention
        |
   ┌────┴────┐
   |         |
 Disease   Severity
 Classes    Level (0-3)
```

The disease classifier outputs a probability distribution over known diseases for a given crop. The severity model independently estimates disease severity as a 4-level ordinal scale. Both are combined by the orchestrator to produce the final diagnosis.
