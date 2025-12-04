"""
Single-file, dependency-free Milk Supply Prediction & Route Optimization demo.

Save as app_no_flask.py and run:
    python app_no_flask.py

Open http://127.0.0.1:8000
"""
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import parse_qs
import html
import sys

HOST = "127.0.0.1"
PORT = 8000

HTML_TEMPLATE = """<!doctype html>
<html>
  <head>
    <meta charset="utf-8" />
    <title>Milk Supply Prediction & Route Optimization (No deps)</title>
    <style>
      body {{ font-family: Arial, sans-serif; max-width: 900px; margin: 24px; }}
      label {{ display:block; margin-top:12px; font-weight:600; }}
      input[type=text], textarea {{ width:100%; padding:8px; box-sizing:border-box; }}
      .btn {{ margin-top:12px; padding:10px 16px; background:#0d6efd; color:white; border:none; cursor:pointer; }}
      .alert {{ padding:10px; background:#f8d7da; color:#842029; margin-top:12px; }}
      .success {{ padding:10px; background:#d1e7dd; color:#0f5132; margin-top:12px; }}
      .list {{ margin-top:8px; }}
    </style>
  </head>
  <body>
    <h2>Milk Supply Prediction & Route Optimization (No dependencies)</h2>
    <p style="color:#555">Minimal demo — enter values and press Generate.</p>

    {messages}

    <form method="post" action="/">
      <label>Village Names (comma separated)</label>
      <input name="villages" placeholder="Village A, Village B, Village C" value="{villages}">

      <label>Milk Collected Yesterday (comma separated, liters)</label>
      <input name="milk_data" placeholder="120, 80, 95" value="{milk_data}">
      <small>Provide one value per village or a single value to broadcast to all.</small>

      <label>Optional: Distances (comma separated, km)</label>
      <input name="distances" placeholder="5, 8, 3" value="{distances}">
      <small>If provided, must match number of villages; interpreted as leg distances in the given order.</small>

      <label>Vehicle Capacity (liters) — optional</label>
      <input name="capacity" placeholder="e.g. 1000" value="{capacity}">

      <button class="btn" type="submit">Generate Result</button>
    </form>

    {result_section}

  </body>
</html>
"""

def predict_supply(milk_data):
    # deterministic tiny predictor: +5% baseline
    return [round(max(0.0, val * 1.05), 2) for val in milk_data]

def optimize_route(villages, distances=None):
    if distances is not None:
        total = round(sum(distances), 2)
        return villages, total
    return villages, None

def make_messages_html(msgs):
    if not msgs:
        return ""
    out = []
    for typ, m in msgs:
        cls = "success" if typ == "success" else "alert"
        out.append(f'<div class="{cls}">{html.escape(m)}</div>')
    return "\n".join(out)

def render_page(result=False, villages_list=None, predictions=None, route=None,
                total_distance=None, capacity=None, capacity_ok=None, total_predicted=None,
                form_values=None, messages=None):
    form_values = form_values or {}
    messages_html = make_messages_html(messages or [])
    if result:
        # build result HTML
        items = []
        for v, p in zip(villages_list, predictions):
            items.append(f'<div style="display:flex;justify-content:space-between;border:1px solid #eee;padding:8px;margin-top:6px;">'
                         f'<div>{html.escape(v)}</div><div style="font-weight:600;">{p} L</div></div>')
        route_html = "<ol>" + "".join(f"<li>{html.escape(r)}</li>" for r in route) + "</ol>"
        total_distance_html = f"<p><strong>Total distance:</strong> {total_distance} km</p>" if total_distance is not None else ""
        capacity_html = ""
        if capacity is not None:
            ok_text = "Sufficient" if capacity_ok else "Insufficient"
            ok_class = "success" if capacity_ok else "alert"
            capacity_html = f'<p><strong>Total predicted milk:</strong> {total_predicted} L</p><div class="{ok_class}"><strong>Vehicle capacity:</strong> {capacity} L — {ok_text}</div>'
        result_section = "<hr><h3>Predicted Milk Supply</h3>" + "".join(items) + "<h3 style='margin-top:12px;'>Optimized Route</h3>" + route_html + total_distance_html + capacity_html
    else:
        result_section = ""
    html_page = HTML_TEMPLATE.format(
        messages=messages_html,
        villages=html.escape(form_values.get("villages", "")),
        milk_data=html.escape(form_values.get("milk_data", "")),
        distances=html.escape(form_values.get("distances", "")),
        capacity=html.escape(form_values.get("capacity", "")),
        result_section=result_section
    )
    return html_page.encode("utf-8")

class SimpleHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        page = render_page(result=False, form_values={})
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(page)))
        self.end_headers()
        self.wfile.write(page)

    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length).decode("utf-8")
        data = parse_qs(body)
        form = {k: (v[0] if v else "") for k,v in data.items()}

        messages = []
        # parse villages
        raw_villages = form.get("villages", "")
        villages = [v.strip() for v in raw_villages.split(",") if v.strip()]
        if not villages:
            messages.append(("error", "Please provide at least one village name."))

        # parse milk data
        raw_milk = form.get("milk_data", "")
        milk_tokens = [t.strip() for t in raw_milk.split(",") if t.strip()]
        if not milk_tokens:
            messages.append(("error", "Please provide milk collection numbers (comma separated)."))
        milk_data = []
        if milk_tokens:
            try:
                milk_data = [float(x) for x in milk_tokens]
            except ValueError:
                messages.append(("error", "Milk values must be numbers (e.g. 120, 85.5)."))

        if villages and milk_data:
            if len(milk_data) == 1 and len(villages) > 1:
                milk_data = milk_data * len(villages)
            elif len(milk_data) != len(villages):
                messages.append(("error", "Number of milk data entries does not match number of villages. Provide one value per village or one value to broadcast."))

        # parse distances (optional)
        distances = None
        raw_distances = form.get("distances", "")
        if raw_distances.strip():
            dist_tokens = [t.strip() for t in raw_distances.split(",") if t.strip()]
            try:
                dist_vals = [float(x) for x in dist_tokens]
            except ValueError:
                messages.append(("error", "Distance values must be numbers (e.g. 5, 8.2)."))
                dist_vals = None
            if dist_vals is not None:
                if len(dist_vals) != len(villages):
                    messages.append(("error", "If you provide distances, provide the same number as villages."))
                else:
                    distances = dist_vals

        # parse capacity (optional)
        vehicle_capacity = None
        raw_capacity = form.get("capacity", "").strip()
        if raw_capacity:
            try:
                vehicle_capacity = float(raw_capacity)
                if vehicle_capacity <= 0:
                    raise ValueError()
            except ValueError:
                messages.append(("error", "Vehicle capacity must be a positive number."))

        # If any errors, re-render with messages
        err_msgs = [m for t,m in messages if t == "error"]
        if err_msgs:
            page = render_page(result=False, form_values=form, messages=[("error", m) for m in err_msgs])
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(page)))
            self.end_headers()
            self.wfile.write(page)
            return

        # compute predictions and route
        predictions = predict_supply(milk_data)
        route_order, total_distance = optimize_route(villages, distances=distances)
        total_predicted = round(sum(predictions), 2)
        capacity_ok = None
        if vehicle_capacity is not None:
            capacity_ok = vehicle_capacity >= total_predicted

        page = render_page(
            result=True,
            villages_list=villages,
            predictions=predictions,
            route=route_order,
            total_distance=total_distance,
            capacity=vehicle_capacity,
            capacity_ok=capacity_ok,
            total_predicted=total_predicted,
            form_values=form,
            messages=[("success", "Result generated successfully.")]
        )
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(page)))
        self.end_headers()
        self.wfile.write(page)

def run(server_class=HTTPServer, handler_class=SimpleHandler):
    server_address = (HOST, PORT)
    httpd = server_class(server_address, handler_class)
    print(f"Serving on http://{HOST}:{PORT}  (Ctrl-C to stop)")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("Shutting down...")
        httpd.server_close()
    except Exception as e:
        print("Server error:", e, file=sys.stderr)
        httpd.server_close()

if __name__ == "__main__":
    run() 