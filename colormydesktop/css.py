# /home/Warzen/Color-My-Desktop/colormydesktop/css.py
BASE_STYLE_SHEET = """
.color-preview-dot {
    border-radius: 6px;
    border: 1px solid rgba(0,0,0,0.3);
    transition: all 0.2s ease-in-out;
    min-width: 26px;
    min-height: 26px;
}

.preview-dropper-icon {
    transition: opacity 0.2s ease;
    opacity: 0.5;
}

/* --- HOVER PHYSICS MAPS LINKED TO YOUR BLUEPRINT ROW STYLE CLASS --- */
.color-row-css:hover .color-preview-dot,
.color-row-css:focus-within .color-preview-dot {
    transform: scale(1.18);
    box-shadow: 0 0 12px rgba(255, 255, 255, 0.25);
    border-color: rgba(255, 255, 255, 0.6);
}

.color-row-css:hover .preview-dropper-icon,
.color-row-css:focus-within .preview-dropper-icon {
    opacity: 1.0;
}

.color-preview-container:active .color-preview-dot {
    transform: scale(0.92);
    transition: transform 0.05s;
}

/* Base mockup layout dimensions constraints */
#mockup-preview-image {
    margin-top: -80px;
    margin-bottom: -60px;
    padding: 0px;
    width: 100%;
}

#mockup-wrapper {
    border-radius: 12px;
    background: linear-gradient(165deg, #181818 0%, #080808 100%);
    padding: 0px; 
    min-height: 10px;
}

/* Strip away the default header bar styling */
headerbar.integrated-header {
    background: transparent;      /* Merges cleanly into your main app background */
    background-color: transparent;
    border-bottom: none;          /* Removes the stark separating line beneath it */
    box-shadow: none;             /* Removes the 3D depth shadows */
    max-height: 20px;             /* Slims down the vertical thickness */
    padding-top: 2px;
    padding-bottom: -2px;
}

headerbar.integrated-header > box {
    min-height: 20px;
    padding: 0;
    margin: 0;
}

/* Ensure the header bar doesn't draw its own window container background */
headerbar.integrated-header windowcontrols {
    background: transparent;
}

/* Optional: Make the title label extra sleek and low-profile */
headerbar.integrated-header label.heading {
    font-size: 9.5pt;
    font-weight: 600;
    opacity: 0.85;                /* Gives it a slightly muted, integrated look */
}

/* Tighten the header container space */
box.ultra-slim-header {
    background-color: transparent;
    min-height: 24px;
    padding-top: 4px;
    padding-bottom: 2px;
    margin: 0;
}

/* Make the title text clean and subtle */
box.ultra-slim-header label.slim-title {
    font-size: 10pt;
    font-weight: 500;
    opacity: 0.8;
}

"""
