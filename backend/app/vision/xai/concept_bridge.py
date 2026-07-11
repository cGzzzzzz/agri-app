from app.vision.xai.types import AgronomicInterpretation, ModelFeature

DISEASE_KNOWLEDGE = {
    "Rice Blast": {
        "organism": "Magnaporthe oryzae",
        "stage_map": {"low": "early", "moderate": "established", "high": "severe"},
        "spread_factors": [
            "High humidity",
            "Warm temperature",
            "Dense planting",
            "Excess nitrogen",
        ],
        "visual_indicators": [
            "Spindle-shaped lesions",
            "Gray centers with brown borders",
            "Lesion clustering on leaf tips",
        ],
        "differential": ["Brown Spot", "Bacterial Blight", "Sheath Blight"],
    },
    "Brown Spot": {
        "organism": "Bipolaris oryzae",
        "stage_map": {"low": "early", "moderate": "moderate", "high": "advanced"},
        "spread_factors": ["Nutrient-deficient soil", "Poor water management", "High humidity"],
        "visual_indicators": [
            "Circular brown spots",
            "Yellow halo around lesions",
            "Spots on older leaves first",
        ],
        "differential": ["Rice Blast", "Narrow Brown Leaf Spot"],
    },
    "Bacterial Blight": {
        "organism": "Xanthomonas oryzae pv. oryzae",
        "stage_map": {"low": "localized", "moderate": "spreading", "high": "systemic"},
        "spread_factors": ["Flooding/heavy rain", "Wounds from wind/insects", "High temperature"],
        "visual_indicators": [
            "Water-soaked lesions on leaf edges",
            "Yellow-white stripes along veins",
            "Bacterial ooze droplets",
        ],
        "differential": ["Rice Blast", "Leaf Streak"],
    },
    "Sheath Blight": {
        "organism": "Rhizoctonia solani",
        "stage_map": {"low": "initial", "moderate": "spreading", "high": "severe"},
        "spread_factors": ["High humidity", "Dense canopy", "Excess nitrogen", "Standing water"],
        "visual_indicators": [
            "Irregular lesions on leaf sheath",
            "Green-gray spots",
            "Lesion spreading upward",
        ],
        "differential": ["Bacterial Panicle Blight"],
    },
    "Early Blight": {
        "organism": "Alternaria solani",
        "stage_map": {"low": "early", "moderate": "moderate", "high": "severe"},
        "spread_factors": ["Warm humid weather", "Rain splash", "Older leaves first"],
        "visual_indicators": [
            "Concentric ring spots",
            "Dark brown to black lesions",
            "Yellowing around spots",
        ],
        "differential": ["Late Blight", "Target Spot"],
    },
    "Late Blight": {
        "organism": "Phytophthora infestans",
        "stage_map": {"low": "initial", "moderate": "spreading", "high": "epidemic"},
        "spread_factors": ["Cool wet weather", "High humidity", "Rain events"],
        "visual_indicators": [
            "Water-soaked dark lesions",
            "White fuzzy growth on undersides",
            "Rapid plant death",
        ],
        "differential": ["Early Blight", "Septoria Leaf Spot"],
    },
    "Leaf Curl": {
        "organism": "Tomato Yellow Leaf Curl Virus (TYLCV)",
        "stage_map": {
            "low": "initial infection",
            "moderate": "established",
            "high": "severe stunting",
        },
        "spread_factors": [
            "Whitefly vector",
            "High temperatures",
            "New plantings near infected fields",
        ],
        "visual_indicators": [
            "Upward leaf curling",
            "Yellow leaf margins",
            "Stunted growth",
            "Flower drop",
        ],
        "differential": ["Herbicide damage", "Nutrient deficiency"],
    },
    "Healthy": {
        "organism": "N/A",
        "stage_map": {},
        "spread_factors": [],
        "visual_indicators": [
            "Uniform green coloration",
            "No visible lesions",
            "Normal leaf architecture",
        ],
        "differential": [],
    },
}


def interpret_disease(
    disease_name: str, severity_label: str, weather: dict | None = None
) -> AgronomicInterpretation:
    knowledge = DISEASE_KNOWLEDGE.get(disease_name, DISEASE_KNOWLEDGE.get("Healthy", {}))

    if not knowledge:
        return AgronomicInterpretation(disease_name=disease_name)

    stage = knowledge["stage_map"].get(severity_label, "unknown")
    spread_risk = _assess_spread_risk(severity_label, weather)

    env_factors = list(knowledge["spread_factors"])
    if weather:
        if weather.get("humidity_percent", 0) > 80:
            env_factors.append(f"High humidity ({weather.get('humidity_percent')}%)")
        if weather.get("temperature_c", 25) > 30:
            env_factors.append(f"Warm temperature ({weather.get('temperature_c')}°C)")
        if weather.get("precipitation_probability_percent", 0) > 50:
            env_factors.append(f"Rain likely ({weather.get('precipitation_probability_percent')}%)")

    urgency = _assess_urgency(severity_label, disease_name)

    return AgronomicInterpretation(
        disease_name=disease_name,
        causal_organism=knowledge.get("organism", ""),
        disease_stage=stage,
        spread_risk=spread_risk,
        environmental_factors=env_factors,
        treatment_urgency=urgency,
        key_visual_indicators=knowledge.get("visual_indicators", []),
        differential_diagnosis=knowledge.get("differential", []),
    )


def map_features_to_agronomy(
    feature_names: list[str],
    activation_strengths: list[float],
) -> list[ModelFeature]:
    mapping = {
        "necrotic_lesion": "Dead tissue indicating fungal infection",
        "necrotic_spindle_pattern": "Spindle-shaped necrosis characteristic of Rice Blast",
        "brown_spot_pattern": "Circular brown lesions indicating Brown Spot disease",
        "gray_center": "Aged necrotic tissue, common in advanced lesions",
        "brown_margin": "Dark border around lesion indicating active pathogen spread",
        "chlorotic_halo": "Yellowing around lesion indicating pathogen toxins",
        "bacterial_ooze": "Wet lesions indicating bacterial infection",
        "leaf_tip": "Lesion concentration at leaf tip, common entry point for pathogens",
        "leaf_edge": "Edge lesions indicating water-borne or wind-borne spread",
        "green_healthy": "Normal chlorophyll content indicating healthy tissue",
        "texture_edge": "High edge density indicating lesion boundaries",
        "color_degradation": "Loss of green color indicating tissue damage",
    }

    features = []
    for name, strength in zip(feature_names, activation_strengths, strict=False):
        agronomic = mapping.get(name, f"Model feature: {name}")
        spatial = _infer_spatial_location(name)
        features.append(
            ModelFeature(
                feature_name=name,
                activation_strength=strength,
                spatial_location=spatial,
                agronomic_mapping=agronomic,
            )
        )

    return features


def _assess_spread_risk(severity: str, weather: dict | None) -> str:
    base_risk = {"low": "low", "moderate": "moderate", "high": "high", "none": "none"}.get(
        severity, "unknown"
    )
    if weather:
        humidity = weather.get("humidity_percent", 50)
        rain_prob = weather.get("precipitation_probability_percent", 30)
        if humidity > 85 and rain_prob > 60:
            return "very_high"
        if humidity > 75 or rain_prob > 50:
            return "high" if base_risk in ("moderate", "high") else "moderate"
    return base_risk


def _assess_urgency(severity: str, disease: str) -> str:
    if disease.lower() == "healthy":
        return "none"
    urgency_map = {
        "high": "immediate",
        "moderate": "within_48h",
        "low": "within_week",
        "none": "monitor",
    }
    return urgency_map.get(severity, "unknown")


def _infer_spatial_location(feature_name: str) -> str:
    if "tip" in feature_name:
        return "leaf_tip"
    if "edge" in feature_name:
        return "leaf_margin"
    if "center" in feature_name:
        return "lesion_center"
    if "margin" in feature_name:
        return "lesion_edge"
    return "general"
