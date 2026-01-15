import os

# --- CONFIGURATION ---
DOMAIN = "https://tv.cricfoot.net" 
DIST_DIR = "dist"

# Ensure dist directory exists
os.makedirs(DIST_DIR, exist_ok=True)

# 404 Page HTML
ERROR_404_HTML = '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>404 - Page Not Found | TV Channels</title>
    <meta name="robots" content="noindex, nofollow">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 20px;
        }
        .error-container {
            text-align: center;
            background: white;
            padding: 60px 40px;
            border-radius: 20px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            max-width: 600px;
            width: 100%;
            animation: fadeIn 0.5s ease-in;
        }
        @keyframes fadeIn {
            from { opacity: 0; transform: translateY(20px); }
            to { opacity: 1; transform: translateY(0); }
        }
        .error-code {
            font-size: 120px;
            font-weight: 900;
            color: #2563eb;
            line-height: 1;
            margin-bottom: 20px;
            text-shadow: 2px 2px 4px rgba(0,0,0,0.1);
            animation: bounce 1s ease infinite alternate;
        }
        @keyframes bounce {
            from { transform: translateY(0px); }
            to { transform: translateY(-10px); }
        }
        h1 {
            font-size: 32px;
            color: #1e293b;
            margin-bottom: 15px;
            font-weight: 700;
        }
        p {
            font-size: 18px;
            color: #64748b;
            margin-bottom: 40px;
            line-height: 1.6;
        }
        .btn-home {
            display: inline-block;
            padding: 16px 40px;
            background: #2563eb;
            color: white;
            text-decoration: none;
            border-radius: 10px;
            font-weight: 600;
            font-size: 16px;
            transition: all 0.3s ease;
            box-shadow: 0 4px 15px rgba(37, 99, 235, 0.3);
        }
        .btn-home:hover {
            background: #1e40af;
            transform: translateY(-2px);
            box-shadow: 0 6px 20px rgba(37, 99, 235, 0.4);
        }
        .suggestions {
            margin-top: 30px;
            padding-top: 30px;
            border-top: 1px solid #e2e8f0;
        }
        .suggestions h2 {
            font-size: 18px;
            color: #475569;
            margin-bottom: 15px;
        }
        .suggestions ul {
            list-style: none;
            padding: 0;
        }
        .suggestions li {
            margin: 8px 0;
        }
        .suggestions a {
            color: #2563eb;
            text-decoration: none;
            font-size: 16px;
            transition: color 0.2s;
        }
        .suggestions a:hover {
            color: #1e40af;
            text-decoration: underline;
        }
        @media (max-width: 480px) {
            .error-code { font-size: 80px; }
            h1 { font-size: 24px; }
            p { font-size: 16px; }
            .error-container { padding: 40px 20px; }
            .btn-home { padding: 14px 30px; font-size: 14px; }
        }
    </style>
</head>
<body>
    <div class="error-container">
        <div class="error-code">404</div>
        <h1>Oops! Page Not Found</h1>
        <p>Sorry, the page you're looking for doesn't exist or has been moved. The match might have ended or the date has passed.</p>
        <a href="''' + DOMAIN + '''" class="btn-home">
            <svg style="display: inline-block; width: 16px; height: 16px; margin-right: 8px; vertical-align: middle;" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 19l-7-7m0 0l7-7m-7 7h18"></path>
            </svg>
            Back to Home
        </a>
        
        <div class="suggestions">
            <h2>You might be looking for:</h2>
            <ul>
                <li><a href="''' + DOMAIN + '''">Today's Matches</a></li>
                <li><a href="''' + DOMAIN + '''/channel/">Browse Channels</a></li>
            </ul>
        </div>
    </div>
</body>
</html>'''

# Write 404 page
output_path = os.path.join(DIST_DIR, "404.html")
with open(output_path, "w", encoding="utf-8") as f:
    f.write(ERROR_404_HTML)

print(f"✅ 404 page generated → {output_path}")
