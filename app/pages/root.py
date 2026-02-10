"""Root landing page for Timeline with onboarding and API links."""

_FONTS_CSS_URL = (
    "https://fonts.googleapis.com/css2?family=DM+Sans:ital,opsz,wght@0,9..40,400;0,9..40,500;0,9..40,600;1,9..40,400"
    "&family=JetBrains+Mono:wght@400;500&display=swap"
)


def render_root_page(app_name: str) -> str:
    """Return HTML for the root landing page."""
    return f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Timeline</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="{_FONTS_CSS_URL}" rel="stylesheet">
    <style>
        * {{ box-sizing: border-box; }}
        body {{
            font-family: 'DM Sans', system-ui, sans-serif;
            margin: 0;
            min-height: 100vh;
            background: #000;
            color: #e0e0e0;
            padding: 2rem 1rem;
        }}
        .wrap {{
            max-width: 560px;
            margin: 0 auto;
            animation: fadeIn 0.6s ease-out;
        }}
        @keyframes fadeIn {{
            from {{ opacity: 0; transform: translateY(12px); }}
            to {{ opacity: 1; transform: translateY(0); }}
        }}
        .hero {{
            text-align: center;
            margin-bottom: 3rem;
        }}
        .hero h1 {{
            font-size: clamp(2rem, 6vw, 2.75rem);
            font-weight: 600;
            letter-spacing: -0.02em;
            margin: 0 0 0.5rem 0;
            color: #fff;
        }}
        .hero .timeline-bar {{
            width: 48px;
            height: 3px;
            background: linear-gradient(90deg, #444, #888);
            margin: 1rem auto 0;
            border-radius: 0;
        }}
        .hero .tagline {{
            color: #888;
            font-size: 1rem;
            margin-top: 0.75rem;
        }}
        .card {{
            background: #0c0c0c;
            border: 1px solid #1a1a1a;
            padding: 1.5rem 1.75rem;
            margin-bottom: 1.25rem;
            border-radius: 0;
        }}
        .card h2 {{
            font-size: 0.75rem;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.08em;
            color: #666;
            margin: 0 0 1rem 0;
        }}
        .card p {{
            color: #999;
            font-size: 0.9375rem;
            line-height: 1.55;
            margin: 0 0 0.75rem 0;
        }}
        .card p:last-child {{
            margin-bottom: 0;
        }}
        .code {{
            font-family: 'JetBrains Mono', monospace;
            font-size: 0.8125rem;
            background: #111;
            color: #b0b0b0;
            padding: 0.6rem 0.85rem;
            border-radius: 0;
            margin: 0.5rem 0 1rem 0;
            border: 1px solid #1a1a1a;
            overflow-x: auto;
        }}
        .code .muted {{
            color: #555;
        }}
        .links {{
            display: flex;
            flex-wrap: wrap;
            gap: 0.75rem;
            margin-top: 1rem;
        }}
        a.btn {{
            display: inline-block;
            padding: 0.65rem 1.25rem;
            background: #222;
            color: #e0e0e0;
            text-decoration: none;
            border-radius: 0;
            font-weight: 500;
            font-size: 0.9375rem;
            border: 1px solid #333;
            transition: background 0.15s, border-color 0.15s;
        }}
        a.btn:hover {{
            background: #2a2a2a;
            border-color: #444;
        }}
        a.btn.primary {{
            background: #fff;
            color: #000;
            border-color: #fff;
        }}
        a.btn.primary:hover {{
            background: #e0e0e0;
            border-color: #e0e0e0;
        }}
        #api-base {{
            font-family: 'JetBrains Mono', monospace;
            font-size: 0.875rem;
            color: #aaa;
            word-break: break-all;
        }}
        .foot {{
            text-align: center;
            margin-top: 2.5rem;
            color: #444;
            font-size: 0.8125rem;
        }}
    </style>
</head>
<body>
    <div class="wrap">
        <header class="hero">
            <h1>Timeline</h1>
            <div class="timeline-bar" aria-hidden="true"></div>
            <p class="tagline">Event-driven API — your events, in order.</p>
        </header>

        <section class="card" aria-labelledby="new-here-heading">
            <h2 id="new-here-heading">New here?</h2>
            <p>This is the Timeline API server. Use the base URL below for all requests.
            API routes live under <code>/api/v1</code>.</p>
            <div class="code" id="api-base">—</div>
            <p>Run locally with:</p>
            <div class="code">uv run uvicorn app.main:app <span class="muted">--reload</span></div>
            <p>Copy <code>.env.example</code> to <code>.env</code> and set your database
            (Firestore or Postgres) and secrets before starting.</p>
            <div class="links">
                <a href="/docs" class="btn primary">Open API docs (Swagger)</a>
                <a href="/redoc" class="btn">ReDoc</a>
            </div>
        </section>

        <footer class="foot">
            {app_name} · API at <code>/api/v1</code>
        </footer>
    </div>
    <script>
        (function () {{
            var el = document.getElementById('api-base');
            if (el) el.textContent = window.location.origin;
        }})();
    </script>
</body>
</html>
""".strip()
