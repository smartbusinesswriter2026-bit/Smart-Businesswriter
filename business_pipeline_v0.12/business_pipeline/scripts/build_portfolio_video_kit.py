"""Build the Portfolio Lab video marketing kit (Word + PDF).

    PYTHONPATH=src python scripts/build_portfolio_video_kit.py

The kit is written for the owner: positioning, scripts, prompts, tools, a
production checklist and a launch sequence. No app change is involved.
"""

import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from bp.product import docx  # noqa: E402

SECTIONS = [
    {"heading": "The one-line positioning", "paragraphs": [
        "\u201cChatGPT can write the memo. It cannot keep the ledger.\u201d",
        "The product is a dated, immutable portfolio record: snapshots, a chained time-weighted return, "
        "a student-written journal and a report a professor can audit. The proof is the screen, not a claim.",
    ]},
    {"heading": "Who it is for, and where they are", "bullets": [
        "Finance and investment-club students: TikTok, Reels, Shorts, Discord, campus clubs.",
        "Instructors and entrepreneurship centres: LinkedIn, department newsletters, conferences.",
        "Mock-fund competitions and cohort programmes: partnerships and free pilot licences.",
        "Search intent: \u201cportfolio report template\u201d, \u201ctime-weighted return calculator\u201d, \u201cmock fund journal\u201d.",
    ]},
    {"heading": "Five hooks you can reuse", "bullets": [
        "\u201cYour professor asked for a portfolio report. You have three stocks and no idea what your return is.\u201d",
        "\u201cAdding your weekly returns is not a time-weighted return. Here is the difference in 30 seconds.\u201d",
        "\u201cA chatbot writes the memo. It cannot show a dated snapshot, a contribution kept out of performance, or a return that chains week by week.\u201d",
        "\u201cFrom three holdings to a graded report in 12 minutes.\u201d",
        "\u201cThe line your professor will ask: where did this price come from? Show the provenance table.\u201d",
    ]},
    {"heading": "30-second TikTok / Reels script", "bullets": [
        "0-3s: HOOK. \u201cYour professor asked for a portfolio report. You have three stocks and no idea what your return is.\u201d",
        "3-8s: PROBLEM. \u201cMost students add their weekly returns. That is not a time-weighted return, and a contribution is not performance.\u201d",
        "8-22s: DEMO. Screen-record: create a mock fund \u2192 add AAPL, MSFT, VOO \u2192 enter prices \u2192 snapshot \u2192 show \u201cAll 12 checks passed\u201d \u2192 open the Word report.",
        "22-27s: PROOF. \u201cDated snapshots. A chained return. A journal in your own words. A report you can defend.\u201d",
        "27-30s: CTA. \u201cFree sample report and explainer in the link. Build your first fund this week.\u201d",
        "Style: vertical 9:16, navy/teal, large captions, real UI only, no fake testimonials.",
    ]},
    {"heading": "60-second YouTube Shorts demo", "bullets": [
        "0-5s: \u201cThis is a portfolio report a professor can actually grade.\u201d",
        "5-15s: Show the landing hero. \u201cStart a paper portfolio or a semester mock fund.\u201d",
        "15-30s: Create a fund, add three holdings, give one reason for each.",
        "30-42s: Enter prices, create the snapshot. Point at NAV, invested, cash and top three.",
        "42-52s: Open the journal, add a flow and a benchmark, show the time-weighted return.",
        "52-60s: Export the Word report; show \u201cAll 12 checks passed\u201d. CTA: free sample and explainer.",
    ]},
    {"heading": "AI video generator prompt (InVideo / Runway / Pika)", "paragraphs": [
        "Create a 30-second vertical fintech product demo, 9:16, clean and premium, navy #071A2B to teal "
        "#0B5A4A gradient, white sans-serif captions.",
        "Scene 1 (0-4s): a laptop on a desk, screen glowing, slow push-in. Text: \u201cYour portfolio report, "
        "without the spreadsheet panic.\u201d",
        "Scene 2 (4-12s): screen capture of a dark portfolio dashboard; big NAV number, three small stat tiles; "
        "cursor clicks \u201cCreate the snapshot\u201d.",
        "Scene 3 (12-20s): close-up of a holdings table and a green \u201cAll 12 checks passed\u201d panel; subtle "
        "checkmark animation.",
        "Scene 4 (20-26s): a Word report page opens; highlight \u201cHoldings and rationale\u201d and \u201cJournal of "
        "decisions\u201d.",
        "Scene 5 (26-30s): logo + text \u201cPortfolio Lab \u2014 build a book you can defend.\u201d CTA \u201cFree sample report.\u201d",
        "Rules: no fake people, no fake testimonials, no invented numbers; use only the numbers visible on "
        "screen. Smooth cuts, soft whoosh, light keyboard clicks.",
    ]},
    {"heading": "30-second voiceover", "paragraphs": [
        "Your professor asked for a portfolio report. Not a screenshot. A record. Declare your holdings, enter "
        "one dated price per position, and take a snapshot. The engine computes NAV, weights and concentration, "
        "and runs twelve checks. For a mock fund, add a weekly journal, a contribution and a benchmark, and it "
        "chains a time-weighted return. Then export the Word report: objective, holdings and rationale, "
        "performance, decisions, provenance and limits. Portfolio Lab. Build a book you can defend.",
    ]},
    {"heading": "LinkedIn / X post", "paragraphs": [
        "Most student portfolio reports fail on one thing: there is no ledger.",
        "A chatbot can write a memo. It cannot show a dated snapshot, a contribution kept out of performance, "
        "or a return that chains week by week.",
        "Portfolio Lab does: paper portfolio or semester mock fund; manual, pasted or CSV prices (optional "
        "quote fetch); NAV, weights, concentration; time-weighted return plus benchmark; a journal in the "
        "student's own words; a Word report with plain-language checks and named limits.",
        "Sample report and explainer: [link]",
    ]},
    {"heading": "Free tools to test", "table": {
        "columns": ["Tool", "Best for", "Free tier"],
        "rows": [
            ["CapCut (capcut.com)", "TikTok/Reels editing, captions, templates", "Free, watermark-free"],
            ["Canva (canva.com)", "Thumbnails, social templates, simple video", "Free plan"],
            ["Clipchamp (clipchamp.com)", "Screen + webcam, text-to-speech", "Free"],
            ["Adobe Express (express.adobe.com)", "Social cuts, branded templates", "Free tier"],
            ["InVideo AI (invideo.io)", "Prompt-to-video", "Free plan, watermark"],
            ["Fliki (fliki.ai)", "Script-to-video with AI voice", "Free plan"],
            ["HeyGen (heygen.com)", "AI avatar presenter", "Free trial/credits"],
            ["Runway / Pika / Luma", "B-roll and motion shots", "Free credits"],
            ["OBS Studio (obsproject.com)", "Real screen recording", "Free"],
            ["Loom (loom.com)", "Quick narrated demo", "Free tier"],
        ],
    }},
    {"heading": "Recommended stack", "bullets": [
        "Record the real workbench with OBS or Loom; the screen is the proof.",
        "Cut in CapCut for pace and automatic captions.",
        "Use Canva for the thumbnail and the end card.",
        "Use an AI avatar or generated b-roll only as garnish; never as the product demonstration.",
        "Keep one 60-second master recording and cut the 15s, 30s and vertical versions from it.",
    ]},
    {"heading": "Production checklist", "bullets": [
        "Format: 1080 \u00d7 1920 for Reels/Shorts/TikTok; 1920 \u00d7 1080 for LinkedIn/YouTube.",
        "First frame: the hook in 6 words or fewer.",
        "Captions on, because most feed viewing is silent.",
        "Blur or avoid any real student name, email or key.",
        "Show a real number and the checks panel; do not invent a return.",
        "End card: product name, one-line promise, link.",
        "Export MP4 (H.264), then upload natively to each platform.",
    ]},
    {"heading": "Launch sequence", "bullets": [
        "Week 1: post the 30s hook and the 60s demo; pin the sample report.",
        "Week 2: publish the \u201cwhy your TWR is wrong\u201d education video.",
        "Week 3: offer 20 instructors a free cohort pilot; ask for one testimonial.",
        "Week 4: publish the case study and a student walkthrough.",
        "Always: one call to action, one link, one measurable next step.",
    ]},
    {"heading": "What to measure", "bullets": [
        "Views are vanity; watch for saves, shares and profile visits.",
        "Sign-ups, first snapshot created, first report exported.",
        "Instructor pilots and weekly fund retention.",
        "Which hook produces the most saves; double down on that one.",
    ]},
    {"heading": "Rules", "bullets": [
        "No fake testimonials, no invented student names, no invented returns.",
        "Use the real sample report and say the prices are simulated.",
        "Do not claim the app predicts prices, picks stocks or executes trades.",
        "Do not show a key, a real portfolio or a private document on screen.",
    ]},
]


def build():
    data = docx.render_note("Portfolio Lab \u2014 video marketing kit",
                            "Scripts, prompts, tools and a production checklist \u00b7 build 1.45",
                            SECTIONS)
    target = ROOT / "samples" / "portfolio-lab-video-kit.docx"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(data)
    return target


if __name__ == "__main__":
    target = build()
    print("wrote %s (%d bytes)" % (target, target.stat().st_size))
