import os

dirs = [
    "core/theme",
    "core/constants",
    "models",
    "services",
    "ui/screens/onboarding",
    "ui/screens/dashboard",
    "ui/screens/assistant",
    "ui/widgets"
]

base_path = "d:/Agri App/frontend/lib"

for d in dirs:
    os.makedirs(os.path.join(base_path, d), exist_ok=True)

print("Frontend scaffolding complete.")
