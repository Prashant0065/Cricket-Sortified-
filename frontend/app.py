import html
import re
from pathlib import Path

import streamlit as st
from services.backend_client import (
    BackendAPIError,
    send_registration_otp,
    resend_registration_otp,
    verify_email_otp,
    complete_registration,
    login,
    logout as logout_backend,
    get_batting_leaderboard,
    get_bowling_leaderboard,
    get_match_summary,
    get_match_overview,
    get_team_match_stats,
    get_match_status_summary,
    get_player_stats,
    get_live_matches,
    get_match_scorecard,
    search_players,
    get_cricbuzz_player_info,
    get_cricbuzz_player_career,
    get_cricbuzz_player_batting,
    get_cricbuzz_player_bowling,
    get_current_user,
)
LOGO_PATH = Path(__file__).parent / "assets" / "cricket_sortified_logo.png"
st.set_page_config(
    page_title="Cricket Sortified",
    page_icon=str(LOGO_PATH),
    layout="wide",
    initial_sidebar_state="expanded",
)



def apply_theme():
    """Apply the charcoal-and-lime visual system across every Streamlit page."""
    st.markdown(
        """
        <style>
        :root {
            --bg: #101713;
            --surface: #18211b;
            --surface-raised: #202b23;
            --border: #2c3a30;
            --accent: #b8f34a;
            --accent-strong: #a5e637;
            --text: #edf4ee;
            --muted: #a2afa5;
        }
        .stApp, [data-testid="stAppViewContainer"] {
            background: radial-gradient(ellipse at 80% -10%, #203324 0%, #101713 48%);
            color: var(--text);
        }
        [data-testid="stHeader"] { background: rgba(16,23,19,.88); }
        [data-testid="stToolbar"] { right: 1rem; }
        .block-container {
            max-width: 1500px;
            padding-top: 2.35rem;
            padding-bottom: 3rem;
        }
        /* Keep the public header spacious and prevent the brand lockup from clipping. */
        .public-header [data-testid="stHorizontalBlock"] { align-items: center; gap: 1rem; }
        .public-header [data-testid="column"] { min-width: 0; }
        .public-header .brand-lockup { min-width: 0; margin: 0; }
        .public-header .brand-name { white-space: nowrap; overflow: visible; }
        .public-header .brand-tagline { white-space: normal; line-height: 1.35; }
        .public-header .stButton > button {
            white-space: nowrap;
            min-height: 2.55rem;
            padding: .45rem .8rem;
        }
        h1, h2, h3, h4 { color: var(--text) !important; letter-spacing: -0.035em; }
        h1 { font-size: clamp(2rem, 3.2vw, 3rem) !important; font-weight: 800 !important; }
        h2 { font-weight: 750 !important; }
        p, label, .stMarkdown, [data-testid="stCaptionContainer"] { color: var(--text); }
        [data-testid="stCaptionContainer"] { color: var(--muted) !important; }
        a { color: var(--accent) !important; }
        hr { border-color: var(--border) !important; }
        [data-testid="stSidebar"] { background: #0b100d; border-right: 1px solid var(--border); }
        [data-testid="stSidebar"] > div:first-child { padding-top: 1.1rem; }
        [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] h1,
        [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] h2 { color: var(--accent) !important; }
        [data-testid="stRadio"] label { border-radius: 10px; padding: .45rem .55rem; transition: background .15s ease; }
        [data-testid="stRadio"] label:hover { background: var(--surface-raised); }
        [data-testid="stRadio"] label[data-checked="true"] { background: #263820; }
        .stButton > button, .stFormSubmitButton > button {
            border-radius: 10px; border: 1px solid var(--border); min-height: 2.65rem;
            font-weight: 650; transition: transform .15s ease, border-color .15s ease, background .15s ease;
        }
        .stButton > button:hover, .stFormSubmitButton > button:hover { border-color: var(--accent); transform: translateY(-1px); }
        .stButton > button[kind="primary"], .stFormSubmitButton > button[kind="primary"] {
            background: var(--accent); color: #15200f; border-color: var(--accent);
        }
        .stButton > button[kind="primary"] p, .stFormSubmitButton > button[kind="primary"] p { color: #15200f !important; }
        [data-testid="stMetric"] { background: linear-gradient(145deg, #1b271f, #151e18); border: 1px solid var(--border); padding: 1rem 1.1rem; border-radius: 14px; }
        [data-testid="stMetricLabel"] { color: var(--muted) !important; }
        [data-testid="stMetricValue"] { color: var(--accent) !important; font-weight: 800; }
        [data-testid="stVerticalBlockBorderWrapper"] { border-color: var(--border) !important; border-radius: 15px !important; background: rgba(24,33,27,.68); }
        [data-testid="stForm"] { border: 1px solid var(--border); background: rgba(24,33,27,.75); border-radius: 16px; padding: 1.25rem; }
        [data-testid="stTextInput"] input, [data-testid="stNumberInput"] input, [data-testid="stSelectbox"] div[data-baseweb="select"] > div, [data-testid="stTextArea"] textarea {
            background: #111914; color: var(--text); border-color: var(--border); border-radius: 10px;
        }
        /* Table containers: navy glass panel with a subtle cyan edge. */
        [data-testid="stDataFrame"], [data-testid="stTable"] {
            border: 1px solid #07539a !important;
            border-radius: 14px !important;
            overflow: hidden !important;
            background: #061426 !important;
            box-shadow: 0 0 18px rgba(0, 153, 255, .10), inset 0 0 0 1px rgba(0, 153, 255, .05);
        }
        [data-testid="stDataFrame"] [data-testid="glideDataEditor"],
        [data-testid="stDataFrame"] canvas { border-radius: 12px !important; }
        [data-testid="stTable"] table { border-collapse: separate !important; border-spacing: 0 !important; }
        [data-testid="stTable"] thead tr { background: #082448 !important; }
        [data-testid="stTable"] thead th {
            color: #a9d0ff !important; background: #082448 !important;
            border-bottom: 1px solid #124b80 !important; text-transform: uppercase;
            letter-spacing: .035em; font-weight: 800 !important; padding: 14px 16px !important;
        }
        [data-testid="stTable"] tbody tr:nth-child(odd) { background: #061426 !important; }
        [data-testid="stTable"] tbody tr:nth-child(even) { background: #0b1d32 !important; }
        [data-testid="stTable"] tbody td {
            color: #edf5ff !important; border-bottom: 1px solid rgba(52, 115, 170, .24) !important;
            padding: 13px 16px !important;
        }
        [data-testid="stTable"] tbody tr:hover td { background: #0c2b4c !important; }
        [data-testid="stAlert"] { border-radius: 12px; border: 1px solid var(--border); }
        [data-testid="stExpander"] { border: 1px solid var(--border); border-radius: 12px; background: rgba(24,33,27,.45); }
        [data-testid="stImage"] img { border-radius: 14px; }
        .brand-lockup {
            display:flex; align-items:center; gap:.8rem;
            min-width:0; margin:.2rem 0 1.25rem;
        }
        .brand-logo {
            display:block; flex:0 0 auto; width:58px; height:58px;
            object-fit:contain; border-radius:14px;
            filter: drop-shadow(0 5px 16px rgba(0, 190, 255, .15));
        }
        .brand-mark {
            display:flex; flex:0 0 auto; align-items:center; justify-content:center;
            width:46px; height:46px; border-radius:14px; background:var(--accent);
            color:#15200f; font-size:1.45rem; font-weight:900;
            box-shadow:0 8px 26px #b8f34a22;
        }
        .brand-copy { min-width:0; }
        .brand-name {
            color:var(--text); font-size:clamp(1.05rem, 1.45vw, 1.4rem);
            font-weight:850; line-height:1.2; letter-spacing:-.035em;
            overflow-wrap:normal;
        }
        .brand-tagline { color:var(--muted); font-size:.72rem; margin-top:.28rem; line-height:1.35; }
        .eyebrow { color:var(--accent); text-transform:uppercase; letter-spacing:.13em; font-size:.72rem; font-weight:800; margin-bottom:.45rem; }
        .hero-panel { padding:clamp(1.25rem, 3vw, 2.5rem); border:1px solid #354936; border-radius:22px; background:linear-gradient(120deg, #1d2b20 0%, #121a15 70%); margin:.5rem 0 1.25rem; }
        .hero-panel h1 { margin:.1rem 0 .6rem; }
        .hero-copy { color:#b7c5ba; font-size:1.04rem; max-width:760px; line-height:1.7; }
        .section-kicker { color:var(--accent); font-size:.75rem; font-weight:800; text-transform:uppercase; letter-spacing:.12em; }
        @media (max-width: 760px) {
            .block-container { padding: 1.5rem 1rem 2rem; }
            .public-header .brand-logo { width: 46px; height: 46px; }
            .public-header .brand-name { white-space: normal; font-size: 1.05rem; }
            .public-header .brand-tagline { font-size: .65rem; }
            [data-testid="stMetric"] { padding: .8rem; }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def brand_lockup(compact=False):
    """Show the Cricket Sortified logo and brand without changing page navigation."""
    tagline = "CRICKET INTELLIGENCE" if compact else "LIVE SCORES · PLAYER INSIGHTS · SQL ANALYTICS"
    logo_path = Path(__file__).resolve().parent / "assets" / "cricket_sortified_logo.png"

    if logo_path.is_file():
        import base64
        logo_data = base64.b64encode(logo_path.read_bytes()).decode("ascii")
        logo_html = (
            f'<img class="brand-logo" src="data:image/png;base64,{logo_data}" '
            'alt="Cricket Sortified logo">'
        )
    else:
        # Safe fallback if the optional logo asset has not been copied yet.
        logo_html = '<div class="brand-mark" aria-hidden="true">C</div>'

    st.markdown(
        f'<div class="brand-lockup">{logo_html}'
        f'<div class="brand-copy"><div class="brand-name">Cricket Sortified</div>'
        f'<div class="brand-tagline">{tagline}</div></div></div>',
        unsafe_allow_html=True,
    )


def initialize_session():
    defaults = {
        "page": "home",
        "pending_email": "",
        "access_token": None,
        "user": None,
        "live_matches": [],
        "selected_scorecard": None,
        "selected_match_label": "",
        "selected_match_id": None,
        "cricbuzz_search_results": [],
        "cricbuzz_player_data": None,
        "match_overview_data": None,
        "team_match_stats_data": None,
        "match_status_summary_data": None,
        "live_last_refreshed": None,
        "live_refresh_error": None,
    }

    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


initialize_session()
apply_theme()


def navigate(page):
    st.session_state.page = page
    st.rerun()


def handle_api_error(error):
    if getattr(error, "status_code", None) == 401:
        st.session_state.access_token = None
        st.session_state.user = None
        st.session_state.page = "signin"
        st.session_state.pending_email = ""
        st.warning(
            "Your session has expired or is no longer valid. "
            "Please sign in again."
        )
        st.rerun()
    else:
        st.error(str(error))


def start_dashboard(result):
    token = result.get("access_token")

    if not token:
        st.error("Authentication succeeded, but no access token was returned.")
        return

    st.session_state.access_token = token
    st.session_state.user = result.get("user", {})
    st.session_state.page = "dashboard"
    st.rerun()


def logout():
    token = st.session_state.access_token

    if token:
        try:
            logout_backend(token)
        except BackendAPIError as error:
            if getattr(error, "status_code", None) != 401:
                st.error(
                    "Could not confirm server-side logout. "
                    "Please try again."
                )
                return

    st.session_state.access_token = None
    st.session_state.user = None
    st.session_state.pending_email = ""
    st.session_state.page = "home"
    st.session_state.live_matches = []
    st.session_state.selected_scorecard = None
    st.rerun()


def show_header():
    # One aligned header row: generous brand width, flexible breathing room,
    # and consistently sized actions at the right.
    st.markdown('<div class="public-header">', unsafe_allow_html=True)
    left, spacer, signin_col, signup_col = st.columns(
        [4.8, 2.2, 1.35, 1.35]
    )

    with left:
        brand_lockup()

    if st.session_state.access_token:
        with signin_col:
            if st.button("Dashboard", use_container_width=True):
                navigate("dashboard")
        with signup_col:
            if st.button("Log Out", use_container_width=True):
                logout()
    else:
        with signin_col:
            if st.button("Sign In", use_container_width=True):
                navigate("signin")
        with signup_col:
            if st.button("Sign Up", use_container_width=True):
                navigate("signup")

    st.markdown('</div>', unsafe_allow_html=True)
    st.divider()


def show_home():
    st.markdown(
        """
        <section class="hero-panel">
          <div class="eyebrow">CRICKET DATA, REIMAGINED</div>
          <h1>Every match has a story.</h1>
          <div class="hero-copy">Explore match intelligence, player performance and team trends in one focused workspace. Powered by FastAPI, PostgreSQL and Cricbuzz data when the live API is available.</div>
        </section>
        """,
        unsafe_allow_html=True,
    )
    st.markdown("### Your cricket command center")
    st.caption("A quick look at what you can explore once you sign in.")
    cards = st.columns(4)
    features = [
        ("01", "Match centre", "Browse live snapshots and inspect detailed scorecards."),
        ("02", "Team analytics", "Compare wins, losses and match-status trends."),
        ("03", "Player insights", "Review locally stored batting and bowling totals."),
        ("04", "SQL leaderboards", "Explore top performers computed from PostgreSQL."),
    ]
    for col, (number, title, description) in zip(cards, features):
        with col:
            with st.container(border=True):
                st.markdown(f'<div class="section-kicker">{number}</div><h3>{title}</h3><p style="color:#a2afa5;line-height:1.55">{description}</p>', unsafe_allow_html=True)
    st.write("")
    left, right = st.columns([1, 3])
    with left:
        if st.button("Create account", type="primary", use_container_width=True):
            navigate("signup")
    with right:
        if st.button("I already have an account", use_container_width=True):
            navigate("signin")


def show_signup():
    st.title("Create your account")
    st.write("Enter your email address to receive a verification code.")

    with st.form("signup_form"):
        email = st.text_input(
            "Email address",
            placeholder="you@example.com",
        ).strip().lower()

        submitted = st.form_submit_button(
            "Send OTP",
            use_container_width=True,
            type="primary",
        )

    if submitted:
        if not email:
            st.error("Please enter your email address.")
        else:
            try:
                result = send_registration_otp(email)
                st.session_state.pending_email = email
                st.success(
                    result.get(
                        "message",
                        "Verification code sent. Check your email.",
                    )
                )
                navigate("verify_otp")
            except BackendAPIError as error:
                st.error(str(error))

    st.caption("Already have an account?")
    if st.button("Go to Sign In", use_container_width=True):
        navigate("signin")


def show_verify_otp():
    st.title("Verify your email")

    email = st.session_state.pending_email

    if not email:
        st.warning("Start registration first to request a verification code.")
        if st.button("Back to Sign Up"):
            navigate("signup")
        return

    st.write(f"Verification code sent to **{email}**.")

    with st.form("verify_otp_form"):
        otp = st.text_input(
            "Six-digit verification code",
            max_chars=6,
            placeholder="123456",
        ).strip()

        submitted = st.form_submit_button(
            "Verify OTP",
            use_container_width=True,
            type="primary",
        )

    if submitted:
        if len(otp) != 6 or not otp.isdigit():
            st.error("Enter a valid six-digit verification code.")
        else:
            try:
                result = verify_email_otp(email, otp)
                st.success(
                    result.get("message", "Email verified successfully.")
                )
                navigate("complete_registration")
            except BackendAPIError as error:
                st.error(str(error))

    if st.button("Resend OTP", use_container_width=True):
        try:
            result = resend_registration_otp(email)
            st.success(
                result.get(
                    "message",
                    "A new verification code has been sent.",
                )
            )
        except BackendAPIError as error:
            st.error(str(error))

    if st.button("Back to Sign Up", use_container_width=True):
        navigate("signup")


def show_complete_registration():
    st.title("Complete your registration")

    email = st.session_state.pending_email

    if not email:
        st.warning("Please start registration first.")
        if st.button("Go to Sign Up"):
            navigate("signup")
        return

    st.write(f"Verified email: **{email}**")

    with st.form("complete_registration_form"):
        username = st.text_input(
            "Username",
            max_chars=50,
            placeholder="Choose a username",
        ).strip()

        password = st.text_input(
            "Password",
            type="password",
            max_chars=128,
        )

        confirm_password = st.text_input(
            "Confirm password",
            type="password",
            max_chars=128,
        )

        submitted = st.form_submit_button(
            "Create Account",
            use_container_width=True,
            type="primary",
        )

    if submitted:
        if len(username) < 3:
            st.error("Username must contain at least 3 characters.")
        elif password != confirm_password:
            st.error("Passwords do not match.")
        elif len(password) < 8:
            st.error("Password must contain at least 8 characters.")
        else:
            try:
                result = complete_registration(
                    email,
                    username,
                    password,
                    confirm_password,
                )
                st.success("Registration successful.")
                start_dashboard(result)
            except BackendAPIError as error:
                st.error(str(error))

    if st.button("Back to Email Verification", use_container_width=True):
        navigate("verify_otp")


def show_signin():
    st.title("Welcome back")
    st.write("Sign in with your registered email or username.")

    with st.form("signin_form"):
        identifier = st.text_input(
            "Email or username",
            placeholder="Enter email or username",
        ).strip()

        password = st.text_input(
            "Password",
            type="password",
            max_chars=128,
        )

        submitted = st.form_submit_button(
            "Sign In",
            use_container_width=True,
            type="primary",
        )

    if submitted:
        if not identifier or not password:
            st.error("Enter both your email/username and password.")
        else:
            try:
                result = login(identifier, password)
                start_dashboard(result)
            except BackendAPIError as error:
                st.error(str(error))

    st.caption("Don't have an account?")
    if st.button("Create an Account", use_container_width=True):
        navigate("signup")


def render_table(data, use_container_width=True, hide_index=False, **kwargs):
    """Render data as a custom HTML table matching the navy/cyan reference UI."""
    import pandas as pd

    frame = data.copy() if isinstance(data, pd.DataFrame) else pd.DataFrame(data)
    if frame.empty:
        st.info("No records are available yet.")
        return

    # Keep the source data untouched; only customize its presentation.
    columns = [str(column) for column in frame.columns]
    rows = frame.to_dict(orient="records")

    def cell_html(column, value):
        label = "" if value is None else str(value)
        if label.lower() in {"none", "nan", "nat"}:
            label = "—" if label.lower() != "none" else "None"
        safe = html.escape(label)
        key = column.strip().lower().replace(" ", "_")

        if key in {"team_id", "match_id", "player_id", "cricbuzz_match_id"}:
            return f'<span class="cric-id">{safe}</span>'
        if key in {"status", "match_status"}:
            status = label.lower()
            cls = "live" if "live" in status or "in progress" in status else "completed" if "complete" in status else "neutral"
            icon = "●" if cls == "live" else "✓" if cls == "completed" else "•"
            return f'<span class="cric-pill {cls}">{icon}&nbsp; {safe}</span>'
        if key in {"format", "match_format"}:
            fmt = label.upper()
            cls = "odi" if fmt == "ODI" else "t20" if "T20" in fmt else "test" if "TEST" in fmt else "neutral"
            return f'<span class="cric-pill format-{cls}">{safe}</span>'
        if key in {"wins", "win", "total_wins"}:
            return f'<span class="cric-pill win">{safe}</span>' if label not in {"", "—"} else safe
        if key in {"losses", "loss", "total_losses"}:
            return f'<span class="cric-pill loss">{safe}</span>' if label not in {"", "—"} else safe
        if key in {"result_type", "result"} and label.lower() not in {"", "none", "nan", "—"}:
            return f'<span class="cric-pill result">{safe}</span>'
        if key in {"batter", "batsman", "batsman_name"}:
            return f'<span class="cric-player">🏏&nbsp; {safe}</span>'
        if key in {"bowler", "bowler_name"}:
            return f'<span class="cric-player">🔴&nbsp; {safe}</span>'
        if label in {"0", "0.0"} and key in {"wins", "losses", "wickets", "runs", "matches_played", "completed_matches"}:
            return f'<span class="cric-zero">{safe}</span>'
        return safe

    header_html = "".join(
        f'<th>{html.escape(column.replace("_", " ").upper())}<span class="cric-sort"> ↕</span></th>'
        for column in columns
    )
    body_rows = []
    for row in rows:
        cells = "".join(
            f'<td>{cell_html(column, row.get(column))}</td>'
            for column in frame.columns
        )
        body_rows.append(f"<tr>{cells}</tr>")

    st.markdown(
        """
        <style>
        .cric-table-shell {
            width: 100%; overflow-x: auto; margin: .45rem 0 1.15rem;
            border: 1px solid #123d68; border-radius: 15px;
            background: linear-gradient(145deg, #07172a 0%, #061222 100%);
            box-shadow: 0 0 0 1px rgba(0, 130, 255, .06), 0 8px 28px rgba(0, 35, 75, .16);
        }
        table.cric-table {
            width: 100%; min-width: 760px; border-collapse: separate;
            border-spacing: 0; color: #eaf3ff; font-size: 14px; line-height: 1.35;
        }
        .cric-table thead th {
            background: linear-gradient(180deg, #0b2341 0%, #081b33 100%);
            color: #a9ccf6; text-align: left; white-space: nowrap;
            font-size: 11px; font-weight: 850; letter-spacing: .055em;
            padding: 15px 17px; border-bottom: 1px solid #173b62;
            border-right: 1px solid rgba(62, 119, 176, .22);
        }
        .cric-table thead th:first-child { border-top-left-radius: 14px; }
        .cric-table thead th:last-child { border-top-right-radius: 14px; border-right: 0; }
        .cric-table tbody td {
            padding: 15px 17px; border-bottom: 1px solid rgba(65, 112, 160, .22);
            border-right: 1px solid rgba(65, 112, 160, .18);
            white-space: nowrap; font-weight: 550; color: #e7f0fc;
            background: rgba(5, 18, 34, .84);
        }
        .cric-table tbody tr:nth-child(even) td { background: rgba(12, 31, 53, .92); }
        .cric-table tbody tr:last-child td { border-bottom: 0; }
        .cric-table tbody td:last-child { border-right: 0; }
        .cric-table tbody tr:hover td {
            background: #0b2a4a; border-top: 1px solid #00bfff;
            border-bottom: 1px solid #00bfff;
        }
        .cric-sort { color: #7eb8f4; font-size: 13px; margin-left: 4px; }
        .cric-id { color: #24d8ff; font-weight: 850; }
        .cric-player { color: #f5f8ff; font-weight: 800; }
        .cric-pill {
            display: inline-block; border-radius: 999px; padding: 5px 10px;
            font-size: 11px; font-weight: 850; letter-spacing: .015em;
            border: 1px solid transparent;
        }
        .cric-pill.live { color: #8bff9d; background: rgba(24, 196, 83, .14); border-color: #168d43; box-shadow: inset 0 0 12px rgba(20, 210, 75, .08); }
        .cric-pill.completed { color: #9bc9ff; background: rgba(34, 112, 205, .18); border-color: #225a9e; }
        .cric-pill.win { color: #a2ffad; background: rgba(24, 196, 83, .18); border-color: #159447; min-width: 30px; text-align: center; }
        .cric-pill.loss { color: #ffaaaa; background: rgba(239, 68, 68, .15); border-color: #a83b48; min-width: 30px; text-align: center; }
        .cric-pill.result { color: #a2ffad; background: rgba(24, 196, 83, .15); border-color: #159447; text-transform: uppercase; }
        .cric-pill.format-odi { color: #65cfff; background: rgba(0, 153, 255, .13); border-color: #087cc0; }
        .cric-pill.format-t20 { color: #d2a3ff; background: rgba(147, 51, 234, .15); border-color: #7943bd; }
        .cric-pill.format-test { color: #ffc47d; background: rgba(249, 115, 22, .14); border-color: #b86617; }
        .cric-pill.format-neutral, .cric-pill.neutral { color: #c4d3e6; background: #172b42; border-color: #294562; }
        .cric-zero { color: #9aaec4; opacity: .62; }
        @media (max-width: 760px) {
            table.cric-table { font-size: 12px; }
            .cric-table thead th, .cric-table tbody td { padding: 12px; }
        }
        </style>
        <div class="cric-table-shell">
          <table class="cric-table">
            <thead><tr>""" + header_html + """</tr></thead>
            <tbody>""" + "".join(body_rows) + """</tbody>
          </table>
        </div>
        """,
        unsafe_allow_html=True,
    )


def display_api_result(result):
    if isinstance(result, list):
        if result:
            render_table(result, use_container_width=True)
        else:
            st.info("No records are available yet.")
        return

    if isinstance(result, dict):
        if not result:
            st.info("No records are available yet.")
            return

        if all(isinstance(value, (dict, list)) for value in result.values()):
            st.json(result)
            return

        render_table(
            [{"Metric": key, "Value": value} for key, value in result.items()],
            use_container_width=True,
        )
        return

    st.write(result)


def extract_matches(data):
    """Extract match records from the Cricbuzz live-matches response."""
    if not isinstance(data, dict):
        return []

    matches = []

    for match_group in data.get("typeMatches", []) or []:
        if not isinstance(match_group, dict):
            continue

        for series_group in match_group.get("seriesMatches", []) or []:
            if not isinstance(series_group, dict):
                continue

            wrapper = series_group.get("seriesAdWrapper") or {}
            if not isinstance(wrapper, dict):
                continue

            for match in wrapper.get("matches", []) or []:
                if not isinstance(match, dict):
                    continue

                info = match.get("matchInfo") or {}
                score = match.get("matchScore") or {}

                if isinstance(info, dict) and info:
                    matches.append({
                        "info": info,
                        "score": score if isinstance(score, dict) else {},
                    })

    return matches


def format_innings(team_score):
    if not isinstance(team_score, dict):
        return []

    formatted = []

    for key, innings in team_score.items():
        if not key.startswith("inngs") or not isinstance(innings, dict):
            continue

        runs = innings.get("runs", 0)
        wickets = innings.get("wickets", 0)
        overs = innings.get("overs")

        if overs is None:
            formatted.append(f"{runs}/{wickets}")
        else:
            formatted.append(f"{runs}/{wickets} · {overs} overs")

    return formatted


def render_selected_scorecard(match_id):
    """Render a selected scorecard directly inside its matching live-match card."""
    selected = st.session_state.get("selected_scorecard")
    selected_match_id = st.session_state.get("selected_match_id")
    if selected is None or str(selected_match_id) != str(match_id):
        return

    st.divider()
    st.subheader(
        f"Detailed Scorecard: {st.session_state.get('selected_match_label', 'Selected Match')}"
    )

    if not isinstance(selected, dict):
        st.error("The scorecard response is not a JSON object.")
        return

    innings_list = selected.get("scorecard")
    if not isinstance(innings_list, list) or not innings_list:
        st.warning("Cricbuzz did not return any innings for this scorecard.")
        with st.expander("View raw scorecard response"):
            st.json(selected)
        return

    for innings_index, innings in enumerate(innings_list, start=1):
        if not isinstance(innings, dict):
            continue

        innings_number = innings.get("inningsid", innings_index)
        st.markdown(f"### Innings {innings_number}")

        batsmen = innings.get("batsman")
        if not isinstance(batsmen, list):
            batsmen = innings.get("batTeamDetails", {}).get("batsmenData", [])
        if isinstance(batsmen, dict):
            batsmen = list(batsmen.values())

        batting_rows = []
        if isinstance(batsmen, list):
            for batter in batsmen:
                if not isinstance(batter, dict):
                    continue
                batting_rows.append({
                    "Batter": batter.get("name", batter.get("batName", "Unknown")),
                    "Runs": batter.get("runs", batter.get("runsScored", 0)),
                    "Balls": batter.get("balls", batter.get("ballsFaced", 0)),
                    "4s": batter.get("fours", batter.get("4s", 0)),
                    "6s": batter.get("sixes", batter.get("6s", 0)),
                    "Strike Rate": batter.get("strkrate", batter.get("strikeRate", "")),
                    "Dismissal": batter.get("outdec", batter.get("outDesc", "")),
                })

        if batting_rows:
            st.markdown("**Batting**")
            render_table(batting_rows, use_container_width=True, hide_index=True)
        else:
            st.info("Batting figures are not available for this innings.")

        bowlers = innings.get("bowler")
        if not isinstance(bowlers, list):
            bowlers = innings.get("bowlTeamDetails", {}).get("bowlersData", [])
        if isinstance(bowlers, dict):
            bowlers = list(bowlers.values())

        bowling_rows = []
        if isinstance(bowlers, list):
            for bowler in bowlers:
                if not isinstance(bowler, dict):
                    continue
                bowling_rows.append({
                    "Bowler": bowler.get("name", bowler.get("bowlName", "Unknown")),
                    "Overs": bowler.get("overs", bowler.get("oversBowled", "")),
                    "Maidens": bowler.get("maidens", bowler.get("maidensBowled", "")),
                    "Runs": bowler.get("runs", bowler.get("runsConceded", "")),
                    "Wickets": bowler.get("wickets", bowler.get("wicketsTaken", "")),
                    "Economy": bowler.get("economy", bowler.get("economyRate", "")),
                })

        if bowling_rows:
            st.markdown("**Bowling**")
            render_table(bowling_rows, use_container_width=True, hide_index=True)

        extras = innings.get("extrasData") or innings.get("extras")
        if extras:
            with st.expander(f"Extras — Innings {innings_number}"):
                st.json(extras)

        totals = innings.get("scoreDetails") or innings.get("total")
        if totals:
            with st.expander(f"Innings totals — Innings {innings_number}"):
                st.json(totals)

    with st.expander("View raw scorecard response"):
        st.json(selected)


def show_live_matches(token):
    st.subheader("Live Matches")
    st.caption(
        "Live match snapshots are provided by Cricbuzz when the API is available. "
        "Use View Scorecard to inspect a match's innings."
    )

    refresh_error = None
    if st.button("Refresh Live Matches", type="primary"):
        try:
            with st.spinner("Fetching match updates from Cricbuzz..."):
                data = get_live_matches(token)
            st.session_state.live_matches = extract_matches(data)
            from datetime import datetime, timezone
            st.session_state.live_last_refreshed = datetime.now(timezone.utc).strftime(
                "%Y-%m-%d %H:%M UTC"
            )
            st.session_state.live_refresh_error = None
        except BackendAPIError as error:
            # Preserve any previously fetched snapshots and avoid showing raw
            # provider responses (which may be confusing or overly detailed).
            refresh_error = error
            error_text = str(error).lower()
            if "429" in error_text or "monthly quota" in error_text or "quota" in error_text:
                st.session_state.live_refresh_error = "quota"
            else:
                st.session_state.live_refresh_error = "unavailable"

            if getattr(error, "status_code", None) == 401:
                handle_api_error(error)
                return

    matches = st.session_state.get("live_matches", [])
    refresh_error_state = st.session_state.get("live_refresh_error")

    if refresh_error is not None:
        error_text = str(refresh_error).lower()
        quota_exhausted = (
            "429" in error_text
            or "monthly quota" in error_text
            or "quota" in error_text
        )
        if quota_exhausted:
            st.warning(
                "Live updates are temporarily unavailable because the configured "
                "Cricbuzz API monthly request quota has been reached. Previously "
                "loaded match snapshots, if any, are shown below. Your saved "
                "PostgreSQL analytics remain available in Match Overview and Team Match Stats."
            )
        else:
            st.warning(
                "Cricbuzz could not provide live updates right now. Previously "
                "loaded match snapshots, if any, are shown below. Please try again later."
            )
    elif refresh_error_state == "quota":
        st.warning(
            "Live updates are temporarily unavailable because the configured "
            "Cricbuzz API monthly request quota has been reached. Previously "
            "loaded match snapshots, if any, are shown below. Your saved "
            "PostgreSQL analytics remain available in Match Overview and Team Match Stats."
        )

    if not matches:
        st.info(
            "No live-match snapshot is cached in this session. You can still use "
            "Match Overview, Team Match Stats, Match Status Summary, and SQL Analytics "
            "to explore data already stored in PostgreSQL."
        )
        return

    st.caption(
        f"Cached match snapshots: {len(matches)} · Last successful refresh: "
        f"{st.session_state.get('live_last_refreshed') or 'Not recorded'}"
    )
    st.info(
        "These are snapshots from the last successful refresh, not an automatic live feed. "
        "Scores may be out of date."
    )

    for index, item in enumerate(matches):
        info = item.get("info") or {}
        score = item.get("score") or {}
        team1_info = info.get("team1") or {}
        team2_info = info.get("team2") or {}
        venue = info.get("venueInfo") or {}

        team1 = team1_info.get("teamName", "Team 1")
        team2 = team2_info.get("teamName", "Team 2")
        status = info.get("status") or info.get("state") or "Status unavailable"
        series = info.get("seriesName", "Series unavailable")
        description = info.get("matchDesc", "Match")
        match_format = info.get("matchFormat", "Cricket")
        match_id = info.get("matchId")

        with st.container(border=True):
            st.markdown(f"### {team1} vs {team2}")
            st.caption(f"{series} · {description} · {match_format}")
            col1, col2 = st.columns(2)

            with col1:
                st.markdown(f"**{team1}**")
                scores = format_innings(score.get("team1Score", {}))
                if scores:
                    for score_line in scores:
                        st.write(score_line)
                else:
                    st.write("Score unavailable")

            with col2:
                st.markdown(f"**{team2}**")
                scores = format_innings(score.get("team2Score", {}))
                if scores:
                    for score_line in scores:
                        st.write(score_line)
                else:
                    st.write("Score unavailable")

            ground = venue.get("ground", "")
            city = venue.get("city", "")
            location = ", ".join(part for part in (ground, city) if part)
            if location:
                st.caption(f"📍 {location}")
            st.info(status)

            if match_id is None:
                st.caption("Scorecard unavailable: match ID not provided.")
            elif st.button(
                "View Scorecard",
                key=f"scorecard_{match_id}_{index}",
                use_container_width=True,
            ):
                try:
                    with st.spinner(f"Loading scorecard for {team1} vs {team2}..."):
                        result = get_match_scorecard(int(match_id), token)
                    if not isinstance(result, dict):
                        st.error("The backend returned an unexpected scorecard response.")
                    else:
                        st.session_state.selected_scorecard = result
                        st.session_state.selected_match_label = f"{team1} vs {team2}"
                        st.session_state.selected_match_id = match_id
                        st.rerun()
                except BackendAPIError as error:
                    handle_api_error(error)
                except (TypeError, ValueError):
                    st.error("This match has an invalid match ID.")
                except Exception:
                    st.error("An unexpected scorecard error occurred. Check the backend logs.")

            render_selected_scorecard(match_id)


def stats_response_to_rows(data):
    """Convert Cricbuzz's headers/values statistics response to table rows."""
    if not isinstance(data, dict):
        return []

    headers = data.get("headers", [])
    values = data.get("values", [])
    rows = []

    for item in values:
        if not isinstance(item, dict):
            continue

        row_values = item.get("values", [])
        if not row_values:
            continue

        row = {"Metric": row_values[0]}
        for index, header in enumerate(headers[1:], start=1):
            if index < len(row_values):
                row[header] = row_values[index]
        rows.append(row)

    return rows


def show_cricbuzz_player_dashboard(token):
    """Search for a player and display profile and career statistics."""
    st.subheader("Player Dashboard")
    st.caption(
        "Search for a cricket player to explore their profile, career, "
        "batting and bowling statistics from Cricbuzz."
    )

    with st.form("cricbuzz_player_search_form"):
        player_name = st.text_input(
            "Search player",
            placeholder="e.g. Virat Kohli",
        ).strip()
        search_submitted = st.form_submit_button(
            "Search Players",
            type="primary",
            use_container_width=True,
        )

    if search_submitted:
        if not player_name:
            st.warning("Enter a player name first.")
        else:
            try:
                with st.spinner("Searching Cricbuzz..."):
                    result = search_players(token, player_name)

                players = result.get("player", []) if isinstance(result, dict) else []
                st.session_state.cricbuzz_search_results = (
                    players if isinstance(players, list) else []
                )
                st.session_state.cricbuzz_player_data = None

                if not st.session_state.cricbuzz_search_results:
                    st.info("No players found. Try another name.")
            except BackendAPIError as error:
                handle_api_error(error)
                return

    players = st.session_state.get("cricbuzz_search_results", [])
    if not players:
        st.info("Search for a player to get started.")
        return

    player_options = {}
    for player in players:
        if not isinstance(player, dict) or player.get("id") is None:
            continue
        label = (
            f"{player.get('name', 'Unknown')} — "
            f"{player.get('teamName', 'Team unavailable')} "
            f"(ID: {player.get('id')})"
        )
        player_options[label] = player

    if not player_options:
        st.warning("Cricbuzz returned player results in an unexpected format.")
        return

    selected_label = st.selectbox(
        "Select a player",
        list(player_options.keys()),
        key="cricbuzz_selected_player",
    )
    selected_player = player_options[selected_label]
    player_id = str(selected_player["id"])

    if st.button(
        "Load Player Dashboard",
        type="primary",
        use_container_width=True,
    ):
        try:
            with st.spinner("Loading player profile and statistics..."):
                info = get_cricbuzz_player_info(token, player_id)
                career = get_cricbuzz_player_career(token, player_id)
                batting = get_cricbuzz_player_batting(token, player_id)
                bowling = get_cricbuzz_player_bowling(token, player_id)

            st.session_state.cricbuzz_player_data = {
                "player_id": player_id,
                "info": info,
                "career": career,
                "batting": batting,
                "bowling": bowling,
            }
        except BackendAPIError as error:
            handle_api_error(error)
            return

    player_data = st.session_state.get("cricbuzz_player_data")
    if not player_data:
        return

    if player_data.get("player_id") != player_id:
        st.info("Click **Load Player Dashboard** to load the selected player.")
        return

    info = player_data.get("info", {})
    if not isinstance(info, dict):
        st.error("Cricbuzz returned an unexpected player profile.")
        return

    st.divider()
    st.markdown(f"## {info.get('fullName') or info.get('name') or 'Player'}")

    face_image_id = selected_player.get("faceImageId")

    if face_image_id:
        image_url = (
            "https://static.cricbuzz.com/a/img/v1/152x152/"
            f"i1/c{face_image_id}/player.jpg"
        )

        try:
            import requests

            response = requests.get(
                image_url,
                headers={"User-Agent": "Mozilla/5.0"},
                timeout=10,
            )
            response.raise_for_status()

            if response.headers.get("Content-Type", "").startswith("image/"):
                st.image(response.content, width=160)
            else:
                st.caption("Player image is currently unavailable.")
        except requests.RequestException:
            st.caption("Player image is currently unavailable.")
    else:
        st.caption("Cricbuzz did not provide a player image ID.")

    col1, col2, col3 = st.columns(3)
    col1.metric("Team", info.get("intlTeam") or "Unavailable")
    col2.metric("Role", info.get("role") or "Unavailable")
    col3.metric("Height", info.get("height") or "Unavailable")

    col1, col2, col3 = st.columns(3)
    col1.metric("Batting Style", info.get("bat") or "Unavailable")
    col2.metric("Bowling Style", info.get("bowl") or "Unavailable")
    col3.metric("Birthplace", info.get("birthPlace") or "Unavailable")

    career = player_data.get("career", {})
    career_values = career.get("values", []) if isinstance(career, dict) else []
    career_rows = [
        {
            "Format": str(item.get("name", "")).upper(),
            "Debut": item.get("debut", "Unavailable"),
            "Last Played": item.get("lastPlayed", "Unavailable"),
        }
        for item in career_values
        if isinstance(item, dict)
    ]

    st.markdown("### Career Overview")
    if career_rows:
        render_table(career_rows, use_container_width=True, hide_index=True)
    else:
        st.info("Career overview is unavailable.")

    st.markdown("### Batting Statistics")
    batting_rows = stats_response_to_rows(player_data.get("batting"))
    if batting_rows:
        render_table(batting_rows, use_container_width=True, hide_index=True)
    else:
        st.info("Batting statistics are unavailable.")

    st.markdown("### Bowling Statistics")
    bowling_rows = stats_response_to_rows(player_data.get("bowling"))
    if bowling_rows:
        render_table(bowling_rows, use_container_width=True, hide_index=True)
    else:
        st.info("Bowling statistics are unavailable.")

    biography = info.get("bio", "")
    if isinstance(biography, str) and biography.strip():
        biography = html.unescape(biography)
        biography = re.sub(r"<[^>]+>", " ", biography)
        biography = re.sub(r"\s+", " ", biography).strip()
        with st.expander("Player Biography"):
            st.write(biography)


def render_lime_area_chart(chart_data):
    """Render match counts as a glowing lime area chart without changing page layout."""
    if chart_data is None or chart_data.empty:
        st.info("No chart data is available.")
        return

    try:
        import plotly.graph_objects as go

        totals = chart_data.sum(axis=1)
        x_values = [str(value).replace("_", " ").title() for value in totals.index]
        y_values = [int(value) for value in totals.fillna(0).tolist()]

        fig = go.Figure()

        # Layered translucent lines create a soft glow around the main lime line.
        fig.add_trace(go.Scatter(
            x=x_values, y=y_values, mode="lines",
            line=dict(color="rgba(184,243,74,0.10)", width=22, shape="spline"),
            hoverinfo="skip", showlegend=False,
        ))
        fig.add_trace(go.Scatter(
            x=x_values, y=y_values, mode="lines",
            line=dict(color="rgba(184,243,74,0.22)", width=12, shape="spline"),
            hoverinfo="skip", showlegend=False,
        ))
        fig.add_trace(go.Scatter(
            x=x_values, y=y_values, mode="lines+markers",
            line=dict(color="#B8F34A", width=3, shape="spline"),
            marker=dict(
                size=8, color="#D8FF8A",
                line=dict(color="#B8F34A", width=2),
            ),
            fill="tozeroy",
            fillcolor="rgba(92,190,44,0.20)",
            name="Matches",
            hovertemplate="<b>%{x}</b><br>Matches: %{y}<extra></extra>",
        ))

        fig.update_layout(
            height=340,
            margin=dict(l=12, r=18, t=18, b=12),
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font=dict(color="#EAF3E8", family="Arial, sans-serif", size=12),
            showlegend=False,
            hovermode="x unified",
            xaxis=dict(
                title=None,
                showgrid=False,
                zeroline=False,
                tickfont=dict(color="#C2D0C0"),
                linecolor="rgba(184,243,74,0.22)",
            ),
            yaxis=dict(
                title="Number of matches",
                rangemode="tozero",
                gridcolor="rgba(190,210,190,0.12)",
                zeroline=False,
                tickfont=dict(color="#AAB9A8"),
                title_font=dict(color="#AAB9A8", size=11),
            ),
        )
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
    except ImportError:
        # Keep the dashboard usable if Plotly is not installed in this environment.
        fallback = chart_data.sum(axis=1).rename("Matches")
        st.area_chart(fallback, color="#B8F34A")


def show_dashboard():
    token = st.session_state.access_token
    user = st.session_state.user or {}

    if not token:
        st.session_state.page = "signin"
        st.rerun()

    with st.sidebar:
        brand_lockup(compact=True)
        st.caption(f"SIGNED IN AS  ·  {user.get('username', 'User')}")
        st.divider()

        sections = [
            "Overview", "Live Matches", "Match Overview", "Team Match Stats",
            "Match Status Summary", "Batting Leaderboard", "Bowling Leaderboard",
            "Match Summary", "Player Statistics", "Player Dashboard", "Account",
            "CRUD Operations", "Home", "SQL Analytics", "Top Stats",
        ]
        quick = st.session_state.pop("quick_page", None)
        if quick in sections:
            st.session_state["dashboard_nav"] = quick
        section = st.radio(
            "Navigate",
            [
                "Overview",
                "Live Matches",
                "Match Overview",
                "Team Match Stats",
                "Match Status Summary",
                "Batting Leaderboard",
                "Bowling Leaderboard",
                "Match Summary",
                "Player Statistics",
                "Player Dashboard",
                "Account",
                "CRUD Operations",
                "Home",
                "SQL Analytics",
                "Top Stats",
            ],
            key="dashboard_nav",
        )

        st.divider()

        if st.button("Log Out", use_container_width=True):
            logout()

    st.markdown('<div class="eyebrow">PERFORMANCE WORKSPACE</div>', unsafe_allow_html=True)
    st.title(section if section != "Overview" else "Cricket Overview")
    st.caption("Cricket intelligence from your saved database and live provider snapshots.")

    if section == "Live Matches":
        show_live_matches(token)

    elif section == "Overview":
        st.subheader("Dashboard Overview")
        st.write(
            "A summary of match activity and team performance from your "
            "PostgreSQL analytics views."
        )

        if st.button("Refresh Analytics Dashboard", type="primary"):
            try:
                with st.spinner("Loading analytics from the backend..."):
                    st.session_state.match_overview_data = get_match_overview(token)
                    st.session_state.team_match_stats_data = get_team_match_stats(token)
                    st.session_state.match_status_summary_data = get_match_status_summary(token)
            except BackendAPIError as error:
                handle_api_error(error)

        overview = st.session_state.get("match_overview_data")
        team_stats = st.session_state.get("team_match_stats_data")
        status_summary = st.session_state.get("match_status_summary_data")

        if overview is None or team_stats is None or status_summary is None:
            st.info("Select **Refresh Analytics Dashboard** to load the latest database analytics.")
            col1, col2 = st.columns(2)
            with col1:
                st.info("Use the batting leaderboard to compare batters.")
            with col2:
                st.info("Use the bowling leaderboard to compare bowlers.")
        else:
            overview = overview if isinstance(overview, list) else []
            team_stats = team_stats if isinstance(team_stats, list) else []
            status_summary = status_summary if isinstance(status_summary, list) else []

            live_count = sum(1 for row in overview if str(row.get("status", "")).lower() == "live")
            completed_count = sum(1 for row in overview if str(row.get("status", "")).lower() == "completed")
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("Matches in Database", len(overview))
            col2.metric("Live Matches", live_count)
            col3.metric("Completed Matches", completed_count)
            col4.metric("Teams Tracked", len(team_stats))

            st.markdown("### Match Overview")
            if overview:
                render_table(overview, use_container_width=True, hide_index=True)
            else:
                st.info("No match records are available yet.")

            st.markdown("### Team Performance")
            if team_stats:
                import pandas as pd

                team_df = pd.DataFrame(team_stats)

                for column in ["wins", "matches_played", "completed_matches", "losses"]:
                    if column in team_df.columns:
                        team_df[column] = pd.to_numeric(
                            team_df[column], errors="coerce"
                        ).fillna(0).astype(int)

                sort_columns = [
                    column
                    for column in ["wins", "matches_played", "team_name"]
                    if column in team_df.columns
                ]
                if sort_columns:
                    team_df = team_df.sort_values(
                        by=sort_columns,
                        ascending=[column == "team_name" for column in sort_columns],
                        kind="stable",
                    )

                render_table(
                    team_df.head(10),
                    use_container_width=True,
                    hide_index=True,
                )
            else:
                st.info("No team statistics are available yet.")

            st.markdown("### Matches by Format and Status")
            if status_summary:
                render_table(status_summary, use_container_width=True, hide_index=True)
                try:
                    import pandas as pd
                    chart_data = pd.DataFrame(status_summary)
                    if {"status", "total_matches"}.issubset(chart_data.columns):
                        chart_data["total_matches"] = pd.to_numeric(
                            chart_data["total_matches"], errors="coerce"
                        ).fillna(0)
                        chart_data = chart_data.pivot_table(
                            index="status",
                            columns="format",
                            values="total_matches",
                            aggfunc="sum",
                            fill_value=0,
                        )
                        if not chart_data.empty:
                            render_lime_area_chart(chart_data)
                except (ImportError, ValueError, TypeError):
                    st.caption("Chart unavailable; the status summary table is shown above.")
            else:
                st.info("No match-status summary is available yet.")

    elif section == "Match Overview":
        st.subheader("Match Overview")
        if st.button("Load Match Overview", type="primary"):
            try:
                display_api_result(get_match_overview(token))
            except BackendAPIError as error:
                handle_api_error(error)

    elif section == "Team Match Stats":
        st.subheader("Team Match Statistics")
        if st.button("Load Team Match Statistics", type="primary"):
            try:
                display_api_result(get_team_match_stats(token))
            except BackendAPIError as error:
                handle_api_error(error)

    elif section == "Match Status Summary":
        st.subheader("Match Status Summary")
        if st.button("Load Match Status Summary", type="primary"):
            try:
                result = get_match_status_summary(token)
                display_api_result(result)
                if isinstance(result, list) and result:
                    try:
                        import pandas as pd
                        chart_data = pd.DataFrame(result)
                        if {"status", "total_matches"}.issubset(chart_data.columns):
                            chart_data["total_matches"] = pd.to_numeric(
                                chart_data["total_matches"], errors="coerce"
                            ).fillna(0)
                            chart_data = chart_data.pivot_table(
                                index="status", columns="format",
                                values="total_matches", aggfunc="sum", fill_value=0
                            )
                            if not chart_data.empty:
                                render_lime_area_chart(chart_data)
                    except (ImportError, ValueError, TypeError):
                        st.caption("Chart unavailable; use the table above.")
            except BackendAPIError as error:
                handle_api_error(error)

    elif section == "Batting Leaderboard":
        st.subheader("Batting Leaderboard")

        if st.button("Load Batting Leaderboard", type="primary"):
            try:
                result = get_batting_leaderboard(token)
                display_api_result(result)
            except BackendAPIError as error:
                handle_api_error(error)

    elif section == "Bowling Leaderboard":
        st.subheader("Bowling Leaderboard")

        if st.button("Load Bowling Leaderboard", type="primary"):
            try:
                result = get_bowling_leaderboard(token)
                display_api_result(result)
            except BackendAPIError as error:
                handle_api_error(error)

    elif section == "Match Summary":
        st.subheader("Match Summary")

        if st.button("Load Match Summary", type="primary"):
            try:
                result = get_match_summary(token)
                display_api_result(result)
            except BackendAPIError as error:
                handle_api_error(error)

    elif section == "Player Statistics":
        st.subheader("Player Statistics")

        st.caption("This page uses a LOCAL PostgreSQL player ID, not a Cricbuzz API player ID. Use Player Dashboard for live Cricbuzz player search.")
        player_id = st.number_input(
            "Local Database Player ID",
            min_value=1,
            step=1,
            value=1,
        )

        if st.button("Load Player Statistics", type="primary"):
            try:
                result = get_player_stats(token, player_id)
                display_api_result(result)
            except BackendAPIError as error:
                if error.status_code == 404:
                    st.warning("No player with that local database ID. Use Player Dashboard to search Cricbuzz players.")
                else:
                    handle_api_error(error)

    elif section == "Player Dashboard":
        show_cricbuzz_player_dashboard(token)

    elif section == "Account":
        st.subheader("My Account")
        if st.button("Refresh Account"):
            try:
                st.session_state.user = get_current_user(token)
            except BackendAPIError as error:
                handle_api_error(error)
        profile = st.session_state.user or {}
        st.write("**Username:**", profile.get("username") or "Unavailable")
        st.write("**Email:**", profile.get("email") or "Unavailable")
        st.write("**User ID:**", profile.get("user_id") or "Unavailable")
        st.caption("Account information is retrieved from your authenticated session. Passwords and access tokens are never displayed.")

    elif section == "CRUD Operations":
        st.subheader("Database Operations")
        st.info("Read-only database exploration is available here. Administrative writes should only be performed through validated, role-protected backend endpoints.")
        dataset = st.selectbox("Explore dataset", ["Match Overview", "Team Match Stats", "Match Status Summary"])
        try:
            fetch = {
                "Match Overview": get_match_overview,
                "Team Match Stats": get_team_match_stats,
                "Match Status Summary": get_match_status_summary,
            }[dataset]
            if st.button("Read Records"):
                display_api_result(fetch(token))
        except BackendAPIError as error:
            handle_api_error(error)
        st.caption("Create, update and delete actions are intentionally unavailable until their authorization and validation are implemented.")

    elif section == "Home":
        st.subheader("Welcome to Cricket Sortified")
        st.write("Explore synchronized cricket match metadata, live scorecards, PostgreSQL analytics and Cricbuzz player profiles.")
        st.info("Live API snapshots and PostgreSQL records may have different update times. Use Refresh Live Matches for current provider data.")
        if st.button("Go to Live Matches"):
            st.session_state["quick_page"] = "Live Matches"
            st.rerun()

    elif section == "SQL Analytics":
        st.subheader("SQL Analytics")
        st.caption("These results are computed from your PostgreSQL database, not directly from the live API.")
        choice = st.selectbox("Analytics report", ["Match Overview", "Team Match Stats", "Match Status Summary", "Match Summary"])
        endpoints = {
            "Match Overview": get_match_overview,
            "Team Match Stats": get_team_match_stats,
            "Match Status Summary": get_match_status_summary,
            "Match Summary": get_match_summary,
        }
        if st.button("Run Analytics"):
            try:
                display_api_result(endpoints[choice](token))
            except BackendAPIError as error:
                handle_api_error(error)

    elif section == "Top Stats":
        st.subheader("Top Cricket Statistics")
        st.caption("Only players with imported batting or bowling records appear in the SQL leaderboards.")
        if st.button("Load Top Performers"):
            try:
                st.markdown("#### Batting")
                display_api_result(get_batting_leaderboard(token))
                st.markdown("#### Bowling")
                display_api_result(get_bowling_leaderboard(token))
            except BackendAPIError as error:
                handle_api_error(error)


def main():
    if st.session_state.page != "dashboard":
        show_header()

    page = st.session_state.page

    if page == "home":
        show_home()
    elif page == "signup":
        show_signup()
    elif page == "verify_otp":
        show_verify_otp()
    elif page == "complete_registration":
        show_complete_registration()
    elif page == "signin":
        show_signin()
    elif page == "dashboard":
        show_dashboard()
    else:
        st.session_state.page = "home"
        st.rerun()


main()