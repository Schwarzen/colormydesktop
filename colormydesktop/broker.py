# /home/Warzen/Color-My-Desktop/colormydesktop/broker.py
from colormydesktop.config import FEATURE_SWITCH_STATES, SWITCH_REVEAL_MAP
from colormydesktop.dialogs import DynamicPopupWindow
from colormydesktop.state_cache import (
    init_cache,
    load_all_switch_states,
    save_switch_state,
)


class ContextBroker:
    # Storage bins for our unique live object instances
    _contexts = {}
    _current_active_id = None
    manager = None
    _gnome_manager = None
    _nautilus_manager = None
    gnome_options_singleton = None
    kde_options_singleton = None
    nautilus_options_singleton = None
    # --- 1. System/Broker Initialization (Run once on startup) ---
    init_cache()

    # Load all previously persistent states from disk directly into your in-memory container
    FEATURE_SWITCH_STATES = load_all_switch_states()
    print(
        f"[BROKER INIT] Loaded {len(FEATURE_SWITCH_STATES)} switch states from hard database cache."
    )

    @classmethod
    def register_page(cls, page_id, instance):
        """
        Allows any unique UI page (PageHomeView, GnomeOptions, etc.)
        to identify itself and register its live memory block.
        """
        cls._contexts[page_id] = instance
        cls._current_active_id = page_id  #  Cache the latest registered page ID
        print(
            f"[CONTEXT BROKER] Registered UI Layer mapping: '{page_id}' -> {instance}"
        )

    @classmethod
    def get_page(cls, page_id):
        """
        Retrieves a registered page context safely.
        """
        return cls._contexts.get(page_id, None)

    @classmethod
    def active_page(cls):
        """
        Dynamic getter that returns the live memory block of the last registered page.
        """
        if cls._current_active_id:
            return cls.get_page(cls._current_active_id)
        return None

    @property
    def gnome(self):
        """Lazily creates and returns the GnomeOptionsManager instance."""
        # Read/Write from the class scope directly using self.__class__
        cls = self.__class__
        if cls._gnome_manager is None:
            from colormydesktop.gnomeoptions import GnomeThemeConfig

            cls._gnome_manager = GnomeThemeConfig(self)
        return cls._gnome_manager

    @property
    def nautilus(self):
        """Lazily creates and returns the GnomeOptionsManager instance."""
        # Read/Write from the class scope directly using self.__class__
        cls = self.__class__
        if cls._nautilus_manager is None:
            from colormydesktop.nautilusoptions import NautilusThemeConfig

            cls._nautilus_manager = NautilusThemeConfig(self)
        return cls._nautilus_manager

    # Add global properties to the broker class
    #  DYNAMIC MAGIC: Catch any .xxxx_entry or .xxxx_switch lookups automatically
    def __getattr__(self, name):
        gnome = self.get_page("gnome_options")
        if not gnome:
            raise AttributeError(
                f"'ContextBroker' has no attribute '{name}' (and gnome_options page is not registered)"
            )
        nautilus = self.get_page("nautilus_options")
        if not gnome:
            raise AttributeError(
                f"'ContextBroker' has no attribute '{name}' (and nautilus_options page is not registered)"
            )

        # Handle entry rows (e.g., broker.clock_entry or broker.topbar_entry)
        if name.endswith("_entry"):
            prefix = name.replace("_entry", "")  # e.g., "clock" or "topbar"
            # Normalize prefix to match your key names (adds "color" if needed)
            key = f"{prefix}color" if not prefix.endswith("color") else prefix
            if key in gnome.color_entries:
                return gnome.color_entries[key]
            elif key in nautilus.color_entries:
                return nautilus.color_entries[key]

        # Handle switches (e.g., broker.clock_switch or broker.topbar_switch)
        elif name.endswith("_switch"):
            prefix = name.replace("_switch", "")  # e.g., "clock" or "topbar"
            key = f"{prefix}color" if not prefix.endswith("color") else prefix
            if key in gnome.switches:
                return gnome.switches[key]
            elif key in nautilus.switches:
                return nautilus.switches[key]

        # Fallback to standard Python error if it's completely unrelated
        raise AttributeError(f"'ContextBroker' object has no attribute '{name}'")

    @classmethod
    def navigate(cls, current_widget, target_page_class, page_id):
        """
        Universal Routing Engine. Manages singletons, tracks memory allocations,
        and dynamically determines whether to SPAWN a fresh popup window or
        SWAP layout frames inside an existing one.
        """
        sender_name = current_widget.__class__.__name__
        sender_mem = hex(id(current_widget))
        target_name = target_page_class.__name__

        print(
            f"\n[ROUTER] {sender_name} ({sender_mem}) requested transition to {target_name}..."
        )

        # 1. Look for an existing permanent instance in our lazy-loading state pool
        live_instance = cls.get_page(page_id)

        if live_instance:
            print(
                f"   -> Existing instance found at {hex(id(live_instance))}. Preparing canvas routing tracks..."
            )
        else:
            print(
                f"   -> Instance not found for key '{page_id}'. Creating fresh layout memory block now..."
            )
            live_instance = target_page_class()
            cls.register_page(page_id, live_instance)
            print(
                f"   -> Successfully allocated {target_name} memory registry node at {hex(id(live_instance))}."
            )

        # 2. DETECT PARENT CONTEXT: Determine whether to SPAWN or SWAP
        root_window = current_widget.get_root()
        root_class_name = root_window.__class__.__name__ if root_window else ""

        #  DYNAMIC TITLE LOGIC
        if page_id.startswith("permission_dialog_"):
            app_name = (
                page_id.replace("permission_dialog_", "").replace("_", " ").title()
            )
            window_title = f"Permissions for {app_name} Required"
        else:
            window_title = "Advanced Options"

        #  REVERSED CHECK: Safely check if we are already inside the popup
        if root_class_name != "DynamicPopupWindow":
            print(
                f"   -> Parent is {root_class_name}. Spawning fresh Window shell wrapper..."
            )

            # Spawn the window
            popup_window = DynamicPopupWindow.spawn(
                parent_window=root_window,
                title=window_title,
                content_widget=live_instance,
            )

            # Target the window directly to lock in desired dimensions
            if popup_window:
                popup_window.set_size_request(350, 300)
        else:
            print(
                f"   -> Active popup container detected. Swapping view layout tracks smoothly..."
            )

            # Pass the new title so the window updates correctly
            DynamicPopupWindow.swap_content(
                current_widget=current_widget,
                new_content_widget=live_instance,
                new_title=window_title,
            )

    @classmethod
    def translate_action(cls, sender_id, action_type, payload):
        """
        The central translation matrix. It captures who called the function (sender_id),
        updates their local UI context if needed, and forces updates on completely separate pages.
        """
        if not cls.manager:
            print("[BROKER ERROR] No manager instance registered to handle events yet!")
            return

        print(
            f"\n[BROKER ACTION] '{sender_id}' requested a state mutation loop: '{action_type}'"
        )

        #  Fetch our unique targets out of the registration pool
        home_page = cls.get_page("home_view")
        gnome_page = cls.get_page("gnome_options")
        nautilus_page = cls.get_page("nautilus_options")
        global FEATURE_SWITCH_STATES

        # --- HANDLE MOCKUP VECTOR CLICKS ---
        if action_type == "CLICKED_MOCKUP_ELEMENT":
            element_id = payload["element_id"]
            print(f"[BROKER LOG] Mockup shape vector context clicked: '{element_id}'")

            if element_id == "topbar":
                from colormydesktop.lib_gui import GnomeOptions

                # Look up our active Home View card container block to use as the base context
                home_view = cls.get_page("home_view")

                # Automatically open the GnomeOptions window when clicking the topbar preview!
                if home_view:
                    cls.navigate(
                        current_widget=home_view,
                        target_page_class=GnomeOptions,
                        page_id="gnome_options",
                    )

            elif element_id == "nautilus-window":
                from colormydesktop.lib_gui import NautilusOptions

                # Look up our active Home View card container block to use as the base context
                home_view = cls.get_page("home_view")

                # Automatically open the GnomeOptions window when clicking the topbar preview!
                if home_view:
                    cls.navigate(
                        current_widget=home_view,
                        target_page_class=NautilusOptions,
                        page_id="nautilus_options",
                    )

            elif element_id == "accent_button":
                # Trigger a quick picker color swap, toggle rows, or launch another sub-page!
                pass

        if action_type == "TOGGLED_FEATURE_SWITCH":
            css_id = payload["css_id"]
            is_active = payload["is_active"]

            # Save permanently to our centralized memory state cache container
            FEATURE_SWITCH_STATES[css_id] = is_active
            print(f"[BROKER STATE] Feature toggle '{css_id}' cached as: {is_active}")

            # Set initial colors for custom fields in advanced options pages
            # Ensure the feature is active and home_page exists, alongside at least one configuration page
            if is_active and home_page and (gnome_page or nautilus_page):
                # 1. Grab the current live text inside the home view primary box
                live_primary_hex = home_page.current_colors.get("primary", "#246cc5")
                live_secondary_hex = home_page.current_colors.get(
                    "secondary", "#214fc3"
                )
                live_text_hex = home_page.current_colors.get("text", "#f9f9f9")

                # Dynamically choose the color map (Primary, Secondary, or Text)
                if css_id == "clockcolor":
                    color_to_apply = live_text_hex
                elif css_id == "nautilusprimarycolor":
                    color_to_apply = live_primary_hex
                elif css_id == "nautilussecondarycolor":
                    color_to_apply = live_secondary_hex
                else:
                    color_to_apply = live_primary_hex

                # Dynamically find target entry row across both Gnome and Nautilus pages
                target_row = None
                if gnome_page:
                    target_row = gnome_page.color_entries.get(css_id, None)

                # Fallback to checking nautilus_page if not found in gnome_page
                if not target_row and nautilus_page:
                    target_row = nautilus_page.color_entries.get(css_id, None)

                if target_row:
                    # 3. Overwrite the row's inner entry text buffer directly via code!
                    if hasattr(target_row, "set_text"):
                        target_row.set_text(color_to_apply)
                    elif hasattr(target_row, "get_editable"):
                        target_row.get_editable().set_text(color_to_apply)

                    print(
                        f"[BROKER AUTOFILL] Populated custom entry '{css_id}' with color: {color_to_apply}"
                    )

            # Check if the toggled switch was the refresh_switch and if it is active
            if payload.get("css_id") == "refresh_switch":
                is_active = payload.get("is_active", False)
                switch_widget = payload.get("widget")
                gnome_options_page = payload.get("page")
                save_switch_state(css_id, is_active)
                print(
                    f"[BROKER PERSISTENCE] Committed '{css_id}' to SQLite database storage."
                )

                cls.manager.initial_status(cls.get_page("home_view"), is_active)
                cls.manager.on_gnome_refresh_toggled(
                    is_active=is_active,
                    switch_widget=switch_widget,
                    gnome_options_page=gnome_options_page,
                )
            if payload.get("css_id") == "kde_refresh_switch":
                is_active = payload.get("is_active", False)
                switch_widget = payload.get("widget")
                kde_options_page = payload.get("page")
                save_switch_state(css_id, is_active)
                print(
                    f"[BROKER PERSISTENCE] Committed '{css_id}' to SQLite database storage."
                )

                cls.manager.initial_status(cls.get_page("home_view"), is_active)
                cls.manager.on_plasma_refresh_toggled(
                    is_active=is_active,
                    switch_widget=switch_widget,
                    kde_options_page=kde_options_page,
                )
        # ---  HANDLE TYPING ACTIONS ---
        if action_type == "CHANGED_TEXT_INPUT":
            # Save standard input changes to memory
            if payload["entry_row"] is not None:
                row = payload["entry_row"]
                css_id = payload["css_id"]
                sender_page = (
                    cls.get_page("home_view")
                    if sender_id == "PageHomeView"
                    else cls.get_page("gnome_options")
                )
                if sender_page and hasattr(sender_page, "current_colors"):
                    sender_page.current_colors[css_id] = row.get_text().strip()
                cls.manager.update_preview(row, css_id)

            if home_page and hasattr(home_page, "interactive_preview"):
                master_color_payload = {}

                # Load baseline values from Home Page
                if hasattr(home_page, "current_colors"):
                    master_color_payload.update(home_page.current_colors)

                # SCALABLE PRE-FILTER LOOP
                # Automatically iterates across any custom row mapped to a switch controller
                for advanced_key in SWITCH_REVEAL_MAP.keys():
                    switch_is_on = FEATURE_SWITCH_STATES.get(advanced_key, False)

                    if (
                        switch_is_on
                        and gnome_page
                        and hasattr(gnome_page, "current_colors")
                    ):
                        # Rule A: Switch active -> Extract custom text value from GnomeOptions memory map
                        custom_hex = gnome_page.current_colors.get(
                            advanced_key, ""
                        ).strip()
                        if custom_hex and custom_hex != "INHERIT":
                            master_color_payload[advanced_key] = custom_hex
                            continue

                    # Rule B: Switch inactive -> Dynamically force synchronization with current primary color
                    if advanced_key == "clockcolor":
                        # If clock switch is off, sync with the text color layer
                        master_color_payload[advanced_key] = master_color_payload.get(
                            "text", "#f9f9f9"
                        )
                    elif advanced_key == "nautilussecondarycolor":
                        # If clock switch is off, sync with the text color layer
                        master_color_payload[advanced_key] = master_color_payload.get(
                            "secondary", "#f9f9f9"
                        )
                    else:
                        # Otherwise, force synchronization with current primary color
                        master_color_payload[advanced_key] = master_color_payload.get(
                            "primary", "#246cc5"
                        )

                # Push the cleanly processed configuration payload to your canvas renderer
                home_page.interactive_preview.update_colors(master_color_payload)

        # ---  HANDLE ADVANCED COLOR PICKER DIALOG CLICKS ---
        elif action_type == "CLICKED_ADVANCED_PICKER":
            p = payload
            # Call your manager function directly, unpacking the exact expected arguments
            cls.manager.on_advanced_picker_clicked(
                p["gesture"], p["n_press"], p["x"], p["y"], p["entry_row"]
            )

        # ---  HANDLE QUICK PALETTE PICKER DIALOG CLICKS ---
        elif action_type == "CLICKED_QUICK_PICKER":
            p = payload
            cls.manager.on_quick_picker_clicked(
                p["gesture"], p["n_press"], p["x"], p["y"], p["entry_row"]
            )
        elif action_type == "GNOME_SETUP_CLICKED":
            p = payload
            cls.manager.on_quick_picker_clicked(
                p["gesture"], p["n_press"], p["x"], p["y"], p["entry_row"]
            )

        # --- HANDLE PERMISSION PORTAL DIALOG ---
        elif action_type == "SWITCH_FOLDER_CLICKED":
            title = payload.get("title")
            folders = payload.get("folders", [])
            current_widget = payload.get("widget")

            if isinstance(folders, str):
                folders = [folders]

            print(f"[BROKER PORTAL] Validating portal paths for {title}...")

            # 1. Evaluate existing portal access natively in Python
            portal_data_map = {}
            for folder in folders:
                safe_key = cls.manager.get_safe_key(folder)
                existing_path = getattr(cls.manager, f"active_portal_{safe_key}", None)
                if existing_path:
                    portal_data_map[folder] = existing_path
                    print(f"   -> Match found for {folder}: {existing_path}")

            safe_title_key = title.lower().replace(" ", "_")
            page_id = f"permission_dialog_{safe_title_key}"

            #  FORCE CLEANUP: If an old context exists, drop it so a fresh widget is always created
            if page_id in cls._contexts:
                del cls._contexts[page_id]

            # 2. Trigger your Universal Routing Engine
            from colormydesktop.lib_gui import PermissionDialogPage

            cls.navigate(
                current_widget=current_widget,
                target_page_class=PermissionDialogPage,
                page_id=page_id,
            )

            # 3. Retrieve the freshly allocated memory block
            dialog_page = cls.get_page(page_id)

            # 4. Inject payload and portal map
            if dialog_page:
                dialog_page.setup_dialog(
                    title=title,
                    folders=folders,
                    portal_data_map=portal_data_map,
                    broker_instance=cls,
                )

        # ---  HANDLE SWITCH TOGGLED (PERMISSION CHECK) ---
        elif action_type == "SWITCH_TOGGLED":
            import os
            import glob

            widget = payload.get("widget")
            folders = payload.get("folders", [])
            feature_name = payload.get("feature_name")

            if widget.get_active():
                if isinstance(folders, str):
                    folders = [folders]

                invalid_folders = []

                # 1. Execute the permission checks for ALL folders without breaking early
                for folder_pattern in folders:
                    has_access = False

                    # --- MANUAL ZEN PATH CHECK ---
                    if feature_name in ["Zen", "YouTube"]:
                        manual_path = getattr(
                            cls.manager, "last_manually_entered_zen_path", None
                        )
                        if manual_path:
                            expanded_manual = os.path.expanduser(manual_path)
                            if os.access(expanded_manual, os.W_OK):
                                has_access = True

                    # --- EXISTING PORTAL CHECK ---
                    if not has_access:
                        safe_key = cls.manager.get_safe_key(folder_pattern)
                        portal_path = getattr(
                            cls.manager, f"active_portal_{safe_key}", None
                        )
                        if portal_path and os.access(portal_path, os.W_OK):
                            has_access = True

                    # --- HOST FALLBACK (WITH WILDCARDS) ---
                    if not has_access:
                        expanded_pattern = os.path.expanduser(folder_pattern)
                        matches = list(glob.iglob(expanded_pattern))

                        if matches and any(os.access(m, os.W_OK) for m in matches):
                            has_access = True
                        elif os.access(expanded_pattern, os.W_OK):
                            has_access = True

                    # If after all checks we still have no access, track it
                    if not has_access:
                        invalid_folders.append(folder_pattern)

                # 2. Trigger dynamic dialog routing if any permissions are missing
                if invalid_folders:
                    print(
                        f"[BROKER] Missing permissions for {feature_name}. Spawning dynamic dialog..."
                    )

                    # Clear cache for all invalid folders simultaneously
                    if hasattr(cls.manager, "clear_specific_portal_cache"):
                        cls.manager.clear_specific_portal_cache(invalid_folders)

                    # Stash context directly onto the widget for the cleanup loop
                    widget._assigned_folders = folders
                    widget._feature_name = feature_name
                    cls.manager.last_toggled_switch = widget

                    # Prevent the switch from turning on
                    widget.set_active(False)

                    # Build unique page ID and force fresh allocation
                    safe_title_key = feature_name.lower().replace(" ", "_")
                    page_id = f"permission_dialog_{safe_title_key}"

                    if page_id in cls._contexts:
                        del cls._contexts[page_id]

                    # Trigger the Universal Routing Engine
                    from colormydesktop.lib_gui import PermissionDialogPage

                    cls.navigate(
                        current_widget=widget,
                        target_page_class=PermissionDialogPage,
                        page_id=page_id,
                    )

                    # Retrieve and construct the dynamic dialog payload
                    dialog_page = cls.get_page(page_id)
                    if dialog_page:
                        portal_data_map = {}
                        for f in folders:
                            s_key = cls.manager.get_safe_key(f)
                            existing_path = getattr(
                                cls.manager, f"active_portal_{s_key}", None
                            )
                            if existing_path:
                                portal_data_map[f] = existing_path

                        dialog_page.setup_dialog(
                            title=feature_name,
                            folders=folders,
                            portal_data_map=portal_data_map,
                            broker_instance=cls,
                        )
                else:
                    print(
                        f"[BROKER] Permissions verified for {feature_name}. Feature activated."
                    )

                    widget.set_active(True)

        # ---  HANDLE REQUIREMENTS LINK CLICKED ---
        elif action_type == "OPEN_REQUIREMENTS_CLICKED":
            current_widget = payload.get("widget")

            from colormydesktop.lib_gui import RequirementsPage

            # Trigger the Universal Routing Engine to swap content or spawn window
            cls.navigate(
                current_widget=current_widget,
                target_page_class=RequirementsPage,
                page_id="requirements_checklist",
            )

        elif action_type == "PORTAL_PATH_UPDATED":
            target_folder = payload.get("target_folder")
            sandboxed_path = payload.get("sandboxed_path")

            # 1. Dynamically target the live window instance currently in focus
            active_page = cls.active_page()

            if active_page:
                # Synchronize underlying state dictionary
                if not hasattr(active_page, "portal_data_map"):
                    active_page.portal_data_map = {}
                active_page.portal_data_map[target_folder] = sandboxed_path

                # 2. Extract row component from tracker index
                target_row = getattr(active_page, "folder_rows", {}).get(target_folder)

                if target_row:
                    # 3. Direct access to target entry
                    entry_widget = target_row.path_entry

                    from gi.repository import GLib

                    GLib.idle_add(
                        lambda e=entry_widget, p=sandboxed_path: [
                            e.set_text(p),
                            e.add_css_class("success"),
                            GLib.SOURCE_REMOVE,
                        ][-1]
                    )
                    print(
                        f"[BROKER] Dynamically updated active page entry for '{target_folder}'."
                    )
                else:
                    print(
                        f"[BROKER] Warning: No row index mapping found for '{target_folder}'."
                    )

            # (Optional) Call your backend generator/activation logic here

        elif action_type == "COPY_PATH_CLICKED":
            p = payload
            cls.manager.on_copy_clicked(p)

        elif action_type == "BUILD_BUTTON_CLICKED":
            pass
        elif action_type == "ANOTHER_FEATURE_EVENT":
            # additional cross-page interaction loops here
            pass


broker = ContextBroker()
