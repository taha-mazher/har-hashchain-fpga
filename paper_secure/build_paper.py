"""Builds the AEJ hash-chain manuscript from the author's last AEJ Word file (same journal template, same styles).

Template: ../../Paper Modified.docx (final revision of the published AEJ paper). Output: AEJ_cascade_paper.docx.
Text markup: {i:...} italic, {b:...} bold, {sub:...} subscript, {sup:...} superscript, [[key]] citation.
Citations are numbered in order of first appearance, as the AEJ guidelines require.
"""
import copy
import json
import os
import re

import docx
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Emu, Inches, Pt, RGBColor

HERE = os.path.dirname(os.path.abspath(__file__))
TEMPLATE = os.path.join(HERE, '..', '..', 'Paper Modified.docx')
OUT = os.environ.get('PAPER_OUT') or os.path.join(HERE, 'AEJ_hashchain_paper.docx')
REFS = json.load(open(os.path.join(HERE, 'refs.json'), encoding='utf-8'))
EXTRA_REFS = {
    'bmi160': 'Bosch Sensortec. 2015. BMI160 Small, Low Power Inertial Measurement Unit: Data Sheet. Document '
              'BST-BMI160-DS000-07, Revision 0.8. Reutlingen: Bosch Sensortec GmbH.',
    'fips180': 'National Institute of Standards and Technology. 2015. Secure Hash Standard (SHS). {i:Federal Information '
               'Processing Standards Publication} 180-4. Gaithersburg, MD: NIST. DOI: https://doi.org/10.6028/NIST.FIPS.180-4',
    'rfc2104': 'Krawczyk, H., M. Bellare, and R. Canetti. 1997. HMAC: Keyed-Hashing for Message Authentication. {i:RFC 2104}. '
               'Internet Engineering Task Force. DOI: https://doi.org/10.17487/RFC2104',
    'secworks': 'Strömbergson, J. 2013. sha256: Hardware Implementation of the SHA-256 Cryptographic Hash Function '
                '(Verilog source code, BSD license). Available: https://github.com/secworks/sha256',
    'ug472': 'Xilinx. 2018. {i:7 Series FPGAs Clocking Resources User Guide}. UG472 (v1.14). San Jose, CA: Xilinx Inc.',
    'mazher2026': 'Mazher, T., and M. S. Hussain. 2026. Sensor-Gated Early-Exit Neural Network on FPGA for Low-Power '
                  'Human Activity Recognition. Manuscript submitted to {i:ASEAN Engineering Journal}.',
}
FIX = {}

d = docx.Document(TEMPLATE)
for s in d.sections:   # running header still names the template's author
    for p in s.header.paragraphs + s.first_page_header.paragraphs + s.even_page_header.paragraphs:
        for r in p.runs:
            if 'Azizul' in r.text:   # setting .text on other runs would wipe the PAGE field
                r.text = r.text.replace('Azizul et al', 'Mazher et al')
body = d.element.body
B = list(body.iterchildren())
T = {k: copy.deepcopy(B[i]) for k, i in dict(h1=5, h2=22, h3=45, body=24, bullet=29, tcap=39, table=41, img=122,
                                              fcap=18, ref=386, sec2=155, sec1=170).items()}
final_sect = B[-1]
for el in B[5:-1]:
    body.remove(el)

order = []


def cite(m):
    keys = [k.strip() for k in m.group(1).split(',')]
    nums = []
    for k in keys:
        if k not in order:
            order.append(k)
        nums.append(order.index(k) + 1)
    return '[' + ', '.join(map(str, nums)) + ']'


def runs_from(text):
    """Split markup into (text, fmt) pieces."""
    text = re.sub(r'\[\[([^\]]+)\]\]', cite, text)
    out, pos = [], 0
    for m in re.finditer(r'\{(i|b|sub|sup):([^}]*)\}', text):
        if m.start() > pos:
            out.append((text[pos:m.start()], None))
        out.append((m.group(2), m.group(1)))
        pos = m.end()
    if pos < len(text):
        out.append((text[pos:], None))
    return out


def new_par(kind, text='', size=None, align=None, bold_all=False, color=None):
    el = copy.deepcopy(T[kind])
    rpr = None
    for r in el.findall(qn('w:r')):
        if rpr is None and r.find(qn('w:rPr')) is not None:
            rpr = copy.deepcopy(r.find(qn('w:rPr')))
        el.remove(r)
    for tag in ('w:hyperlink', 'm:oMath', 'm:oMathPara', 'w:bookmarkStart', 'w:bookmarkEnd', 'w:proofErr'):
        for x in el.findall(qn(tag)):
            el.remove(x)
    final_sect.addprevious(el)
    p = docx.text.paragraph.Paragraph(el, d._body)
    for piece, fmt in runs_from(text):
        r = p.add_run(piece)
        if rpr is not None:
            r._r.insert(0, copy.deepcopy(rpr))
        r.font.name = 'Calibri'
        if size:
            r.font.size = Pt(size)
        if color:
            r.font.color.rgb = RGBColor.from_string(color)
        r.bold = True if (bold_all or fmt == 'b') else (None if kind in ('h1', 'h2', 'h3') else False)
        if fmt == 'i':
            r.italic = True
        if fmt == 'sub':
            r.font.subscript = True
        if fmt == 'sup':
            r.font.superscript = True
    if align is not None:
        p.alignment = align
    return p


def spaced(p, before, after, justify=False):
    p.paragraph_format.space_before = Pt(before); p.paragraph_format.space_after = Pt(after)
    if justify:
        p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    return p


def h1(t): spaced(new_par('h1', t, size=11), 12, 4).paragraph_format.keep_with_next = True
def h2(t): spaced(new_par('h2', t, size=9), 8, 3).paragraph_format.keep_with_next = True
def h3(t): spaced(new_par('h3', t, size=9), 6, 2)
def para(t): spaced(new_par('body', t, size=9), 0, 6, justify=True)
def bullet(t): spaced(new_par('bullet', t, size=9), 0, 3, justify=True)


def equation(expr, num):
    p = new_par('body', '', size=9)
    pf = p.paragraph_format
    pf.tab_stops.add_tab_stop(Inches(1.68), alignment=1)   # center of a 3.36 in column
    pf.tab_stops.add_tab_stop(Inches(3.36), alignment=2)   # right
    for piece, fmt in runs_from('\t' + expr + '\t(' + str(num) + ')'):
        r = p.add_run(piece); r.font.size = Pt(9); r.font.name = 'Cambria Math' if fmt != 'sub' else 'Cambria Math'
        r.italic = fmt == 'i'
        r.font.subscript = fmt == 'sub'; r.font.superscript = fmt == 'sup'


def section(kind):
    el = copy.deepcopy(T[kind])
    for r in el.findall(qn('w:r')):
        el.remove(r)
    final_sect.addprevious(el)


TEXT_W = Emu(7772400 - 2 * 694690)     # page width minus margins (template)
_float_id = [1000]


def wide(*fns):
    """Full-width block at a subsection boundary: ends the two-column section, places the figures/tables across
    the page, then resumes two columns. Placed only where a subsection ends, so no paragraph is split by it."""
    section('sec2')
    for fn in fns:
        fn()
    section('sec1')


def caption(kind, label, num, text):
    p = new_par(kind, '', size=9, align=WD_ALIGN_PARAGRAPH.CENTER)
    p.paragraph_format.space_before = Pt(8 if label == 'Table' else 2)
    p.paragraph_format.space_after = Pt(4 if label == 'Table' else 8)
    r = p.add_run(f'{label} {num} '); r.bold = True; r.font.size = Pt(9); r.font.name = 'Calibri'
    for piece, fmt in runs_from(text):
        r = p.add_run(piece); r.font.size = Pt(9); r.font.name = 'Calibri'; r.italic = fmt == 'i'
        r.font.subscript = fmt == 'sub'; r.font.superscript = fmt == 'sup'


def figure(path, width_in, num, text):
    p = new_par('img', '', align=WD_ALIGN_PARAGRAPH.CENTER)
    p.add_run().add_picture(path, width=Inches(width_in))
    p.paragraph_format.space_before = Pt(6)
    caption('fcap', 'Figure', num, text)


def border(cell, sides, sz=8):
    tcpr = cell._tc.get_or_add_tcPr()
    b = tcpr.find(qn('w:tcBorders'))
    if b is None:
        b = OxmlElement('w:tcBorders'); tcpr.append(b)
    for s in ('top', 'left', 'bottom', 'right'):
        e = OxmlElement(f'w:{s}')
        if s in sides:
            e.set(qn('w:val'), 'single'); e.set(qn('w:sz'), str(sz)); e.set(qn('w:space'), '0'); e.set(qn('w:color'), 'auto')
        else:
            e.set(qn('w:val'), 'nil')
        b.append(e)


def table(num, title, rows, widths, fs=7.5, keep=False):
    caption('tcap', 'Table', num, title)
    if keep:
        list(body.iterchildren())[-2].find(qn('w:pPr')).append(OxmlElement('w:keepNext'))
    t = d.add_table(rows=len(rows), cols=len(rows[0]))
    t.alignment = 1
    t.autofit = False
    mar = OxmlElement('w:tblCellMar')
    for side, w in (('top', 40), ('left', 70), ('bottom', 40), ('right', 70)):
        e = OxmlElement(f'w:{side}'); e.set(qn('w:w'), str(w)); e.set(qn('w:type'), 'dxa'); mar.append(e)
    look = t._tbl.tblPr.find(qn('w:tblLook'))
    (look.addprevious(mar) if look is not None else t._tbl.tblPr.append(mar))
    for ri, row in enumerate(rows):
        for ci, val in enumerate(row):
            c = t.cell(ri, ci)
            c.width = Inches(widths[ci])
            p = c.paragraphs[0]
            p.alignment = WD_ALIGN_PARAGRAPH.LEFT if ci == 0 else WD_ALIGN_PARAGRAPH.CENTER
            p.paragraph_format.space_after = Pt(0); p.paragraph_format.space_before = Pt(0)
            if keep and ri < len(rows) - 1:
                p.paragraph_format.keep_with_next = True
            for piece, fmt in runs_from(str(val)):
                r = p.add_run(piece); r.font.size = Pt(fs); r.font.name = 'Calibri'
                r.bold = ri == 0 or fmt == 'b'; r.italic = fmt == 'i'
                r.font.subscript = fmt == 'sub'; r.font.superscript = fmt == 'sup'
            sides = []
            if ri == 0:
                sides = ['top', 'bottom']
            if ri == len(rows) - 1:
                sides.append('bottom')
            border(c, sides)
            if ri == 0:
                shd = OxmlElement('w:shd'); shd.set(qn('w:val'), 'clear'); shd.set(qn('w:color'), 'auto'); shd.set(qn('w:fill'), 'EDEDED')
                c._tc.get_or_add_tcPr().append(shd)
            c.vertical_alignment = 1
    final_sect.addprevious(t._tbl)
    spacer = new_par('body', '', size=4)



# ---------------------------------------------------------------- header block (title, authors, abstract)
hdr = d.tables[0]


def set_par(p, text, keep_first_fmt=True):
    runs = p.runs
    runs[0].text = text
    for r in runs[1:]:
        r._r.getparent().remove(r._r)


cells = {(ri, ci): hdr.cell(ri, ci) for ri in range(len(hdr.rows)) for ci in range(len(hdr.columns))}
title_cell = hdr.cell(3, 0)
set_par(title_cell.paragraphs[0], 'Tamper-Evident Activity Logging on FPGA: A SHA-256 Hash Chain for an Early-Exit '
                                  'Wearable Classifier')
set_par(title_cell.paragraphs[2], 'Taha Mazher*, Mohammed Sabir Hussain')
abs_cell = hdr.cell(5, 2)
ABSTRACT = (
    'Activity records from wearable sensors are used in health monitoring and safety-critical work, yet a record '
    'stored on the device and uploaded later can be edited without trace. This paper adds a tamper-evident log to an '
    'FPGA activity classifier. Every 1.28 s, the class decided by an early-exit cascade, its sensor-control flags and a '
    'window number are folded into a SHA-256 hash chain, the linking structure used by blockchains. Three modes are '
    'provided: a plain chain, a keyed chain using HMAC-SHA256, and a forward-secure chain whose key '
    'is replaced by its own hash after every window, so a key extracted from a captured device cannot re-sign '
    'earlier records. A low-area SHA-256 core keeps the message schedule in shift-register lookup tables. On a Xilinx '
    'Artix-7 at 50 MHz the design was verified bit-exact at gate level; it uses 1,101 to '
    '1,716 LUTs and spends 18.8 to 105 nJ per window on hashing. Without clock gating the idle clock costs up to '
    '1.68 mJ per window, as much as the gyroscope energy the cascade saves; with gating, idle power falls to 0.059 mW '
    'in every mode. In tamper tests every edit, deletion and reordering was located at the exact window.')
KEYWORDS = ('Hash chain, SHA-256, HMAC, forward security, FPGA, human activity recognition, tamper-evident logging, '
            'clock gating')

set_par(abs_cell.paragraphs[2], ABSTRACT)
kp = abs_cell.paragraphs[4]
kp.runs[0].text = 'Keywords'
kp.runs[1].text = ': '
kp.runs[2].text = KEYWORDS
for r in kp.runs[3:]:
    r._r.getparent().remove(r._r)

# graphical abstract: replace the template picture(s) with the architecture figure, keeping the frame width
ga = os.path.join(HERE, 'fig_ga.png')
from PIL import Image
gw, gh = Image.open(ga).size
for blip in hdr._tbl.iter(qn('a:blip')):
    rid = blip.get(qn('r:embed'))
    d.part.related_parts[rid]._blob = open(ga, 'rb').read()
for inline in hdr._tbl.iter(qn('wp:extent')):
    cx = int(inline.get('cx'))
    inline.set('cy', str(int(cx * gh / gw)))
for ext in hdr._tbl.iter(qn('a:ext')):
    if ext.get('cx'):
        cx = int(ext.get('cx')); ext.set('cy', str(int(cx * gh / gw)))


# ---------------------------------------------------------------- body
h1('1.0  INTRODUCTION')
para('Human activity recognition (HAR) from body-worn inertial sensors supports health monitoring, rehabilitation '
     'and the supervision of people in hazardous work [[lara2013]]. Its output is increasingly a record that other '
     'people rely on: a clinician reviewing a patient’s activity, or an employer checking that a worker was not '
     'immobile. Data from connected devices is therefore being given the integrity guarantees of a ledger '
     '[[christidis2016, dorri2017]], and in medicine blockchains have been proposed to manage access to patient '
     'records [[azaria2016]]. A wearable, however, usually stores its results in local memory or on a paired phone '
     'and uploads them later, and anyone with access to that storage, including the wearer, can change them.')
para('A hash chain makes such changes visible. Haber and Stornetta linked documents by including the hash of each '
     'document in the next [[haber1991]], the structure that blockchains later adopted [[christidis2016]]. For logs '
     'kept on a machine that may later be compromised, Schneier and Kelsey added a secret key that evolves after '
     'every entry [[schneier1999]], Bellare and Yee formalised this property as forward security [[bellare2003]], and '
     'Ma and Tsudik extended it to aggregate signatures [[ma2009]]. These schemes were designed for software on '
     'general-purpose computers.')
para('Hardware SHA-256 has been studied extensively on FPGAs. Santos {i:et al.} proposed cores for Internet of '
     'Things devices in a blockchain context [[santos2024]], Kieu-Do-Nguyen {i:et al.} targeted power efficiency in '
     'embedded applications [[kieu2021]], Kammoun {i:et al.} explored hardware and software partitioning [[kammoun2021]], '
     'and compact and folded architectures reduce area further [[garcia2014, wong2018]]. These cores are evaluated as '
     'stand-alone hash engines, by area and throughput. Meanwhile, FPGA classifiers for HAR [[gaikwad2019, hussain2026]] '
     'and our sensor-gated early-exit cascade [[mazher2026]] produce a class for every window but do nothing to '
     'protect it. To the best of our knowledge, no prior work secures the output log of a hardware HAR classifier, '
     'or reports the energy of hashing per logged decision including the idle time between decisions.')
para('This paper adds a tamper-evident log to the cascade of [[mazher2026]]. The contributions are:')
bullet('A hardware hash chain with one SHA-256 link per classified window, in three modes selected by a parameter: '
       'plain, keyed with HMAC-SHA256, and forward-secure with a key that evolves after every window.')
bullet('A low-area SHA-256 core whose message schedule maps to shift-register lookup tables, compared under the same '
       'tool flow with a standard core and an open-source core, and with published results.')
bullet('Bit-exact verification of the complete design at gate level, implementation results on an Artix-7, and an '
       'energy analysis that includes the idle time between windows, which shows that clock gating is required and '
       'that, once gated, the strongest mode costs no more than the weakest while idle.')
bullet('A tamper evaluation with six attacks that shows what each mode, with and without an external anchor, detects.')

h1('2.0  METHODOLOGY')
h2('2.1  System Overview')
para('Figure 1 shows the design. The classifier is the two-stage cascade of [[mazher2026]]: a 7-6-5 ReLU6 '
     'multilayer perceptron [[hussain2026]] classifies every window from accelerometer features and, when it is '
     'unsure, powers a gyroscope and runs a second network. For each window it outputs the activity class {i:c} '
     '(three bits), the sensor-enable state {i:e} and a flag {i:s} that records whether the second stage answered. '
     'Windows are 2.56 s long with 50% overlap, so one result arrives every 1.28 s. The logging hardware is added '
     'behind the classifier and leaves it unchanged; a record builder forms one record per window, a sequencer drives '
     'a SHA-256 core, and the chain register holds the latest hash, which can be published to an anchor outside the '
     'device.')
wide(lambda: figure(os.path.join(HERE, 'fig_arch.png'), 6.2, 1,
                    'Architecture of the tamper-evident classifier. The dashed arrow is used only in the '
                    'forward-secure mode; the clock gate stops the clock of the whole design between windows'))

h2('2.2  Record and Hash Chain')
para('The record of window {i:n} concatenates the previous hash, the window number and one byte holding the result:')
equation('{i:r}{sub:n} = {i:h}{sub:n−1} ‖ {i:n} ‖ (000 ‖ {i:c} ‖ {i:e} ‖ {i:s})', 1)
equation('{i:h}{sub:n} = SHA-256({i:r}{sub:n}),   {i:h}{sub:−1} = 0', 2)
para('The record is 37 bytes (296 bits). With the padding of the Secure Hash Standard [[fips180]], one bit and a 64-bit '
     'length, it fits a single 512-bit block, so each window costs one compression. The window number makes the '
     'deletion or reordering of windows with identical results detectable. A verifier recomputes the chain from the '
     'start, and the first window whose hash differs from the stored one locates the change. Removing records from '
     'the end, however, leaves a shorter chain that is still valid. Truncation can only be detected if the latest '
     'hash, or the number of windows, has been published outside the device; this external anchor is the role that a '
     'timestamping service [[haber1991]] or a blockchain [[christidis2016]] plays. The chain restarts at each '
     'recording.')

h2('2.3  Keyed and Forward-Secure Modes')
para('Anyone who can edit a plain chain can also recompute every later hash. The keyed mode prevents this with '
     'HMAC-SHA256 [[bellare1996, rfc2104]] under a device key {i:K}:')
equation('{i:h}{sub:n} = H(({i:K} ⊕ opad) ‖ H(({i:K} ⊕ ipad) ‖ {i:r}{sub:n}))', 3)
para('Because {i:K} is fixed, the compression of each padded key block is computed at build time and stored as a '
     'constant midstate, so each window needs two compressions: the inner hash from the ipad midstate and the outer '
     'hash from the opad midstate. The inner hash is held in the previous-hash register, which the first pass no '
     'longer needs, so the keyed mode adds no 256-bit register.')
para('A key that never changes can be read out of a captured device and used to re-sign the whole log. The '
     'forward-secure mode, following [[schneier1999, bellare2003]], replaces the key after every window:')
equation('{i:h}{sub:n} = HMAC({i:k}{sub:n}, {i:r}{sub:n}),   {i:k}{sub:n+1} = SHA-256({i:k}{sub:n}),   {i:k}{sub:0} = {i:K}', 4)
para('The old key is overwritten, and because SHA-256 is one-way, a key read at window {i:t} gives no way to compute '
     'the keys of earlier windows. The midstates now change every window, so five compressions are needed: the two '
     'padded key blocks, the inner and outer hashes, and the key update. Table 1 summarises the three modes.')
table(1, 'Chain modes', [
    ['Mode', 'Compressions per window', 'Added registers', 'Stops re-signing without the key', 'Stops re-signing after capture'],
    ['Plain', '1', 'None', 'No', 'No'],
    ['Keyed (HMAC)', '2', 'None', 'Yes', 'No'],
    ['Forward-secure', '5', 'Key {i:k}, scratch {i:r} (512 bits)', 'Yes', 'Yes, for earlier windows'],
], [0.72, 0.83, 0.7, 0.6, 0.6], fs=7, keep=True)

h2('2.4  SHA-256 Cores')
para('Two cores were written, both computing the compression function of [[fips180]] at one round per clock cycle. '
     'The standard core loads the 512-bit block into a 16-word shift register that produces the message schedule '
     'and registers its output; it takes 66 cycles. The low-area core removes both copies. In rounds 0 to 15 it '
     'reads the message words directly from the block input, which the sequencer holds stable, so the schedule '
     'becomes a 16-word delay line without a parallel load, which the synthesis tool maps to shift-register lookup '
     'tables (SRL). Its output, the sum of the input hash and the working state, is combinational, because the chain '
     'already keeps the result in its own register. It takes 65 cycles. For comparison, the open-source SHA-256 core '
     'of [[secworks]] was implemented with the same tool flow.')

h2('2.5  Integration and Clock Gating')
para('The sequencer counts the compressions of each window and selects, for each one, the input hash (the '
     'standard initial value, a midstate, or an intermediate result) and the block. Results are written to the '
     'previous-hash register, to the scratch register {i:r} or to the key register. The latest hash is ready 67, '
     '133 or 331 cycles after the class, or 1.34, 2.66 or 6.62 µs at 50 MHz, against 1.28 s between windows, so one '
     'record in flight is sufficient. The hash is read as eight 32-bit words through a select input so that the '
     'design fits the pins of the package.')
para('Between windows the design has nothing to do, but a free-running clock still toggles every register. Clock '
     'gating [[wu2000]] removes this cost: a single BUFGCE global clock buffer [[ug472]] passes the clock only while '
     'features are arriving, the classifier or the hash core is busy, or a one-cycle flag has to clear. The enable '
     'is the OR of eight status signals, and the gate stops the clock of the whole design, classifier included.')

h2('2.6  Verification and Implementation')
para('A Python model built the plain, keyed and forward-secure chains for every window with the standard hashlib '
     'and hmac libraries. A separately written compression function, checked against those libraries, produced 207 '
     'single-block test vectors for the cores and the 280-window chain of the first UCI-HAPT test recording. The RTL '
     'was simulated with Icarus Verilog. The complete design was compared on all eight hash words of every window '
     'for nine classifier models, namely the UCI-HAPT [[reyes2016]] official split and the eight PAMAP2 [[reiss2012]] '
     'leave-one-subject-out folds of [[mazher2026]], with both cores, all three modes, and with and without clock '
     'gating: 108 configurations in all.')
para('The design was implemented with Vivado 2024.2 for the Xilinx Artix-7 xc7a35ticsg324-1L at 50 MHz. The cores '
     'were implemented on their own, out of context. For the complete UCI-HAPT design, the post-implementation netlist '
     'was simulated on the 5,053 test windows with every hash word checked, and power was estimated from the recorded '
     'switching activity. In this run windows follow each other without pause, so dynamic power multiplied by the '
     'simulated time and divided by the number of windows gives the active energy per window. Idle power was '
     'estimated from the same netlist held idle for 20,000 cycles after reset. The energy per classification in '
     'operation is the active energy plus the idle power multiplied by 1.28 s. Vivado ignored the enable of the '
     'BUFGCE and the recorded activity of the gated clock net, and reported the same idle power with and without '
     'gating; for the gated idle runs, the stopped clock was therefore modelled as a generated clock at one millionth '
     'of the input frequency. This is a modelling assumption and is listed among the limitations.')

h1('3.0  RESULTS AND DISCUSSION')
h2('3.1  Tamper Detection')
para('Table 2 applies six attacks to the first UCI-HAPT test recording (280 windows) and reports the first window '
     'at which verification fails. Changing one class, deleting one window and swapping two windows were located at '
     'the exact window in every mode. Dropping the last ten windows was missed in every mode without an anchor; with '
     'an anchor, the published hash no longer matches and the log is rejected, although the missing records cannot '
     'be recovered. An attacker who changes window 100 and recomputes every later hash defeats the plain chain; '
     'an anchor detects this only at the end of the log, while the keyed and forward-secure chains fail from the first '
     'window, because the attacker’s chain was computed without the key. Finally, an attacker who captures the device '
     'at window 200 and reads its key can rewrite window 100 in the keyed chain without detection. In the '
     'forward-secure chain the key held at window 200 cannot produce the key of window 100, so the change is located '
     'exactly.')
wide(lambda: table(2, 'First window at which verification fails, for attacks on a 280-window UCI-HAPT recording. '
                      'Anchor: the latest hash was published outside the device', [
    ['Attack', 'Plain', 'Plain + anchor', 'Keyed', 'Keyed + anchor', 'Forward-secure', 'Forward-secure + anchor'],
    ['Change the class of window 100', '100', '100', '100', '100', '100', '100'],
    ['Delete window 100', '100', '100', '100', '100', '100', '100'],
    ['Swap windows 114 and 115', '114', '114', '114', '114', '114', '114'],
    ['Drop the last 10 windows', 'Missed', '269 (end)', 'Missed', '269 (end)', 'Missed', '269 (end)'],
    ['Change window 100 and recompute all hashes without the key', 'Missed', '279 (end)', '0', '0', '0', '0'],
    ['Capture the device at window 200, read the key, change window 100', 'Missed', '279 (end)', 'Missed', '279 (end)', '100', '100'],
], [2.35, 0.55, 0.75, 0.55, 0.75, 0.75, 0.9], fs=7.5, keep=True))

h2('3.2  SHA-256 Cores')
para('Table 3 compares the cores. Under the same flow, the standard core occupies 273 slices against 409 for the '
     'open-source core of [[secworks]], and is smaller than the 327 slices reported for [[kieu2021]] on a similar '
     'device. The low-area core cuts flip-flops by 58%, from 1,033 to 431, but occupies 26 more slices, because the '
     'design is limited by lookup tables rather than registers: the 256-bit addition of the input hash alone needs '
     'about 256 of them. The compact processor of [[garcia2014]] is smaller still, at 139 slices, with a lower '
     'throughput. Results on other device families, and slices in particular, are not directly comparable. All of '
     'these cores are far faster than the application requires: one block per 1.28 s is 400 bit/s.')
wide(lambda: table(3, 'SHA-256 cores. This work and the open-source core were implemented out of context with the '
                      'same flow (Artix-7 xc7a35t, Vivado 2024.2); the maximum frequency is estimated from the slack at '
                      '50 MHz. Other figures are as reported in [[santos2024]]', [
    ['Core', 'Device', 'Slices', 'LUTs', 'Flip-flops', 'Max. frequency (MHz)', 'Cycles per block', 'Throughput (Mbit/s)'],
    ['This work, standard', 'Artix-7', '273', '1,011', '1,033', '83.9', '66', '651'],
    ['This work, low-area', 'Artix-7', '299', '1,058', '431', '66.1', '65', '520'],
    ['Open-source core [[secworks]]', 'Artix-7', '409', '1,430', '1,054', '67.1', '67', '513'],
    ['Santos {i:et al.} [[santos2024]], one core', 'Virtex-6', '1,933', '6,730', '794', '12.67', '65', '100'],
    ['Kieu-Do-Nguyen {i:et al.} [[kieu2021]]', 'Artix-7 / Zynq-7000', '327', 'n/a', 'n/a', '141.84', 'n/a', '1,404'],
    ['Kammoun {i:et al.} [[kammoun2021]]', 'Zynq-7000', '1,305', 'n/a', 'n/a', '135', 'n/a', '1,063'],
    ['García {i:et al.} [[garcia2014]]', 'Virtex-5', '139', 'n/a', 'n/a', '64.45', 'n/a', '118'],
], [1.9, 0.95, 0.5, 0.5, 0.6, 0.75, 0.65, 0.75], fs=7.5),
     lambda: table(4, 'Complete design, UCI-HAPT model, on the Xilinx Artix-7 xc7a35ticsg324-1L at 50 MHz (Vivado '
                      '2024.2). Power is estimated from gate-level switching activity', [
    ['Design', 'SHA-256 core', 'LUTs', 'Flip-flops', 'Slices', 'Worst slack (ns)', 'Power, total (dynamic) (mW)', 'Hashing energy per window (nJ)', 'Idle power, dynamic (mW)'],
    ['Classifier only [[mazher2026]]', 'None', '358', '286', '126', '+5.63', '63.1 (2.8)', 'n/a', 'n/a'],
    ['Plain', 'Standard', '1,143', '1,529', '396', '+5.37', '68.6 (8.3)', '19.8', 'n/a'],
    ['Plain', 'Low-area', '1,101', '1,006', '376', '+5.13', '68.6 (8.2)', '18.8', '0.906'],
    ['Keyed', 'Standard', '1,261', '1,534', '403', '+6.02', '70.5 (10.1)', '38.3', 'n/a'],
    ['Keyed', 'Low-area', '1,228', '1,010', '384', '+4.95', '70.7 (10.3)', '38.0', '0.925'],
    ['Forward-secure', 'Low-area', '1,716', '1,532', '534', '+4.98', '74.8 (14.4)', '105.2', '1.315'],
    ['Plain, clock gated', 'Low-area', '1,101', '1,005', '382', '+5.35', '68.6 (8.3)', '18.9', '0.059'],
    ['Keyed, clock gated', 'Low-area', '1,235', '1,011', '408', '+4.76', '70.8 (10.4)', '38.0', '0.059'],
    ['Forward-secure, clock gated', 'Low-area', '1,718', '1,531', '545', '+4.78', '74.9 (14.5)', '106.5', '0.059'],
], [1.6, 0.65, 0.45, 0.6, 0.45, 0.6, 0.9, 0.8, 0.75], fs=7.5, keep=True))

h2('3.3  Complete Design')
para('All eight complete designs matched the Python model on every hash word of all 5,053 test windows in '
     'post-implementation simulation, and all 108 RTL configurations matched on every window of the UCI-HAPT and '
     'PAMAP2 models. Table 4 lists the implementation results for the UCI-HAPT model. Inside the complete design the '
     'low-area core is better on every measure: the plain chain needs 1,101 LUTs and 1,006 flip-flops against 1,143 '
     'and 1,529 with the standard core, whose schedule and output registers duplicate data that the sequencer and the '
     'chain register already hold. The keyed mode adds 127 LUTs and 4 flip-flops to the plain chain, because the '
     'midstates are constants and the inner hash reuses the previous-hash register. The forward-secure mode adds 615 '
     'LUTs and 526 flip-flops, for the key and scratch registers and the wider block selection. Clock gating adds at '
     'most 24 slices. Every design meets timing at 50 MHz with at least 4.76 ns of slack. Total power is 68.6 to '
     '74.9 mW, of which about 60 mW is static power of the device.')


h2('3.4  Energy per Classification')
para('Figure 2 places the energy of hashing beside the energy that the cascade saves. Hashing one window costs 18.8 '
     'nJ in the plain mode, 38.0 nJ in the keyed mode and 105 nJ in the forward-secure mode, against 6.2 nJ for the '
     'classification itself. These active energies are small next to the idle time. Without gating, the clock '
     'running for the 1.28 s between windows costs 0.906 to 1.315 mW of dynamic power, or 1.16 to 1.68 mJ per '
     'classification, four orders of magnitude more than the hashing.')
para('The cascade exists to keep the gyroscope off. With the currents of [[bmi160]] and an assumed 1.8 V supply, each '
     'window in which the gyroscope stays off saves 745 µA × 1.8 V × 1.28 s = 1.72 mJ. Without clock gating, the '
     'idle clock of the logging design would therefore consume 67 to 98% of the energy that the cascade saves. With '
     'gating, idle power falls to 0.059 mW, or 0.076 mJ per classification, 4.4% of the saving. Idle power is the '
     'same in all three modes, because no mode-specific logic toggles once the clock stops. The forward-secure mode '
     'then costs about 86 nJ per window more than the plain mode, about 0.1% of the gated idle energy, so the '
     'strongest protection is practically free.')
wide(lambda: figure(os.path.join(HERE, 'fig_energy.png'), 5.3, 2,
                    'Dynamic energy per classification for the UCI-HAPT model (log scale). Active bars are for one '
                    'window; idle bars are idle power over the 1.28 s between windows; the last bar is the energy saved '
                    'in each window in which the cascade keeps the gyroscope off'))

h2('3.5  Limitations')
para('All results come from simulation and Vivado estimates; nothing was measured on a board. The static power of '
     'the Artix-7, about 60 mW or 77 mJ per classification, is larger than every dynamic figure in this paper, so '
     'the energy results apply to the logic itself and matter on devices with low static power, such as flash-based '
     'FPGAs or ASICs [[kuon2007]]. The gated idle power depends on the modelling step described in Section 2.6. The '
     'key is a build-time constant; a deployed device would keep it in one-time-programmable or secure storage, and '
     'the forward-secure key in non-volatile memory across power cycles. Physical attacks such as side-channel '
     'analysis and fault injection, and the protocol for publishing the anchor, are outside the scope of this work. '
     'As in [[gaikwad2019, mazher2026]], features are computed outside the FPGA.')

h1('4.0  CONCLUSION')
para('This paper added a tamper-evident log to an FPGA activity classifier: every window’s result is folded into a '
     'SHA-256 hash chain in plain, keyed or forward-secure mode. The complete design was verified bit-exact at gate '
     'level and occupies 1,101 to 1,716 LUTs on an Artix-7 at 50 MHz. In tamper tests every edit, deletion and '
     'reordering was located at the exact window; truncation required an external anchor in every mode; and only the '
     'forward-secure mode resisted an attacker who captured the device and its key. Hashing costs 18.8 to 105 nJ per '
     'window, but the idle clock between windows costs up to 1.68 mJ, as much as the gyroscope energy the cascade '
     'saves. With clock gating, idle power is 0.059 mW in every mode, so the strongest protection costs practically '
     'the same as none. Future work will measure power on a board, implement the anchor protocol, and move the design '
     'to a device with low static power.')

new_par('body', 'Acknowledgement', size=9, bold_all=True, color='943634')
para('The authors thank the Department of Electronics and Communication Engineering, Muffakham Jah College of '
     'Engineering and Technology, for its support.')
new_par('body', 'References', size=9, bold_all=True, color='943634')
for n, k in enumerate(order, 1):
    if k in EXTRA_REFS:
        text = EXTRA_REFS[k]
    else:
        r = dict(REFS[k], **FIX.get(k, {}))
        vip = r['vip'].lstrip(': ').strip()
        if r['vip'].startswith(':'):
            vip = 'pp. ' + vip
        au = r['authors'] if r['authors'].endswith('.') else r['authors'] + '.'
        text = f"{au} {r['year']}. {r['title']}. {{i:{r['venue']}}}." + (f" {vip}." if vip else '') + \
               f" DOI: https://doi.org/{r['doi']}"
    p = new_par('ref', '', size=9); p.alignment = WD_ALIGN_PARAGRAPH.LEFT
    rr = p.add_run(f'[{n}]'); rr.font.size = Pt(9); rr.font.name = 'Calibri'
    p.add_run('\t')
    for piece, fmt in runs_from(text):
        rr = p.add_run(piece); rr.font.size = Pt(9); rr.font.name = 'Calibri'; rr.italic = fmt == 'i'

unused = set(REFS) | set(EXTRA_REFS)
d.save(OUT)
print('saved', OUT)
print('references:', len(order), 'unused:', sorted(unused - set(order)))
print('abstract words:', len(ABSTRACT.split()))
