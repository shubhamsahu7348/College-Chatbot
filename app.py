from flask import Flask, render_template, request, jsonify, session
import json
import os
import re

from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()

API_KEY = os.environ.get('GEMINI_API_KEY')
if not API_KEY:
    raise RuntimeError('GEMINI_API_KEY is not set. Please add it to .env or your environment.')

client = genai.Client(api_key=API_KEY)
MODEL_NAME = 'gemini-3.5-flash'

app = Flask(__name__)
app.secret_key = os.environ.get('FLASK_SECRET_KEY', 'chatgpt_style_bot_secret_v3')
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_PATH = os.path.join(BASE_DIR, 'data', 'colleges.json')

# Load the college database
def load_data():
    try:
        with open(DATA_PATH, 'r', encoding='utf-8') as file:
            return json.load(file)
    except FileNotFoundError:
        return []

colleges_data = load_data()

# Helper: Match a college from free text
def find_college_in_text(text):
    text = text.lower()
    aliases = {
        'sppu': 1, 'pune university': 1,
        'spit': 2, 'sardar patel': 2,
        'pccoe': 3, 'pimpri chinchwad': 3,
        'vesit': 4, 'vivekanand': 4,
        'sies': 5, 'met': 6, 'indira': 7,
        'thakur': 8, 'dy patil': 12,
        'raisoni': 30, 'jspm': 14,
        'modern': 15, 'imcc': 16,
        'mim': 28, 'maharashtra institute of management': 28
    }

    for alias, cid in aliases.items():
        if alias in text:
            return next((c for c in colleges_data if c['id'] == cid), None)

    for c in colleges_data:
        name = c['name'].lower()
        if name in text or any(part in text for part in name.split() if len(part) > 5):
            return c

    return None

# Helper: Extract percentile from user text
def extract_percentile(text):
    match = re.search(r'(\d{1,3}(?:\.\d{1,2})?)\s*(?:percentile|%|pr)', text)
    if match:
        value = float(match.group(1))
        return value if value <= 100 else None
    return None

# Helper: Build relevant college context list
def get_relevant_colleges(active_college=None, detected_city=None, percentile=None):
    # Build a prioritized list of relevant colleges.
    candidates = []
    if active_college:
        candidates.append(active_college)

    # Prefer same-city colleges first
    if detected_city:
        city_matches = [c for c in colleges_data if c.get('city', '').lower() == detected_city.lower()]
        candidates.extend(sorted(city_matches, key=lambda x: x.get('ranking', 999))[:3])

    # If percentile provided, find colleges within a reasonable range (+/- 5-10 percentile)
    if percentile is not None:
        # Find colleges close to the student's percentile (within ±5 percentile range)
        close_range = [c for c in colleges_data if abs(c.get('percentile', 0) - percentile) <= 5]
        if not close_range:
            # Relax to ±10 percentile if nothing found
            close_range = [c for c in colleges_data if abs(c.get('percentile', 0) - percentile) <= 10]
        candidates.extend(sorted(close_range, key=lambda x: x.get('ranking', 999))[:8])

    # Always include top-ranked colleges as fallback
    if not candidates:
        candidates = sorted(colleges_data, key=lambda x: x.get('ranking', 999))[:5]

    # Deduplicate while preserving order
    unique = []
    seen = set()
    for college in candidates:
        cid = college.get('id')
        if cid not in seen:
            unique.append(college)
            seen.add(cid)
    # Limit to 10 to keep prompts small
    return unique[:10]

# System prompt for Gemini
def build_system_prompt():
    return (
        'You are Mikki, a friendly Maharashtra MCA admission counselor. '
        'You MUST answer only using the provided college JSON data included in the prompt. Do not invent or hallucinate any details. '
        'If a requested fact is not present in the provided data, reply exactly: "I could not find that information in the available college data." '
        'When you provide information, always include the college `name` you are referencing. For comparisons, list up to 3 colleges only. '
        'Be concise, natural, and helpful — write like a helpful admissions counselor giving clear, short bullet points or 1-2 sentence answers. '
        'Do NOT ask the user for the API key or any system-level info. '
        'Fields available in the data: id, name, city, type, course, percentile, ranking, fees, fees_tuition, fees_hostel, avg_package, highest_package, admission_process, intake, hostel_facility, scholarships.'
    )

# Build the user prompt
def build_user_prompt(message, context_colleges, detected_city=None, percentile=None):
    # Keep the data passed to the model small and explicit: include up to 3 relevant colleges
    data_summary = json.dumps(context_colleges, indent=2, ensure_ascii=False)
    extra_lines = []
    if detected_city:
        extra_lines.append(f'City context: {detected_city.title()}')
    if percentile is not None:
        extra_lines.append(f'Percentile context: {percentile}%')
    extra = '\n'.join(extra_lines)

    instructions = (
        "Answer the user's query using ONLY the JSON below.\n"
        "- If the user asks for fees, placements, intake, ranking or hostel info, extract those exact fields and cite the `name`.\n"
        "- For comparisons, give up to 3 short bullets: one line per college with name — fees — avg_package — hostel_facility.\n"
        "- If multiple colleges apply, say 'Showing top matches:' then the bullets.\n"
        "- If no data available, say exactly: 'I could not find that information in the available college data.'\n"
    )

    return (
        f"User query:\n{message}\n\n"
        f"{instructions}"
        f"{('Context: ' + extra + '\n\n') if extra else ''}"
        f"Relevant college JSON (only these records):\n{data_summary}"
    )

# Generate model response
def generate_response_with_gemini(user_message, relevant_colleges, detected_city=None, percentile=None):
    prompt_text = build_user_prompt(user_message, relevant_colleges, detected_city, percentile)
    contents = [
        types.Content(
            role='system',
            parts=[types.Part(text=build_system_prompt())],
        ),
        types.Content(
            role='user',
            parts=[types.Part(text=prompt_text)],
        ),
    ]

    response = client.models.generate_content(model=MODEL_NAME, contents=contents)
    if getattr(response, 'text', None):
        return response.text

    parts = []
    for part in getattr(response, 'parts', []) or []:
        if getattr(part, 'text', None):
            parts.append(part.text)
    return ' '.join(parts).strip() or 'I could not find that information in the available college data.'


# Helper: format a list of college dicts as HTML for chat UI
def format_colleges_html(colleges, title=None, show_limit=5, include_type=False, columns=None):
    if not colleges:
        return '<p>I could not find that information in the available college data.</p>'
    display = colleges[:show_limit]
    header = f'<strong>{title}</strong>' if title else ''
    # Default columns: College, City, Cutoff, Fees, Avg Package
    if columns is None:
        columns = ['name', 'city', 'percentile', 'fees', 'avg_package']
    column_labels = {
        'name': 'College',
        'city': 'City',
        'percentile': 'Cutoff',
        'fees': 'Fees (₹)',
        'avg_package': 'Avg Package',
        'intake': 'Intake',
        'type': 'Type',
        'highest_package': 'Highest Package',
        'hostel_facility': 'Hostel',
    }
    headers = [column_labels.get(c, c.title()) for c in columns]
    if include_type and 'type' not in columns:
        columns.insert(3, 'type')
        headers.insert(3, 'Type')
    header_cells = ''.join([f'<th class="pr-4">{h}</th>' for h in headers])
    table = [
        '<div class="mt-2 overflow-x-auto">',
        '<table class="w-full text-sm">',
        f'<thead><tr class="text-left">{header_cells}</tr></thead>',
        '<tbody>'
    ]
    for c in display:
        cols = []
        for col in columns:
            val = c.get(col, 'N/A')
            if col == 'name':
                cols.append(f'<td class="py-2 font-semibold">{val}</td>')
            else:
                cols.append(f'<td class="py-2">{val}</td>')
        row = f'<tr class="align-top border-t">{"".join(cols)}</tr>'
        table.append(row)
    table.append('</tbody></table></div>')
    return header + '\n' + '\n'.join(table)

@app.route('/')
def home():
    session.clear()
    return render_template('index.html')

@app.route('/clear', methods=['POST'])
def clear_chat():
    session.clear()
    return jsonify({'status': 'cleared'})

@app.route('/chat', methods=['POST'])
def chat():
    data = request.get_json(silent=True) or {}
    user_msg = (data.get('message') or '').strip()
    if not user_msg:
        return jsonify({'reply': 'Please type a message to continue.'})

    if 'context' not in session:
        session['context'] = {'college_id': None, 'percentile': None, 'city': None}
    context = session['context']

    lower_msg = user_msg.lower()
    cities = ['pune', 'mumbai', 'navi mumbai', 'nagpur', 'nashik', 'amravati', 'satara', 'kolhapur', 'aurangabad', 'solapur']
    detected_city = next((city for city in cities if city in lower_msg), None)
    if detected_city:
        context['city'] = detected_city.title()

    percentile = extract_percentile(lower_msg)
    if percentile is not None:
        context['percentile'] = percentile
    percentile_just_set = percentile is not None

    mentioned_college = find_college_in_text(lower_msg)
    if mentioned_college:
        context['college_id'] = mentioned_college['id']

    session['context'] = context
    active_college = next((c for c in colleges_data if c['id'] == context['college_id']), None)
    relevant_colleges = get_relevant_colleges(active_college, detected_city, context.get('percentile'))
    # Direct handlers for common structured queries to improve accuracy
    # 1) Top colleges list
    if re.search(r'\btop\b|\btop\s*(?:10|15)\b|top\s+colleges', lower_msg):
        top_n = 15
        top = sorted(colleges_data, key=lambda x: x.get('ranking', 999))[:top_n]
        html = format_colleges_html(top, title='Top 15 MCA colleges (by ranking):', show_limit=15)
        return jsonify({'reply': html, 'buttons': ['Fees of SPIT', 'Check chances for 85 percentile']})

    # 2) Specific quick-action handlers for common requested details
    if 'fees of spit' in lower_msg or 'spit fees' in lower_msg:
        spit = next((c for c in colleges_data if 'sardar patel institute of technology' in c.get('name','').lower()), None)
        if spit:
            html = format_colleges_html([spit], title='SPIT Fees and details:', show_limit=1, include_type=True)
            return jsonify({'reply': html, 'buttons': ['Top 10 MCA Colleges', 'Check chances for 95 percentile']})

    if 'admission process of pccoe' in lower_msg or 'pccoe admission' in lower_msg or 'pccoe' in lower_msg and 'admission' in lower_msg:
        pccoe = next((c for c in colleges_data if 'pimpri chinchwad college of engineering' in c.get('name','').lower()), None)
        if pccoe:
            reply = f"<strong>PCCOE admission process:</strong><br>{pccoe.get('admission_process','Information not available')}"
            return jsonify({'reply': reply, 'buttons': ['Top 10 MCA Colleges', 'Fees of SPIT']})

    # 3) College type queries: direct local answer for private/government classification
    if re.search(r'\b(private|government|govt|government department|university department|college type|type of college)\b', lower_msg):
        private_colleges = [c for c in colleges_data if 'private' in c.get('type','').lower()]
        government_colleges = [c for c in colleges_data if 'university department' in c.get('type','').lower() or ('university' in c.get('type','').lower() and 'private' not in c.get('type','').lower())]
        sections = []
        if private_colleges:
            sections.append(format_colleges_html(private_colleges, title='Private colleges (top results):', show_limit=5, include_type=True))
        if government_colleges:
            sections.append(format_colleges_html(government_colleges, title='Government / University Department colleges (top results):', show_limit=5, include_type=True))
        html = '<div>' + '<br>'.join(sections) + '</div>'
        return jsonify({'reply': html, 'buttons': ['Top 10 MCA Colleges', 'Fees of SPIT', 'Admission Process of PCCOE']})

    # 4) Intake and fees queries: direct local answer
    if re.search(r'\b(intake|fees|fee|fees and intake|intake and fees)\b', lower_msg):
        html = format_colleges_html(colleges_data, title='All colleges: Intake & Fees:', show_limit=30, columns=['name', 'city', 'intake', 'fees'])
        return jsonify({'reply': html, 'buttons': ['Top 15 MCA Colleges', 'Fees of SPIT', 'Check chances for 95 percentile']})

    # 5) Greeting handler
    if re.search(r'\b(hi|hello|hey|hii|hey there|good morning|good evening)\b', lower_msg):
        return jsonify({
            'reply': '<p>Hello! I am Mikki, your MCA admission counselor. Ask me about college fees, rankings, placements, private/government colleges, or percentile chances.</p>',
            'buttons': ['Top 10 MCA Colleges', 'Fees of SPIT', 'Admission Process of PCCOE']
        })

    # 6) Percentile-based matching: categorized by likelihood of admission
    percentile_intent = bool(re.search(r"\b(percentile|chance|chances|my chances|check chances|i got|i have)\b", lower_msg))
    if context.get('percentile') is not None and (percentile_just_set or percentile_intent):
        p = context.get('percentile')
        # Categorize colleges: highly likely (below user percentile), likely (within ±2), stretch (above)
        highly_likely = [c for c in colleges_data if c.get('percentile', 0) < p and c.get('percentile', 0) >= p - 3]
        likely = [c for c in colleges_data if c.get('percentile', 0) >= p - 1 and c.get('percentile', 0) <= p + 2]
        stretch = [c for c in colleges_data if c.get('percentile', 0) > p and c.get('percentile', 0) <= p + 5]
        
        # Sort each by ranking
        highly_likely = sorted(highly_likely, key=lambda x: x.get('ranking', 999))[:2]
        likely = sorted(likely, key=lambda x: x.get('ranking', 999))[:3]
        stretch = sorted(stretch, key=lambda x: x.get('ranking', 999))[:2]
        
        html_sections = []
        
        if highly_likely:
            html_sections.append(format_colleges_html(
                highly_likely, 
                title=f'<span style="color:green;">✓ High Chance (Cutoff &lt; {p}%)</span>',
                show_limit=10,
                columns=['name', 'city', 'percentile', 'fees', 'avg_package']
            ))
        
        if likely:
            html_sections.append(format_colleges_html(
                likely,
                title=f'<span style="color:orange;">◐ Good Chance (Cutoff ≈ {p}%)</span>',
                show_limit=10,
                columns=['name', 'city', 'percentile', 'fees', 'avg_package']
            ))
        
        if stretch:
            html_sections.append(format_colleges_html(
                stretch,
                title=f'<span style="color:blue;">△ Stretch Goal (Cutoff &gt; {p}%)</span>',
                show_limit=10,
                columns=['name', 'city', 'percentile', 'fees', 'avg_package']
            ))
        
        if html_sections:
            html = '<div>' + '<br><br>'.join(html_sections) + '</div>'
            return jsonify({'reply': html, 'buttons': ['Top 15 MCA Colleges', 'Intake & Fees']})
        else:
            return jsonify({'reply': '<p>I could not find colleges matching that percentile in the dataset.</p>', 'buttons': ['Top 15 MCA Colleges']})

    # 7) Fallback to Gemini for open-ended queries
    try:
        generated_reply = generate_response_with_gemini(user_msg, relevant_colleges, detected_city, context.get('percentile'))
    except Exception:
        generated_reply = 'I could not process your request right now. Please try again in a moment.'

    return jsonify({
        'reply': generated_reply,
        'buttons': ['Top 10 MCA Colleges', 'Fees of SPIT', 'Admission Process of PCCOE'],
    })

if __name__ == '__main__':
    app.run(debug=True)
