def patch():
    with open('web_app.py', 'r', encoding='utf-8') as f:
        content = f.read()

    target = '"recent_protections": list(self.closed_events[:10])'
    replacement = '"recent_protections": list(self.closed_events[:10]),\n                "be_events": dict(getattr(self, "be_events", {}))'

    content = content.replace(target, replacement, 1)

    with open('web_app.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print("be_events added to guardian get_status!")

if __name__ == '__main__':
    patch()
