"""
SAP-style integration flowchart generator.
Supports:
  - Multi-hop chains  (S4 → AEM → CPI → PIGMA → Shroom)
  - Multiple receivers (fan-out from CPI or last relay)
  - SAP CPI internal-step visualisation
"""
import io, re, textwrap
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch

# ── SAP colours ───────────────────────────────────────────────────────────────
C_BLUE      = "#0070F2"
C_DARK      = "#1C2B33"
C_GRAY      = "#5C6B73"
C_LIGHT_BG  = "#EEF4FF"
C_SYS_FILL  = "#F7FAFF"
C_MAP       = "#FFF4E0"
C_ROUTE     = "#FFFBE0"
C_ERROR     = "#FFF0EE"
C_GROOVY    = "#F0FFF0"
C_STEP_DEF  = "#FFFFFF"
C_START     = "#107E3E"
C_STEP_BDR  = "#B0C4DE"
C_ARROW     = "#0070F2"
WHITE       = "#FFFFFF"

# System-type colours
_SYS_COLORS = {
    "sap":    ("#0070F2", "#E8F0FF"),   # SAP systems
    "aem":    ("#9B59B6", "#F5EEF8"),   # Event Mesh / AEM
    "mq":     ("#8E44AD", "#F5EEF8"),   # Message queue
    "pigma":  ("#27AE60", "#EAFAF1"),   # PIGMA / relay
    "sftp":   ("#16A085", "#E8F8F5"),   # SFTP
    "other":  ("#5C6B73", "#F2F4F5"),   # default external
}

def _sys_color(name: str):
    n = name.lower()
    if any(k in n for k in ("s4", "sap", "erp", "hana", "ecc")):
        return _SYS_COLORS["sap"]
    if any(k in n for k in ("aem", "event mesh", "event grid", "kafka", "amqp")):
        return _SYS_COLORS["aem"]
    if any(k in n for k in ("pigma", "relay", "middleware")):
        return _SYS_COLORS["pigma"]
    if any(k in n for k in ("sftp", "ftp", "file")):
        return _SYS_COLORS["sftp"]
    return _SYS_COLORS["other"]


# ── chain parsing ─────────────────────────────────────────────────────────────
_CPI_KEYWORDS = ("cpi", "cloud platform integration", "integration suite",
                 "integration flow", "iflow")
_ARROW_SEPS   = ("->", "→", ">>", "=>", "|", "–>", "-->")

def _is_cpi(name: str) -> bool:
    return any(k in name.lower() for k in _CPI_KEYWORDS)

def _parse_chain(data: dict) -> tuple[list[str], list[str]]:
    """
    Returns (pre_cpi, post_cpi) lists of system names.
    Tries to parse process_flow / flowchart string first,
    then falls back to source/target fields.
    """
    flow_str = (
        data.get("process_flow") or
        data.get("flowchart") or
        data.get("integration_logic") or ""
    ).strip()

    parts = _split_chain(flow_str)

    if parts:
        cpi_idx = next((i for i, p in enumerate(parts) if _is_cpi(p)), -1)
        if cpi_idx == -1:
            # No CPI label found – treat middle element as CPI implicitly
            cpi_idx = len(parts) // 2
        return parts[:cpi_idx], parts[cpi_idx + 1:]

    # Fallback: build from data fields
    source  = (data.get("source_app_name") or data.get("from_system") or
               data.get("source_system") or "Source System").split("\n")[0].strip()
    target  = (data.get("target_app_name") or data.get("to_system") or
               data.get("target_system") or "Target System")
    targets = _split_multi(target)
    return [source], targets


def _split_chain(s: str) -> list[str]:
    """Split a flow string on any known arrow separator."""
    for sep in _ARROW_SEPS:
        if sep in s:
            return [p.strip() for p in s.split(sep) if p.strip()]
    return []


def _split_multi(s: str) -> list[str]:
    """Split a comma/semicolon-separated target list."""
    parts = [p.strip() for p in re.split(r"[,;]", s) if p.strip()]
    return parts or [s.strip()]


def _is_relay_system(name: str) -> bool:
    """True only if the system is a genuine middleware relay (not a final receiver)."""
    n = name.lower()
    return any(k in n for k in (
        "pigma", "relay", "middleware", "hub", "bus",
        "aem", "event mesh", "event grid", "kafka", "mq", "amqp",
    ))


def _proto_from_name(name: str) -> str:
    """Infer the protocol label from a receiver system name, e.g. 'Manogna SFTP' → 'SFTP'."""
    n = name.upper()
    for proto in ("SFTP", "FTP", "SOAP", "HTTPS", "HTTP", "IDOC", "RFC", "AS2", "AMQP", "ODATA"):
        if proto in n:
            return proto
    return ""


# ── CPI step extraction ───────────────────────────────────────────────────────
_KNOWN_STEPS = [
    "Content Modifier", "Message Mapping", "XSLT Mapping", "Groovy Script",
    "JavaScript", "Router", "Filter", "Splitter", "Aggregator",
    "Process Call", "Exception Subprocess", "Error Handler",
    "HTTP Call", "OData Call", "SFTP Write", "SFTP Read",
    "Encoder", "Decoder", "JSON to XML", "XML to JSON", "Request Reply",
]

def _classify(label: str):
    l = label.lower()
    if any(k in l for k in ("mapping", "xslt", "transform")):
        return C_MAP, C_BLUE
    if any(k in l for k in ("router", "route", "filter", "condition")):
        return C_ROUTE, "#996600"
    if any(k in l for k in ("groovy", "script", "javascript")):
        return C_GROOVY, "#2E7D32"
    if any(k in l for k in ("error", "exception", "fault", "catch")):
        return C_ERROR, "#BB0000"
    return C_STEP_DEF, C_DARK

def _extract_steps(data: dict) -> list[str]:
    logic = (data.get("integration_logic", "") + " " +
             data.get("processing_description", "") + " " +
             data.get("iflow_description", "")).lower()
    mt = data.get("mapping_type", "").lower()

    found: list[str] = []

    # Content Modifier — almost always present
    if any(k in logic for k in ("content modifier", "set header", "set property",
                                  "msgid", "timestamp", "enrich")):
        found.append("Content Modifier")
    elif "content modifier" not in found:
        found.append("Content Modifier")   # always include as first step

    # Script detection — check groovy BEFORE mapping so Groovy wins over Message Mapping
    if any(k in logic for k in ("groovy", "script", "javascript",
                                  "transform", "parse", "xslurper", "streamingmarkup")):
        found.append("Groovy Script")
    elif "groovy" in mt or "script" in mt:
        found.append("Groovy Script")
    elif any(k in logic for k in ("xslt", "stylesheet", "xsl transform")):
        found.append("XSLT Mapping")
    elif any(k in logic for k in ("message mapping", "graphical mapping",
                                    "mmap", "field mapping")):
        found.append("Message Mapping")
    elif "xslt" in mt:
        found.append("XSLT Mapping")
    elif mt and mt not in ("none", ""):
        found.append("Message Mapping")

    # Router — detect content-based routing
    if any(k in logic for k in ("router", "route", "routing", "gateway",
                                  "branch", "condition", "receiver number",
                                  "exclusive", "cbr")):
        found.append("Router")

    # Splitter / Aggregator
    if any(k in logic for k in ("splitter", "split", "aggregate", "gather")):
        found.append("Splitter")

    # Exception / Error handling
    if any(k in logic for k in ("exception", "error", "fault", "catch",
                                  "subprocess", "error handler")):
        found.append("Exception Subprocess")
    else:
        found.append("Exception Subprocess")  # always shown in CPI best-practice

    # De-duplicate, preserve order
    seen, out = set(), []
    for s in found:
        if s not in seen:
            seen.add(s)
            out.append(s)
    return out


# ── drawing primitives ────────────────────────────────────────────────────────
def _rbox(ax, x, y, w, h, text, fill, edge, tc=C_DARK, fs=8, bold=False, r=0.12):
    ax.add_patch(FancyBboxPatch(
        (x, y), w, h,
        boxstyle=f"round,pad=0.0,rounding_size={r}",
        facecolor=fill, edgecolor=edge, linewidth=1.4, zorder=3,
    ))
    lines = textwrap.wrap(text, width=16)
    lh = 0.22
    sy = y + h / 2 + (len(lines) - 1) * lh / 2
    for i, ln in enumerate(lines):
        ax.text(x + w / 2, sy - i * lh, ln,
                ha="center", va="center",
                fontsize=fs, fontweight="bold" if bold else "normal",
                color=tc, zorder=4)


def _sys_box(ax, x, y, w, h, label, name):
    edge, fill = _sys_color(name)
    # Body
    ax.add_patch(FancyBboxPatch(
        (x, y), w, h,
        boxstyle="round,pad=0.0,rounding_size=0.12",
        facecolor=fill, edgecolor=edge, linewidth=1.8, zorder=3,
    ))
    # Header strip
    hdr_h = 0.35
    ax.add_patch(FancyBboxPatch(
        (x, y + h - hdr_h), w, hdr_h,
        boxstyle="round,pad=0.0,rounding_size=0.10",
        facecolor=edge, edgecolor=edge, linewidth=0, zorder=4,
    ))
    ax.text(x + w / 2, y + h - hdr_h / 2, label,
            ha="center", va="center",
            fontsize=7, fontweight="bold", color=WHITE, zorder=5)
    lines = textwrap.wrap(name, width=14)
    lh = 0.24
    cy = y + (h - hdr_h) / 2 + (len(lines) - 1) * lh / 2
    for i, ln in enumerate(lines):
        ax.text(x + w / 2, cy - i * lh, ln,
                ha="center", va="center",
                fontsize=8, fontweight="bold", color=C_DARK, zorder=5)


def _arrow(ax, x1, y1, x2, y2, label=""):
    ax.annotate("", xy=(x2, y2), xytext=(x1, y1),
                arrowprops=dict(arrowstyle="-|>", color=C_ARROW,
                                lw=1.8, mutation_scale=15,
                                connectionstyle="arc3,rad=0.0"),
                zorder=3)
    if label:
        mx, my = (x1 + x2) / 2, (y1 + y2) / 2 + 0.16
        ax.text(mx, my, label, ha="center", va="bottom",
                fontsize=6.5, color=C_GRAY,
                bbox=dict(boxstyle="round,pad=0.12", fc=WHITE,
                          ec=C_STEP_BDR, lw=0.7))


def _event(ax, cx, cy, r, color, label, below=True):
    ax.add_patch(plt.Circle((cx, cy), r,       color=color, zorder=4))
    ax.add_patch(plt.Circle((cx, cy), r * 0.55, color=WHITE, zorder=5))
    ax.add_patch(plt.Circle((cx, cy), r * 0.30, color=color, zorder=6))
    off = -(r + 0.16) if below else (r + 0.16)
    ax.text(cx, cy + off, label,
            ha="center", va="top" if below else "bottom",
            fontsize=7, color=C_DARK, zorder=7)


# ── main builder ──────────────────────────────────────────────────────────────
SYS_W  = 1.75
SYS_H  = 1.30
GAP    = 0.65      # horizontal gap between boxes (arrow space)
CPI_W  = 3.50
EVT_R  = 0.20
STEP_H = 0.46
STEP_G = 0.18
HDR_H  = 0.38      # CPI title bar height


def _cpi_height(steps: list[str]) -> float:
    n = len(steps)
    return (HDR_H + 0.35          # title + padding
            + EVT_R * 2 + STEP_G  # start event
            + n * STEP_H + max(0, n - 1) * STEP_G
            + STEP_G + EVT_R * 2  # end event
            + 0.35)               # bottom padding


def _draw_cpi_box(ax, x, y, w, h, steps: list[str]):
    # Background
    ax.add_patch(FancyBboxPatch(
        (x, y), w, h,
        boxstyle="round,pad=0.0,rounding_size=0.18",
        facecolor=C_LIGHT_BG, edgecolor=C_BLUE, linewidth=2.0, zorder=1,
    ))
    ax.text(x + w / 2, y + h - HDR_H / 2,
            "SAP Cloud Platform Integration",
            ha="center", va="center",
            fontsize=8.5, fontweight="bold", color=C_BLUE, zorder=2)

    cx = x + w / 2
    cur_y = y + h - HDR_H - 0.30

    # Start event
    _event(ax, cx, cur_y - EVT_R, EVT_R, C_START, "Start", below=False)
    cur_y -= EVT_R * 2 + STEP_G

    # Steps
    sw = w - 0.8
    for i, step in enumerate(steps):
        sy = cur_y - STEP_H
        fill, tc = _classify(step)
        _rbox(ax, cx - sw / 2, sy, sw, STEP_H, step, fill, C_STEP_BDR, tc=tc, fs=8)
        if i < len(steps) - 1:
            _arrow(ax, cx, sy, cx, sy - STEP_G)
        cur_y = sy - STEP_G

    # End event
    _arrow(ax, cx, cur_y + STEP_G, cx, cur_y - EVT_R * 2 + STEP_G * 0.5)
    _event(ax, cx, cur_y - EVT_R, EVT_R, C_START, "End")

    # Dotted spine
    ax.plot([cx, cx], [y + h - HDR_H - 0.30, cur_y - EVT_R + EVT_R],
            color=C_STEP_BDR, lw=0.6, ls=":", zorder=1)


def generate_flowchart(data: dict) -> bytes:
    pre_cpi, post_cpi = _parse_chain(data)
    steps = _extract_steps(data)
    iface = data.get("interface_name", "Integration Flow")

    # Check target_app_name / target_system for multiple receivers explicitly
    explicit_targets_str = (
        data.get("target_app_name") or
        data.get("to_system") or
        data.get("target_system") or ""
    )
    explicit_targets = _split_multi(explicit_targets_str)
    has_multi_targets = len(explicit_targets) > 1

    if has_multi_targets:
        # Multiple final receivers detected.
        # Only treat post_cpi items as relay/middleware if they are genuine relay
        # systems (PIGMA, AEM, MQ, etc.).  Receiver systems (SFTP, HTTP, SOAP-named)
        # must NOT be used as a relay — they fan out directly from CPI.
        relay_nodes = [p for p in post_cpi if _is_relay_system(p)]
        relay     = relay_nodes       # e.g. ["PIGMA"] — only real middleware
        receivers = explicit_targets  # e.g. ["Manogna SFTP","Mrudula HTTP","Shaleni SOAP"]
    elif len(post_cpi) == 1:
        targets = _split_multi(post_cpi[0])
        if len(targets) > 1:
            relay, receivers = [], targets
        else:
            relay, receivers = post_cpi, []
    elif len(post_cpi) > 1:
        combined = ", ".join(post_cpi)
        sub = _split_multi(combined)
        if len(sub) > len(post_cpi):
            relay, receivers = [], sub
        else:
            relay, receivers = post_cpi, []
    else:
        relay, receivers = [], []

    fanout = len(receivers) > 0
    n_recv = max(len(receivers), 1)

    # ── figure dimensions ────────────────────────────────────────────────────
    cpi_h   = _cpi_height(steps)
    row_h   = max(SYS_H, 1.30)
    spacing = 0.55   # vertical gap between receivers

    if fanout:
        needed_h = n_recv * row_h + (n_recv - 1) * spacing
        fig_h = max(cpi_h + 2.0, needed_h + 2.5)
    else:
        fig_h = max(cpi_h + 2.0, SYS_H + 3.0)

    # Width: pre-chain + gap + CPI + gap + relay-chain
    n_pre   = max(len(pre_cpi), 0)
    n_relay = len(relay)
    fig_w   = (n_pre  * (SYS_W + GAP)
               + CPI_W
               + (n_relay * (GAP + SYS_W) if not fanout else (GAP + SYS_W))
               + 1.4)   # margins
    fig_w   = max(fig_w, 13.0)

    fig, ax = plt.subplots(figsize=(fig_w, fig_h), dpi=150)
    ax.set_xlim(0, fig_w)
    ax.set_ylim(0, fig_h)
    ax.axis("off")
    ax.set_facecolor(WHITE)
    fig.patch.set_facecolor(WHITE)

    # ── title ─────────────────────────────────────────────────────────────────
    ax.text(fig_w / 2, fig_h - 0.32, iface,
            ha="center", va="center",
            fontsize=10.5, fontweight="bold", color=C_DARK)
    ax.text(fig_w / 2, fig_h - 0.65,
            "SAP Cloud Platform Integration — Technical Design",
            ha="center", va="center", fontsize=8, color=C_GRAY)

    mid_y = fig_h / 2   # vertical centre

    # ── pre-CPI systems ───────────────────────────────────────────────────────
    cur_x = 0.5
    labels = ["SENDER"] + [""] * (len(pre_cpi) - 1)
    prev_cx = None
    for i, sname in enumerate(pre_cpi):
        lbl = "SENDER" if i == 0 else _short_label(sname)
        _sys_box(ax, cur_x, mid_y - SYS_H / 2, SYS_W, SYS_H, lbl, sname)
        bx = cur_x + SYS_W
        if prev_cx is not None:
            _arrow(ax, prev_cx, mid_y, bx - GAP, mid_y)
        prev_cx = bx
        cur_x = bx + GAP

    # Arrow into CPI
    cpi_x = cur_x
    src_proto = data.get("source_protocol", "").split()[0] if pre_cpi else ""
    if prev_cx is not None:
        _arrow(ax, prev_cx, mid_y, cpi_x, mid_y, label=src_proto)

    # ── SAP CPI box ───────────────────────────────────────────────────────────
    cpi_y = mid_y - cpi_h / 2
    _draw_cpi_box(ax, cpi_x, cpi_y, CPI_W, cpi_h, steps)
    cpi_right = cpi_x + CPI_W

    # ── post-CPI: relay chain or fan-out ──────────────────────────────────────
    tgt_proto = data.get("target_protocol", "").split()[0]

    if not fanout:
        # Linear relay chain
        cur_x = cpi_right + GAP
        prev_cx = cpi_right
        for i, rname in enumerate(relay):
            lbl = "RECEIVER" if i == len(relay) - 1 else _short_label(rname)
            _arrow(ax, prev_cx, mid_y, cur_x, mid_y,
                   label=tgt_proto if i == 0 else "")
            _sys_box(ax, cur_x, mid_y - SYS_H / 2, SYS_W, SYS_H, lbl, rname)
            prev_cx = cur_x + SYS_W
            cur_x = prev_cx + GAP

    else:
        # Fan-out: CPI → relay node (optional) → multiple receivers
        recv_x = cpi_right + GAP
        if relay:
            # Relay node (e.g. PIGMA) at mid_y
            _arrow(ax, cpi_right, mid_y, recv_x, mid_y, label=tgt_proto)
            _sys_box(ax, recv_x, mid_y - SYS_H / 2, SYS_W, SYS_H,
                     _short_label(relay[0]), relay[0])
            fan_x = recv_x + SYS_W
        else:
            fan_x = cpi_right
            tgt_proto = tgt_proto

        # Receivers stacked vertically — fan out from right edge of relay/CPI
        total_h_recv = n_recv * row_h + (n_recv - 1) * spacing
        top_y = mid_y + total_h_recv / 2 - row_h / 2

        recv_x = fan_x + GAP + SYS_W * 0.3   # where receiver boxes start

        for i, rname in enumerate(receivers[:8]):   # cap at 8
            ry = top_y - i * (row_h + spacing)
            ry_mid = ry + row_h / 2
            # Per-receiver protocol: try to infer from system name, fallback to global
            recv_proto = _proto_from_name(rname) or tgt_proto
            # Horizontal jog: go right from fan point, then to receiver
            ax.annotate("",
                xy=(recv_x, ry_mid),
                xytext=(fan_x, mid_y),
                arrowprops=dict(
                    arrowstyle="-|>", color=C_ARROW, lw=1.6,
                    mutation_scale=14,
                    connectionstyle="arc3,rad=0.0",
                ),
                zorder=3,
            )
            # Protocol label on every arrow — place at actual arrow midpoint
            if recv_proto:
                mx = (fan_x * 0.35 + recv_x * 0.65)   # 65% of the way along the arrow
                my_label = (mid_y * 0.35 + ry_mid * 0.65) + 0.14  # slightly above midpoint
                ax.text(mx, my_label, recv_proto,
                        ha="center", va="bottom", fontsize=6.5, color=C_GRAY,
                        bbox=dict(boxstyle="round,pad=0.12", fc=WHITE,
                                  ec=C_STEP_BDR, lw=0.7))
            _sys_box(ax, recv_x, ry, SYS_W, row_h,
                     "RECEIVER" if n_recv == 1 else f"RECV {i+1}", rname)

    # ── legend ────────────────────────────────────────────────────────────────
    legend_items = [
        mpatches.Patch(facecolor=C_MAP,    edgecolor=C_STEP_BDR, label="Mapping"),
        mpatches.Patch(facecolor=C_ROUTE,  edgecolor=C_STEP_BDR, label="Router"),
        mpatches.Patch(facecolor=C_GROOVY, edgecolor=C_STEP_BDR, label="Script"),
        mpatches.Patch(facecolor=C_ERROR,  edgecolor=C_STEP_BDR, label="Error Handling"),
        mpatches.Patch(facecolor=C_STEP_DEF, edgecolor=C_STEP_BDR, label="Other Step"),
    ]
    ax.legend(handles=legend_items, loc="lower right",
              fontsize=7, framealpha=0.95, edgecolor=C_STEP_BDR,
              ncol=5, bbox_to_anchor=(1.0, 0.0))

    buf = io.BytesIO()
    plt.savefig(buf, format="png", dpi=150, bbox_inches="tight",
                facecolor=WHITE, edgecolor="none")
    plt.close(fig)
    buf.seek(0)
    return buf.getvalue()


def _short_label(name: str) -> str:
    """Generate a short 2-word header label from a system name."""
    n = name.upper().strip()
    if any(k in n for k in ("AEM", "EVENT MESH", "EVENT GRID")):
        return "EVENT MESH"
    if "PIGMA" in n:
        return "RELAY"
    if any(k in n for k in ("SFTP", "FTP")):
        return "SFTP"
    words = n.split()
    return " ".join(words[:2]) if words else "SYSTEM"
