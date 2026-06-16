#!/usr/bin/env python3
"""Orphan-number gate: every numeral in main.tex prose must map to a validation/claims.json
entry (any rounding/scale variant) or to a documented whitelist of structural constants.
Scans main.tex body only; \\input-ed tables are claim-derived by construction and excluded."""
import os, re, json, sys
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
TEX = os.path.join(ROOT, "paper/main.tex")
CLAIMS = os.path.join(ROOT, "validation/claims.json")

# structural constants that are not empirical results (documented, allowed)
WHITELIST = set()
WHITELIST |= {str(y) for y in range(2018, 2027)}      # data-range years
WHITELIST |= {"1","2","3","4","5"}                     # scaling/section/footnote indices, "Table 1".."Figure 2"
WHITELIST |= {"10"}                                    # the +10C / +10mm scaling unit
WHITELIST |= {"95"}                                    # confidence level
WHITELIST |= {"0.05","0.10","0.01"}                    # significance thresholds (.01/.05/.10)
WHITELIST |= {"11"}                                    # 11pt documentclass (preamble, but safe)

def claim_number_strings():
    data = json.load(open(CLAIMS))["claims"]
    out = set()
    def emit(x):
        try: v = float(x)
        except (TypeError, ValueError): return
        for s in (f"{v:.5f}", f"{v:.4f}", f"{v:.3f}", f"{v:.2f}", f"{v:.1f}", f"{v:g}",
                  f"{v*100:.3f}", f"{v*100:.2f}", f"{v*100:.1f}", f"{v*100:g}",
                  f"{abs(v):.4f}", f"{abs(v):.3f}", f"{abs(v):.2f}", f"{abs(v*100):.3f}", f"{abs(v*100):.2f}"):
            out.add(s.rstrip("0").rstrip(".") if "." in s else s)
            out.add(s)
    for c in data:
        for key in ("value","se","p","value_ppt","pct_of_baserate","bonferroni"):
            if key in c: emit(c[key])
        for key in ("ci","ci_t","ci_pct"):
            if key in c and isinstance(c[key], list):
                for x in c[key]: emit(x)
        # integer counts with thousands separators
        if isinstance(c.get("value"), int):
            out.add(f"{c['value']:,}"); out.add(str(c['value']))
    return out

def main():
    txt = open(TEX).read()
    body = txt.split(r"\begin{document}",1)[1]
    # strip comments
    body = re.sub(r"(?<!\\)%.*", "", body)
    # drop \input{...}, \includegraphics[...]{...}, \label{...}, \ref{...}, \cite{...}, \graphicspath
    body = re.sub(r"\\(input|includegraphics|label|ref|eqref|cite|graphicspath)(\[[^\]]*\])?\{[^}]*\}", " ", body)
    # drop file-extension tokens just in case
    body = re.sub(r"\b\w+\.(png|tex|pdf)\b", " ", body)
    # normalise thousands separators inside numbers (1{,}000 and 1,000)
    body = body.replace("{,}", ",")
    # find numerals: optional sign handled separately; capture digit groups with , and .
    nums = re.findall(r"\d[\d,]*(?:\.\d+)?", body)
    norm = []
    for n in nums:
        n2 = n.replace(",", "")
        norm.append((n, n2))
    allowed = claim_number_strings()
    # add comma + plain variants for ints
    orphans = []
    for raw, plain in norm:
        cands = {raw, plain, raw.replace(",",""), plain.rstrip("0").rstrip(".") if "." in plain else plain}
        # also the comma-grouped form
        if plain.isdigit():
            cands.add(f"{int(plain):,}")
        if cands & allowed or cands & WHITELIST:
            continue
        # numeric tolerance match against allowed floats (rounding)
        try:
            fv = float(plain)
            hit = any(abs(fv-float(a))<5e-3 for a in allowed if _isnum(a))
        except ValueError:
            hit = False
        if hit: continue
        orphans.append(raw)
    orphans = sorted(set(orphans))
    print(f"numerals scanned: {len(norm)}; distinct orphans: {len(orphans)}")
    if orphans:
        print("ORPHANS:", orphans)
        return 1
    print("ORPHAN CHECK: PASS — every numeral maps to a claim or whitelisted constant.")
    return 0

def _isnum(s):
    try: float(s); return True
    except ValueError: return False

if __name__ == "__main__":
    sys.exit(main())
