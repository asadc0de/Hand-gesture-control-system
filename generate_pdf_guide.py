import os
import sys
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, KeepTogether, HRFlowable
)
from reportlab.pdfgen import canvas

class NumberedCanvas(canvas.Canvas):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_number(num_pages)
            super().showPage()
        super().save()

    def draw_page_number(self, page_count):
        self.saveState()
        self.setFont("Helvetica", 8)
        self.setFillColor(colors.HexColor("#64748B"))
        
        # Header (on pages > 1)
        if self._pageNumber > 1:
            self.drawString(36, A4[1] - 25, "Hand Gesture Control System - Client Architecture & User Guide")
            self.setStrokeColor(colors.HexColor("#E2E8F0"))
            self.setLineWidth(0.5)
            self.line(36, A4[1] - 28, A4[0] - 36, A4[1] - 28)

        # Footer
        footer_text = f"Page {self._pageNumber} of {page_count}"
        self.drawRightString(A4[0] - 36, 20, footer_text)
        self.drawString(36, 20, "Confidential - Project Documentation")
        self.setStrokeColor(colors.HexColor("#E2E8F0"))
        self.setLineWidth(0.5)
        self.line(36, 28, A4[0] - 36, 28)
        self.restoreState()


def create_client_guide(output_pdf_path):
    doc = SimpleDocTemplate(
        output_pdf_path,
        pagesize=A4,
        leftMargin=36,
        rightMargin=36,
        topMargin=36,
        bottomMargin=36
    )

    styles = getSampleStyleSheet()

    # Custom styles
    primary_color = colors.HexColor("#0F2942")     # Deep Corporate Navy
    secondary_color = colors.HexColor("#1E40AF")   # Royal Blue
    accent_color = colors.HexColor("#0D9488")      # Teal / Accent
    dark_text = colors.HexColor("#1E293B")
    muted_text = colors.HexColor("#475569")
    bg_light = colors.HexColor("#F8FAFC")
    bg_alt = colors.HexColor("#F1F5F9")
    border_color = colors.HexColor("#CBD5E1")

    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=20,
        leading=24,
        textColor=primary_color,
        spaceAfter=4
    )

    subtitle_style = ParagraphStyle(
        'DocSubtitle',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=10,
        leading=14,
        textColor=muted_text,
        spaceAfter=12
    )

    h1_style = ParagraphStyle(
        'SectionH1',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=13,
        leading=17,
        textColor=primary_color,
        spaceBefore=10,
        spaceAfter=6,
        keepWithNext=True
    )

    h2_style = ParagraphStyle(
        'SectionH2',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=10.5,
        leading=14,
        textColor=secondary_color,
        spaceBefore=8,
        spaceAfter=4,
        keepWithNext=True
    )

    body_style = ParagraphStyle(
        'BodyDark',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8.5,
        leading=12,
        textColor=dark_text,
        spaceAfter=4
    )

    body_bold = ParagraphStyle(
        'BodyBold',
        parent=body_style,
        fontName='Helvetica-Bold'
    )

    callout_text = ParagraphStyle(
        'CalloutText',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8.5,
        leading=12,
        textColor=colors.HexColor("#0F3E5D")
    )

    table_header = ParagraphStyle(
        'TableHeader',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=8.5,
        leading=11,
        textColor=colors.white
    )

    table_cell = ParagraphStyle(
        'TableCell',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8,
        leading=10.5,
        textColor=dark_text
    )

    table_cell_bold = ParagraphStyle(
        'TableCellBold',
        parent=table_cell,
        fontName='Helvetica-Bold',
        textColor=primary_color
    )

    code_pill = ParagraphStyle(
        'CodePill',
        parent=styles['Normal'],
        fontName='Courier-Bold',
        fontSize=8,
        leading=10,
        textColor=colors.HexColor("#0F172A")
    )

    story = []

    # Title Banner Block
    banner_data = [
        [
            Paragraph("AI-Powered Hand Gesture Control System", title_style),
        ],
        [
            Paragraph("Comprehensive Client Project Guide: Architecture, Technology Stack, Folder Structure & Setup Manual", subtitle_style),
        ]
    ]
    banner_table = Table(banner_data, colWidths=[A4[0] - 72])
    banner_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor("#F0F7FF")),
        ('BOX', (0, 0), (-1, -1), 1, colors.HexColor("#BAE6FD")),
        ('PADDING', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
    ]))
    story.append(banner_table)
    story.append(Spacer(1, 10))

    # Executive Overview
    story.append(Paragraph("1. Project Executive Overview (Ye Project Kya Hai?)", h1_style))
    overview_text = (
        "Yeh project ek <b>AI & Computer Vision based Touchless Computer Interface</b> hai. "
        "Yeh regular webcam ke zariye user ke hath ke ishare (hand gestures) detect karta hai aur physical "
        "mouse ya keyboard touch kiye baghair operating system ko control karta hai. Is system ke zariye mouse pointer "
        "movement, clicks, drag & drop, scrolling, window minimize/restore, volume/brightness control, presentation mode, "
        "aur screenshot/lock actions seamlessly execute hote hain. Saath hi isme ek standalone <b>Interactive Hand-Tracking Fruit Ninja Game</b> "
        "aur bina Python ke chalne wala <b>Windows Executable (.exe)</b> package bhi shamil hai."
    )
    story.append(Paragraph(overview_text, body_style))
    story.append(Spacer(1, 6))

    # Technologies Used & Why
    story.append(Paragraph("2. Technologies Used & Why (Kaunsi Tech Use Hui Aur Kyun?)", h1_style))
    tech_data = [
        [Paragraph("Technology / Library", table_header), Paragraph("Role in Project", table_header), Paragraph("Kyun Use Ki Gai? (Technical Rationale)", table_header)],
        [
            Paragraph("<b>Python 3.10+</b>", table_cell),
            Paragraph("Core Programming Language", table_cell),
            Paragraph("Computer vision aur rapid AI prototyping ke liye industry standard aur rich ecosystem.", table_cell)
        ],
        [
            Paragraph("<b>Google MediaPipe</b>", table_cell),
            Paragraph("Hand Landmark Detection (AI)", table_cell),
            Paragraph("Ultra-fast real-time ML pipeline jo 21 precise 3D joints per hand nikalta hai without heavy GPU requirement.", table_cell)
        ],
        [
            Paragraph("<b>OpenCV (cv2)</b>", table_cell),
            Paragraph("Camera Feed & Image Processing", table_cell),
            Paragraph("Low-latency webcam streaming, horizontal mirroring, color conversion (BGR to RGB), aur visual HUD overlay.", table_cell)
        ],
        [
            Paragraph("<b>PyAutoGUI</b>", table_cell),
            Paragraph("OS-Level Mouse & Keyboard Emulation", table_cell),
            Paragraph("Cross-platform OS cursor navigation, single/double clicks, drag & drop, screenshots, aur hotkeys.", table_cell)
        ],
        [
            Paragraph("<b>PyGetWindow & Win32 API</b>", table_cell),
            Paragraph("Window State Management", table_cell),
            Paragraph("Open desktop applications ko background me minimize karna, stack me save rakhna aur restore karna.", table_cell)
        ],
        [
            Paragraph("<b>PyCaw & Comtypes</b>", table_cell),
            Paragraph("Hardware Audio Volume Control", table_cell),
            Paragraph("Windows Core Audio Endpoint ke direct decibels control karna gesture ke zariye without delay.", table_cell)
        ],
        [
            Paragraph("<b>Screen-Brightness-Control</b>", table_cell),
            Paragraph("Monitor Display Brightness", table_cell),
            Paragraph("Monitor backlight brightness ko thumb-index distance se 0% se 100% smooth scale karna.", table_cell)
        ],
        [
            Paragraph("<b>Pygame</b>", table_cell),
            Paragraph("Bonus Fruit Ninja Game Engine", table_cell),
            Paragraph("60 FPS physics, fruit slicing animations, particle splash effects, aur procedural audio synthesis.", table_cell)
        ],
        [
            Paragraph("<b>PyInstaller</b>", table_cell),
            Paragraph("Standalone .EXE Packaging", table_cell),
            Paragraph("Client ko portable Windows executable provide karna taake bina Python install kiye project chal sake.", table_cell)
        ]
    ]

    col_widths_tech = [110, 130, A4[0] - 72 - 240]
    tech_table = Table(tech_data, colWidths=col_widths_tech, repeatRows=1)
    tech_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), secondary_color),
        ('GRID', (0, 0), (-1, -1), 0.5, border_color),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('PADDING', (0, 0), (-1, -1), 4),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, bg_alt]),
    ]))
    story.append(tech_table)
    story.append(Spacer(1, 10))

    # High-level architecture pipeline
    story.append(Paragraph("3. Processing Pipeline (Data Flow Architecture)", h1_style))
    pipeline_data = [
        [
            Paragraph("<b>Step 1: Webcam Feed</b><br/><font color='#475569'>OpenCV se 640x480 resolution frame capture hota hai.</font>", table_cell),
            Paragraph("<b>Step 2: Preprocessing</b><br/><font color='#475569'>Frame mirror flip hota hai aur RGB color space me badalta hai.</font>", table_cell),
            Paragraph("<b>Step 3: AI Detection</b><br/><font color='#475569'>MediaPipe se 21 hand landmarks aur Left/Right label nikalte hain.</font>", table_cell),
            Paragraph("<b>Step 4: Classification & Smoothing</b><br/><font color='#475569'>Geometric rules se gesture pehchana jata hai aur jitter smooth hota hai.</font>", table_cell),
            Paragraph("<b>Step 5: OS Action Execution</b><br/><font color='#475569'>PyAutoGUI / Win32 se cursor, clicks ya window commands execute hote hain.</font>", table_cell),
        ]
    ]
    pipe_table = Table(pipeline_data, colWidths=[(A4[0] - 72)/5]*5)
    pipe_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor("#EFF6FF")),
        ('BOX', (0, 0), (-1, -1), 1, colors.HexColor("#93C5FD")),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#BFDBFE")),
        ('PADDING', (0, 0), (-1, -1), 5),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
    ]))
    story.append(pipe_table)
    story.append(Spacer(1, 12))

    story.append(PageBreak())

    # Folder & File Structure
    story.append(Paragraph("4. Project Structure & File-by-File Purpose", h1_style))
    story.append(Paragraph("Har folder aur file ka short aur asaan lafzon me maqsad neeche darj hai:", body_style))
    story.append(Spacer(1, 4))

    # Root Files Table
    story.append(Paragraph("A. Root Directory Files", h2_style))
    root_data = [
        [Paragraph("File Name", table_header), Paragraph("Role / Purpose (Asaan Matlab)", table_header)],
        [Paragraph("<b>main.py</b>", table_cell_bold), Paragraph("<b>Main Entry Point:</b> Poore system ka central loop jo camera, AI detector, gesture recognition aur OS controllers ko aapas me connect karta hai.", table_cell)],
        [Paragraph("<b>requirements.txt</b>", table_cell_bold), Paragraph("<b>Libraries List:</b> Project ke tamam zaroori Python packages ki list jise pip ke zariye install kiya jata hai.", table_cell)],
        [Paragraph("<b>gestures.txt</b>", table_cell_bold), Paragraph("<b>Gesture Quick Guide:</b> Tamam single-hand aur two-hand gestures ka handy user manual.", table_cell)],
        [Paragraph("<b>README.md</b>", table_cell_bold), Paragraph("<b>Technical Documentation:</b> Project architecture, code decoupling rationale, aur setup guide.", table_cell)],
    ]
    root_table = Table(root_data, colWidths=[130, A4[0] - 72 - 130], repeatRows=1)
    root_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), primary_color),
        ('GRID', (0, 0), (-1, -1), 0.5, border_color),
        ('PADDING', (0, 0), (-1, -1), 4),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, bg_alt]),
    ]))
    story.append(root_table)
    story.append(Spacer(1, 8))

    # Core Engine Table
    story.append(Paragraph("B. Folder: <code>gesture_mouse/</code> (Core System Engine)", h2_style))
    core_data = [
        [Paragraph("Module File", table_header), Paragraph("Exact Role & Functionality", table_header)],
        [Paragraph("<b>config.py</b>", table_cell_bold), Paragraph("<b>Central Settings:</b> Camera index, frame size (640x480), pinch distance thresholds, landmark IDs, aur smoothing values.", table_cell)],
        [Paragraph("<b>camera.py</b>", table_cell_bold), Paragraph("<b>Camera Manager:</b> OpenCV VideoCapture ko cleanly open karta hai, frames read karta hai aur safe close karta hai.", table_cell)],
        [Paragraph("<b>image_processor.py</b>", table_cell_bold), Paragraph("<b>Image Preprocessing & HUD:</b> Video ko mirror (flip) karta hai, BGR se RGB convert karta hai aur screen par text/FPS draw karta hai.", table_cell)],
        [Paragraph("<b>hand_detector.py</b>", table_cell_bold), Paragraph("<b>AI Hand Tracker:</b> MediaPipe model wrap karta hai, 21 landmark points nikalta hai aur Left vs Right hand pehchanta hai.", table_cell)],
        [Paragraph("<b>gesture_recognizer.py</b>", table_cell_bold), Paragraph("<b>Brain of the System:</b> Geometric math se unglio ki position check karta hai aur confirmation frames (deadzone) ke sath gesture pehchanta hai.", table_cell)],
        [Paragraph("<b>smoothing.py</b>", table_cell_bold), Paragraph("<b>Anti-Jitter Filter:</b> Exponential Moving Average (EMA) algorithm se haath ke thartharahat ko khatam karke smooth cursor movement deta hai.", table_cell)],
        [Paragraph("<b>mouse_control.py</b>", table_cell_bold), Paragraph("<b>OS Actions Execution:</b> PyAutoGUI ke zariye cursor move, clicks, drag & drop, scroll, screenshot, zoom aur screen lock karta hai.", table_cell)],
        [Paragraph("<b>left_hand_controller.py</b>", table_cell_bold), Paragraph("<b>Secondary Controller:</b> Ulte hath se left-clicks, drag-and-drop, right-click aur volume/brightness adjustments handle karta hai.", table_cell)],
        [Paragraph("<b>window_manager.py</b>", table_cell_bold), Paragraph("<b>Window Handling:</b> Windows ko minimize all karna, unhe internal Stack me yaad rakhna aur ek ek karke wapas restore karna.", table_cell)],
        [Paragraph("<b>volume_control.py</b>", table_cell_bold), Paragraph("<b>Audio Control:</b> Windows master volume ko thumb-index distance se barhana/kam karna aur screen par audio slider bar dikhana.", table_cell)],
        [Paragraph("<b>brightness_control.py</b>", table_cell_bold), Paragraph("<b>Brightness Control:</b> Screen display brightness ko gesture se adjust karna aur visual percentage bar draw karna.", table_cell)],
    ]
    core_table = Table(core_data, colWidths=[130, A4[0] - 72 - 130], repeatRows=1)
    core_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), secondary_color),
        ('GRID', (0, 0), (-1, -1), 0.5, border_color),
        ('PADDING', (0, 0), (-1, -1), 3.5),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, bg_alt]),
    ]))
    story.append(core_table)
    story.append(Spacer(1, 8))

    # Tests Folder Table
    story.append(Paragraph("C. Folder: <code>tests/</code> (Automated Testing Suite)", h2_style))
    test_data = [
        [Paragraph("Test File", table_header), Paragraph("Testing Purpose (Decoupled Unit Tests)", table_header)],
        [Paragraph("<b>test_gesture_recognizer.py</b>", table_cell_bold), Paragraph("Bina webcam ke synthetic coordinates ke sath har gesture ki mathematical accuracy verify karta hai.", table_cell)],
        [Paragraph("<b>test_mouse_control.py</b>", table_cell_bold), Paragraph("PyAutoGUI ko mock karke test karta hai taake test run karte waqt actual mouse na hile lekin code verify ho.", table_cell)],
        [Paragraph("<b>test_smoothing.py</b>", table_cell_bold), Paragraph("Cursor jitter filter ke mathematical formulas aur EMA weighting verify karta hai.", table_cell)],
        [Paragraph("<b>test_left_hand_controller.py</b>", table_cell_bold), Paragraph("Left hand ke tap vs hold timings (Click vs Drag threshold) ko test karta hai.", table_cell)],
        [Paragraph("<b>test_window_manager.py</b>", table_cell_bold), Paragraph("Windows minimize batching aur restore stack LIFO order ko verify karta hai.", table_cell)],
        [Paragraph("<b>test_confusion.py</b> & <b>test_zoom.py</b>", table_cell_bold), Paragraph("Similar gestures ke edge cases aur zoom pinch scaling logic ko test karta hai.", table_cell)],
    ]
    test_table = Table(test_data, colWidths=[140, A4[0] - 72 - 140], repeatRows=1)
    test_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#334155")),
        ('GRID', (0, 0), (-1, -1), 0.5, border_color),
        ('PADDING', (0, 0), (-1, -1), 3.5),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, bg_alt]),
    ]))
    story.append(test_table)
    story.append(Spacer(1, 8))

    story.append(PageBreak())

    # Standalone Game & Build/Release
    story.append(Paragraph("D. Folder: <code>ninja_fruit_hand_game/</code> (Bonus Interactive Game)", h2_style))
    game_data = [
        [Paragraph("Game Component", table_header), Paragraph("Role in Hand Fruit Ninja Game", table_header)],
        [Paragraph("<b>main.py</b>", table_cell_bold), Paragraph("Game ka main loop jo Pygame graphics aur camera tracking ko initialize karta hai.", table_cell)],
        [Paragraph("<b>game/hand_tracker.py</b>", table_cell_bold), Paragraph("MediaPipe se sirf index finger tip ki coordinates track karta hai (blade ki tarah).", table_cell)],
        [Paragraph("<b>game/fruit.py</b>", table_cell_bold), Paragraph("Fruit spawn hona, screen par uthna aur slice hone par 2 tukray hone ki physics.", table_cell)],
        [Paragraph("<b>game/trail.py</b>", table_cell_bold), Paragraph("Ungli ke peeche banne wala glowing blade slash trail aur collision detection (blade vs fruit).", table_cell)],
        [Paragraph("<b>game/particles.py</b>", table_cell_bold), Paragraph("Fruit cut hone par juice ke splashes, cut effect flash aur combo score popups.", table_cell)],
        [Paragraph("<b>game/sounds.py</b>", table_cell_bold), Paragraph("Bina kisi audio file ke Python code se synthetically generate hone wali slice audio effects.", table_cell)],
        [Paragraph("<b>game/game.py</b>", table_cell_bold), Paragraph("Game state machine: start, score counter, combos, game over aur restart logic.", table_cell)],
    ]
    game_table = Table(game_data, colWidths=[130, A4[0] - 72 - 130], repeatRows=1)
    game_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), accent_color),
        ('GRID', (0, 0), (-1, -1), 0.5, border_color),
        ('PADDING', (0, 0), (-1, -1), 3.5),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, bg_alt]),
    ]))
    story.append(game_table)
    story.append(Spacer(1, 8))

    story.append(Paragraph("E. Folders: <code>build_exe/</code> & <code>release/</code> (Distribution & Deployment)", h2_style))
    build_data = [
        [Paragraph("Folder / File", table_header), Paragraph("Deployment Role", table_header)],
        [Paragraph("<b>release/GestureMouseControl/</b>", table_cell_bold), Paragraph("<b>Ready-to-Use Portable Application:</b> Final compiled <code>.exe</code> folder jise direct kisi bhi Windows PC par bina Python ke double-click se chalaya ja sakta hai.", table_cell)],
        [Paragraph("<b>release/NinjaFruitHandGame/</b>", table_cell_bold), Paragraph("Fruit Ninja game ka compiled standalone <code>.exe</code> bundle.", table_cell)],
        [Paragraph("<b>build_exe/*.spec</b>", table_cell_bold), Paragraph("PyInstaller configuration files jo Python scripts ko Windows binary me compile karti hain.", table_cell)],
    ]
    build_table = Table(build_data, colWidths=[150, A4[0] - 72 - 150], repeatRows=1)
    build_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), primary_color),
        ('GRID', (0, 0), (-1, -1), 0.5, border_color),
        ('PADDING', (0, 0), (-1, -1), 3.5),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, bg_alt]),
    ]))
    story.append(build_table)
    story.append(Spacer(1, 10))

    # Gestures Reference Table
    story.append(Paragraph("5. Supported Gestures Cheat Sheet", h1_style))
    gesture_data = [
        [Paragraph("Gesture Pose (Hath Ka Ishara)", table_header), Paragraph("Triggered OS Action (Computer Par Kya Hoga)", table_header), Paragraph("Mode", table_header)],
        [Paragraph("Index Finger Extended (Pointing)", table_cell_bold), Paragraph("Mouse Cursor Movement (Screen par pointer chalana)", table_cell), Paragraph("Standard", table_cell)],
        [Paragraph("Thumb + Middle Finger Pinch (Quick Tap)", table_cell_bold), Paragraph("Left Click (Single click)", table_cell), Paragraph("Standard", table_cell)],
        [Paragraph("Thumb + Middle Pinch (Hold > 250ms)", table_cell_bold), Paragraph("Mouse Drag & Drop (Files/Windows pakar kar le jana)", table_cell), Paragraph("Standard", table_cell)],
        [Paragraph("Thumb + Ring Finger Pinch", table_cell_bold), Paragraph("Right Click (Context menu)", table_cell), Paragraph("Standard", table_cell)],
        [Paragraph("Index + Middle Extended ('Peace Sign')", table_cell_bold), Paragraph("Scroll Page (Ooper / Neeche scroll)", table_cell), Paragraph("Standard", table_cell)],
        [Paragraph("All 5 Fingers Folded (Fist / Mutthi)", table_cell_bold), Paragraph("Minimize Active Window", table_cell), Paragraph("Window Mgmt", table_cell)],
        [Paragraph("All 5 Fingers Extended (Flat Palm)", table_cell_bold), Paragraph("Restore Active Window", table_cell), Paragraph("Window Mgmt", table_cell)],
        [Paragraph("Two Hands Both Forming Fists", table_cell_bold), Paragraph("Minimize All Windows (Desktop show karna)", table_cell), Paragraph("Multi-Hand", table_cell)],
        [Paragraph("Two Index Fingers Crossing ('X' Shape)", table_cell_bold), Paragraph("Lock Computer Screen (Win + L)", table_cell), Paragraph("Multi-Hand", table_cell)],
        [Paragraph("Thumb + Index Pinch (Vertical Hand)", table_cell_bold), Paragraph("Volume Control (Awaz kam/zyada karna)", table_cell), Paragraph("Media Mode", table_cell)],
        [Paragraph("Thumb + Index Pinch (Horizontal Hand)", table_cell_bold), Paragraph("Screen Brightness Control (Roshni adjust karna)", table_cell), Paragraph("Media Mode", table_cell)],
        [Paragraph("Thumb + Pinky Extended ('Shaka' Sign)", table_cell_bold), Paragraph("Close Active Window (Alt + F4)", table_cell), Paragraph("Standard", table_cell)],
        [Paragraph("Thumb + Index + Pinky ('Spiderman')", table_cell_bold), Paragraph("Take Screenshot (Folder me image save ho gi)", table_cell), Paragraph("Standard", table_cell)],
        [Paragraph("3 Fingers (Index, Middle, Ring) Extended", table_cell_bold), Paragraph("Toggle Presentation Mode (Slide swipe / Zoom in-out)", table_cell), Paragraph("Presentation", table_cell)],
    ]
    gest_table = Table(gesture_data, colWidths=[160, 240, A4[0] - 72 - 400], repeatRows=1)
    gest_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), secondary_color),
        ('GRID', (0, 0), (-1, -1), 0.5, border_color),
        ('PADDING', (0, 0), (-1, -1), 3),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, bg_alt]),
    ]))
    story.append(gest_table)
    story.append(Spacer(1, 10))

    story.append(PageBreak())

    # How to Run in Order (Step by Step)
    story.append(Paragraph("6. Project Run Kaise Karna Hai (Step-by-Step Order)", h1_style))
    story.append(Paragraph("Client ya examiner ke samne project ko run karne ka bilkul simple aur exact tareeqa yeh hai:", body_style))
    story.append(Spacer(1, 4))

    steps_data = [
        [
            Paragraph("<b>STEP 1</b>", ParagraphStyle('Stp', parent=table_cell_bold, textColor=colors.HexColor("#2563EB"))),
            Paragraph("<b>Terminal / Command Prompt Kholein:</b><br/>Project ke root folder (<code>d:\\F Y P</code>) me terminal open karein.", table_cell)
        ],
        [
            Paragraph("<b>STEP 2</b>", ParagraphStyle('Stp', parent=table_cell_bold, textColor=colors.HexColor("#2563EB"))),
            Paragraph("<b>Virtual Environment Activate Karein:</b><br/><code>.\\.venv\\Scripts\\activate</code> (Windows PowerShell ya CMD me).", table_cell)
        ],
        [
            Paragraph("<b>STEP 3</b>", ParagraphStyle('Stp', parent=table_cell_bold, textColor=colors.HexColor("#2563EB"))),
            Paragraph("<b>Dependencies Install / Verify Karein:</b><br/><code>pip install -r requirements.txt</code> (Tamam libraries ensure karne ke liye).", table_cell)
        ],
        [
            Paragraph("<b>STEP 4</b>", ParagraphStyle('Stp', parent=table_cell_bold, textColor=colors.HexColor("#2563EB"))),
            Paragraph("<b>Camera Selection Check Karein:</b><br/><code>gesture_mouse/config.py</code> me <code>CAMERA_INDEX</code> check karein: Agar laptop ka built-in webcam hai to <code>0</code>, agar mobile/external camera (DroidCam etc.) hai to <code>1</code> rakhein.", table_cell)
        ],
        [
            Paragraph("<b>STEP 5</b>", ParagraphStyle('Stp', parent=table_cell_bold, textColor=colors.HexColor("#059669"))),
            Paragraph("<b>Main Mouse System Start Karein:</b><br/>Command run karein: <b><code>python main.py</code></b><br/>Webcam window open ho jayegi aur live hand detection shuru ho jayegi.", table_cell)
        ],
        [
            Paragraph("<b>STEP 6</b>", ParagraphStyle('Stp', parent=table_cell_bold, textColor=colors.HexColor("#2563EB"))),
            Paragraph("<b>Fruit Ninja Game Chalana (Optional Demo):</b><br/>Game chalane ke liye: <code>cd ninja_fruit_hand_game</code> aur phir <code>python main.py</code> run karein.", table_cell)
        ],
        [
            Paragraph("<b>STEP 7</b>", ParagraphStyle('Stp', parent=table_cell_bold, textColor=colors.HexColor("#DC2626"))),
            Paragraph("<b>Program Band Karna (Safe Exit):</b><br/>• Video window par <b>'q'</b> key dabayein.<br/>• <b>Emergency Failsafe:</b> Agar cursor achanak bhagne lage, to mouse ko screen ke kisi bhi corner (kone) me jhatke se le jayein, PyAutoGUI system ko foran band kar dega.", table_cell)
        ],
    ]
    steps_table = Table(steps_data, colWidths=[65, A4[0] - 72 - 65])
    steps_table.setStyle(TableStyle([
        ('BOX', (0, 0), (-1, -1), 1, border_color),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, border_color),
        ('PADDING', (0, 0), (-1, -1), 6),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('ROWBACKGROUNDS', (0, 0), (-1, -1), [colors.white, bg_alt]),
    ]))
    story.append(steps_table)
    story.append(Spacer(1, 10))

    # Architecture Highlights for Defense / Client Pitch
    story.append(Paragraph("7. Key Highlights & Client Value (Client / Viva Key Points)", h1_style))
    
    highlights = [
        "<b>1. Decoupled Architecture:</b> Gesture recognition logic webcam se mukammal azaad hai; sirf mathematical coordinates par chalta hai, isliye unit tests bina kisi physical camera ke run ho jate hain.",
        "<b>2. Anti-Jitter Exponential Smoothing:</b> Hand tremor ko roknay ke liye Exponential Moving Average (EMA) lagaya gaya hai jiski wajah se cursor bilkul smooth move hota hai.",
        "<b>3. Accidental Trigger Deadzone:</b> Gesture misfires se bachne ke liye <code>GESTURE_CONFIRM_FRAMES</code> confirmation buffer shamil hai jo lagataar confirmation ke baad hi action leta hai.",
        "<b>4. Zero-Install Portable Release:</b> Project ko <code>PyInstaller</code> ke zariye standalone <code>.exe</code> me compile kiya gaya hai jise client bina Python setup ke chala sakta hai.",
    ]
    for h in highlights:
        story.append(Paragraph(f"• {h}", body_style))
        story.append(Spacer(1, 2))

    story.append(Spacer(1, 8))

    # Closing Callout Box
    footer_data = [
        [
            Paragraph(
                "<b>Project Delivery Status:</b> Fully functional, thoroughly tested, standalone portable releases built. "
                "Suitable for commercial touchless kiosk displays, presentations, accessible computing, and academic defense.",
                callout_text
            )
        ]
    ]
    footer_table = Table(footer_data, colWidths=[A4[0] - 72])
    footer_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor("#F0FDF4")),
        ('BOX', (0, 0), (-1, -1), 1, colors.HexColor("#86EFAC")),
        ('PADDING', (0, 0), (-1, -1), 8),
    ]))
    story.append(footer_table)

    doc.build(story, canvasmaker=NumberedCanvas)
    print(f"PDF Successfully created at: {output_pdf_path}")


if __name__ == "__main__":
    output_path = r"d:\F Y P\Hand_Gesture_System_Client_Guide.pdf"
    create_client_guide(output_path)
