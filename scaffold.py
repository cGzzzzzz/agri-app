import os

modules = [
    "auth", "users", "farms", "crops", "weather", "ai",
    "vision", "rag", "recommendations", "analytics", "notifications", "common"
]

base_path = "d:/Agri App/backend"

for module in modules:
    module_path = os.path.join(base_path, module)
    os.makedirs(module_path, exist_ok=True)
    init_file = os.path.join(module_path, "__init__.py")
    with open(init_file, "w") as f:
        f.write("# {} module\n".format(module))

print("Backend scaffolding complete.")
