class RecommendationEngine:
    def generate(self, crop, disease, severity, weather, history):
        disease_name = disease["label"] if isinstance(disease, dict) else disease.label
        crop_name = crop["label"] if isinstance(crop, dict) else crop.label
        severity_label = severity["label"] if isinstance(severity, dict) else severity.label
        rain_probability = weather.get("precipitation_probability_percent", 0)

        urgent = severity_label in {"high", "severe"} or disease_name.lower() not in {"healthy", "none"}
        weather_constraints = []
        if rain_probability >= 60:
            weather_constraints.append("Avoid foliar spraying until the high rain window passes.")
        else:
            weather_constraints.append("Foliar treatment can be scheduled when wind is low and leaves are dry.")

        if disease_name.lower() == "healthy":
            title = f"{crop_name} crop looks healthy"
            action = "Continue monitoring and keep field sanitation records updated."
            urgency = "low"
            safety_notes = ["No chemical treatment is recommended from this scan alone."]
            next_steps = ["Re-scan if symptoms appear", "Track irrigation and fertilizer events"]
        else:
            title = f"{disease_name} risk in {crop_name}"
            urgency = "high" if urgent else "medium"
            action = (
                f"Isolate affected leaves, improve air flow, and consult a local agronomist for registered "
                f"treatment options for {disease_name}. Recheck the crop within 48 hours."
            )
            safety_notes = [
                "Follow local label directions for any pesticide or fungicide.",
                "Use protective equipment and avoid spraying before rainfall.",
            ]
            next_steps = [
                "Capture a second close-up image in daylight",
                "Check nearby plants for spread",
                "Record any treatment applied in farm history",
            ]

        history_count = len(history)
        rationale = (
            f"The engine combined crop={crop_name}, disease={disease_name}, severity={severity_label}, "
            f"rain_probability={rain_probability}%, and {history_count} historical records."
        )
        return {
            "title": title,
            "action": action,
            "urgency": urgency,
            "rationale": rationale,
            "safety_notes": safety_notes,
            "weather_constraints": weather_constraints,
            "next_steps": next_steps,
            "xai": {
                "decision_policy": "hierarchical_rules_with_model_interfaces",
                "features_used": ["crop", "disease", "severity", "weather", "history"],
                "history_records_used": history_count,
            },
        }
