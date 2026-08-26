"""Onboarding and demo flow scaffolding for first-run product experience."""


class OnboardingWizard:
    def run(self):
        return [
            {"title": "Create Enterprise Space"},
            {"title": "Configure AI Provider"},
            {"title": "Create AI Employee"},
            {"title": "Upload Enterprise Knowledge"},
            {"title": "Run First Workflow"},
        ]


class DemoFlow:
    def load_demo_data(self):
        return {
            "enterprise": "LiuHao AI OS",
            "customers": ["demo-customer"],
            "suppliers": ["demo-supplier"],
            "agents": ["Research Agent"],
        }
