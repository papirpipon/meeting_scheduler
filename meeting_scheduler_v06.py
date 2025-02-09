import tkinter as tk
from tkinter import ttk, messagebox
import datetime
import pytz
from functools import partial

try:
    import tzlocal
    system_tz = tzlocal.get_localzone_name()
except ImportError:
    system_tz = "America/Los_Angeles"  # Default to LA

class AutocompleteCombobox(ttk.Combobox):
    def set_completion_list(self, completion_list):
        self._completion_list = sorted(completion_list, key=lambda s: s.lower())
        self['values'] = self._completion_list
        self.bind('<KeyRelease>', self._handle_keyrelease)

    def _handle_keyrelease(self, event):
        if event.keysym in ("BackSpace", "Left", "Right", "Up", "Down", "Return", "Escape", "Tab"):
            return
        value = self.get().lower()
        filtered = [item for item in self._completion_list if value in item.lower()]
        self['values'] = filtered

class MeetingScheduler(tk.Tk):
    def __init__(self):
        print("Initializing...")
        super().__init__()
        self.title("Meeting Scheduler")
        self.configure(bg='black')
        self.cell_states = {}
        self.dragging = False
        self.start_cell = None
        self.last_cell = None
        self.selection_mode = False

        # Initialize these dictionaries
        self.local_time_labels = {}
        self.other_time_labels = {}
        self.slot_labels = {}

        # Define the time label width
        self.time_label_width = 9

        # Define the day header width
        self.day_header_width = 14

        # Set initial window size
        self.geometry("1300x500")

        # Optimization: Precalculate timezones at startup
        print("Getting timezones...")
        self.timezone_list = self.get_timezones()
        self.tz_display_map = {tz: disp for disp, tz in self.timezone_list}

        # Make the window resizable
        print("Setting up grid configuration...")
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        # Change main container to use pack instead of grid
        self.main_container = tk.Frame(self, bg='black')
        self.main_container.pack(fill=tk.BOTH, expand=True)

        # Set up ttk style
        print("Setting up style...")
        style = ttk.Style(self)
        style.theme_use('clam')
        style.configure('TLabel', background='black', foreground='white')
        style.configure('TButton', background='gray', foreground='white')
        style.configure('TCombobox', fieldbackground='gray', background='gray', foreground='white')

        # Add drag bindings
        self.bind_all("<B1-Motion>", self.on_drag)
        self.bind_all("<ButtonRelease-1>", self.on_release)

        print("Creating sections...")
        self.create_top_section()
        self.create_calendar_section()
        self.create_bottom_section()

        print("Adding event bindings...")
        self.bind_all("<B1-Motion>", self.on_drag)
        self.bind_all("<ButtonRelease-1>", self.on_release)

        # Initialize display
        print("Updating time labels...")
        self.update_time_labels()
        print("Setting initial scroll position...")
        self.after(100, lambda: self.canvas.yview_moveto(12/self.total_slots))

        print("Initialization complete, starting mainloop...")

    def get_timezones(self):
        """Get US and all Africa timezones"""
        
        # US major timezones
        us_timezones = [
            'America/Los_Angeles',  # Pacific Time
            'America/Denver',       # Mountain Time
            'America/Chicago',      # Central Time
            'America/New_York',     # Eastern Time
            'America/Anchorage',    # Alaska Time
            'Pacific/Honolulu',     # Hawaii Time
        ]
        
        # Get all Africa timezones from pytz
        africa_timezones = [tz for tz in pytz.all_timezones if tz.startswith('Africa/')]
        
        # Combine US and Africa timezones, plus UTC
        selected_timezones = us_timezones + africa_timezones + ['UTC']
        
        tz_list = []
        now_utc = datetime.datetime.now(pytz.utc)
        
        for tz_name in selected_timezones:
            try:
                tz = pytz.timezone(tz_name)
                dt = now_utc.astimezone(tz)
                offset = dt.utcoffset() or datetime.timedelta(0)
                total_minutes = offset.total_seconds() / 60
                sign = '+' if total_minutes >= 0 else '-'
                hours, minutes = divmod(abs(int(total_minutes)), 60)
                
                # Add clearer labels for US timezones
                if tz_name in us_timezones:
                    if 'Los_Angeles' in tz_name:
                        label = 'US Pacific Time'
                    elif 'Denver' in tz_name:
                        label = 'US Mountain Time'
                    elif 'Chicago' in tz_name:
                        label = 'US Central Time'
                    elif 'New_York' in tz_name:
                        label = 'US Eastern Time'
                    elif 'Anchorage' in tz_name:
                        label = 'US Alaska Time'
                    elif 'Honolulu' in tz_name:
                        label = 'US Hawaii Time'
                else:
                    # For Africa timezones, just clean up the city name
                    label = tz_name.split('/')[-1].replace('_', ' ')
                    
                display_name = f"(UTC{sign}{hours:02d}:{minutes:02d}) {label}"
                tz_list.append((offset, display_name, tz_name))
                
            except Exception:
                continue
                
        # Sort by UTC offset first, then alphabetically
        tz_list.sort(key=lambda x: (x[0], x[2]))
        return [(display, tz_name) for _, display, tz_name in tz_list]
    def create_top_section(self):
        top_frame = tk.Frame(self.main_container, bg='black')
        top_frame.grid(row=0, column=0, sticky='ew', padx=10, pady=5)

        # Time Zone dropdowns
        tk.Label(top_frame, text="My Time Zone:", bg='black', fg='white').grid(row=0, column=0, padx=5, pady=5, sticky='w')
        self.local_tz_cb = AutocompleteCombobox(top_frame, width=30)
        self.local_tz_cb.set_completion_list([disp for disp, tz in self.timezone_list])
        self.local_tz_cb.grid(row=0, column=1, padx=5, pady=5)

        # Set default to Los Angeles
        la_display = next((disp for disp, tz in self.timezone_list if "Pacific Time" in disp), "(UTC-07:00) US Pacific Time")
        self.local_tz_cb.set(la_display)

        tk.Label(top_frame, text="Other Time Zone:", bg='black', fg='white').grid(row=0, column=2, padx=5, pady=5, sticky='w')
        self.target_tz_cb = AutocompleteCombobox(top_frame, width=30)
        self.target_tz_cb.set_completion_list([disp for disp, tz in self.timezone_list])
        self.target_tz_cb.grid(row=0, column=3, padx=5, pady=5)
        self.target_tz_cb.set("(UTC+00:00) UTC")

        # Meeting Duration Selection
        tk.Label(top_frame, text="Meeting Duration:", bg='black', fg='white').grid(row=0, column=4, padx=5, pady=5, sticky='w')
        self.duration_cb = ttk.Combobox(top_frame, values=["30 minutes", "an hour"], state="readonly", width=12)
        self.duration_cb.grid(row=0, column=5, padx=5, pady=5)
        self.duration_cb.current(0)

        # Bind events
        self.local_tz_cb.bind("<<ComboboxSelected>>", self.timezone_changed)
        self.target_tz_cb.bind("<<ComboboxSelected>>", self.timezone_changed)
        self.duration_cb.bind("<<ComboboxSelected>>", lambda e: self.update_meeting_proposal())

        # Configure grid columns
        for i in range(6):
            top_frame.grid_columnconfigure(i, weight=1)

    def create_calendar_section(self):
        # Calendar container
        calendar_container = tk.Frame(self.main_container, bg='black')
        calendar_container.grid(row=1, column=0, sticky='nsew', padx=10, pady=5)
        
        self.main_container.grid_rowconfigure(1, weight=3)
        calendar_container.grid_columnconfigure(0, weight=1)
        calendar_container.grid_rowconfigure(1, weight=1)

        # Header frame with proper column weights
        self.header_frame = tk.Frame(calendar_container, bg='black')
        self.header_frame.grid(row=0, column=0, sticky='ew', columnspan=2)
        
        # Configure header columns with specific weights
        self.header_frame.grid_columnconfigure(0, weight=1)  # Local Time
        self.header_frame.grid_columnconfigure(1, weight=1)  # Other Time
        for i in range(2, 9):
            self.header_frame.grid_columnconfigure(i, weight=2)  # Day columns get more weight
        
        # Time label headers with consistent width
        tk.Label(self.header_frame, text="My Time", bg='black', fg='white',
                borderwidth=1, relief="solid", width=self.time_label_width).grid(row=0, column=0, sticky="ew", padx=1, pady=1)
        tk.Label(self.header_frame, text="Other Time", bg='black', fg='white',
                borderwidth=1, relief="solid", width=self.time_label_width).grid(row=0, column=1, sticky="ew", padx=1, pady=1)

        # Day headers with consistent width
        self.week_dates = self.get_week_dates()
        self.day_headers = []
        for i, day in enumerate(self.week_dates):
            day_str = day.strftime("%a, %b %d")
            lbl = tk.Label(self.header_frame, text=day_str, bg='black', fg='white',
                        borderwidth=1, relief="solid", width=self.day_header_width)
            lbl.grid(row=0, column=i+2, sticky="ew", padx=1, pady=1)
            self.day_headers.append(lbl)

        # Scrollable canvas
        self.canvas = tk.Canvas(calendar_container, bg='black')
        self.canvas.grid(row=1, column=0, sticky='nsew')

        # When the mouse enters the canvas, give it focus so it receives wheel events.
        self.canvas.bind("<Enter>", lambda event: self.canvas.focus_set())

        # Bind the mouse wheel events directly on the canvas.
        self.canvas.bind("<MouseWheel>", self._on_mousewheel)  # For Windows/Mac
        self.canvas.bind("<Button-4>", self._on_mousewheel)    # For Linux scroll up
        self.canvas.bind("<Button-5>", self._on_mousewheel)    # For Linux scroll down

        # Scrollbar
        v_scroll = ttk.Scrollbar(calendar_container, orient=tk.VERTICAL, command=self.canvas.yview)
        v_scroll.grid(row=1, column=1, sticky='ns')
        self.canvas.configure(yscrollcommand=v_scroll.set)

        # Grid frame
        self.grid_frame = tk.Frame(self.canvas, bg='black')
        self.canvas.create_window((0, 0), window=self.grid_frame, anchor="nw")

        # Configure grid frame columns to match header weights
        self.grid_frame.grid_columnconfigure(0, weight=1)  # Local Time
        self.grid_frame.grid_columnconfigure(1, weight=1)  # Other Time
        for i in range(2, 9):
            self.grid_frame.grid_columnconfigure(i, weight=2)  # Day columns get more weight

        # Bind events
        self.bind('<Configure>', self._on_configure)

        # After creating the grid_frame
        self.grid_frame = tk.Frame(self.canvas, bg='black')
        self.canvas.create_window((0, 0), window=self.grid_frame, anchor="nw")

        # Update scroll region when grid_frame changes
        self.grid_frame.bind("<Configure>", lambda event: self.canvas.configure(scrollregion=self.canvas.bbox("all")))

        # Create time slots (48 half-hour slots for 24 hours)
        self.total_slots = 48
        self.create_time_grid()

    def create_time_grid(self):
        label_config = {
            'borderwidth': 1,
            'relief': "solid",
            'bg': 'white',
            'fg': 'black',
            'width': 7
        }
        cell_config = {
            'borderwidth': 1,
            'relief': "solid",
            'bg': 'white',
            'width': 14
        }
        
        for slot in range(self.total_slots):
            # Time labels
            lbl_local = tk.Label(self.grid_frame, bg='white', fg='black', 
                                borderwidth=1, relief="solid", width=self.time_label_width)
            lbl_local.grid(row=slot, column=0, sticky="ew", padx=1, pady=1)
            self.local_time_labels[slot] = lbl_local
            
            lbl_other = tk.Label(self.grid_frame, bg='white', fg='black',
                                borderwidth=1, relief="solid", width=self.time_label_width)
            lbl_other.grid(row=slot, column=1, sticky="ew", padx=1, pady=1)
            self.other_time_labels[slot] = lbl_other

            # Day cells
            for day in range(7):
                cell = tk.Label(self.grid_frame, bg='white', fg='black',
                            borderwidth=1, relief="solid", width=self.day_header_width)
                cell.grid(row=slot, column=day+2, sticky="ew", padx=1, pady=1)
                cell.day = day
                cell.slot = slot
                cell.bind("<Button-1>", self.on_cell_click)
                cell.bind("<Button-3>", self.on_cell_right_click)
                
                self.slot_labels[(day, slot)] = cell
                self.cell_states[(day, slot)] = False

    def create_bottom_section(self):
        bottom_frame = tk.Frame(self.main_container, bg='black')
        bottom_frame.grid(row=2, column=0, sticky='ew', padx=10, pady=5)
        
        self.meeting_text = tk.Text(bottom_frame, height=10, bg='black', fg='white', relief='flat')
        self.meeting_text.grid(row=0, column=0, sticky='nsew', padx=5, pady=5)  # Replace pack with grid
        self.meeting_text.config(state=tk.DISABLED)
        
        self.copy_button = ttk.Button(bottom_frame, text="Copy to Clipboard", command=self.copy_to_clipboard)
        self.copy_button.grid(row=0, column=1, padx=5, pady=5)  # Replace pack with grid

        # Configure column and row weights
        bottom_frame.grid_columnconfigure(0, weight=1)

    def _on_configure(self, event):
        # Only handle main window resizing
        if event.widget == self:
            # Update canvas scroll region
            self.canvas.configure(scrollregion=self.canvas.bbox("all"))
            
            # Update grid frame width to match canvas
            canvas_width = self.canvas.winfo_width()
            self.grid_frame.configure(width=canvas_width)
            
            # Force header frame to match grid frame width
            self.header_frame.configure(width=canvas_width)

    def _on_mousewheel(self, event):
        if event.delta:
            self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
        else:
            if event.num == 4:  # Mouse wheel up
                self.canvas.yview_scroll(-1, "units")
            elif event.num == 5:  # Mouse wheel down
                self.canvas.yview_scroll(1, "units")

    def get_week_dates(self):
        today = datetime.date.today()
        start_week = today - datetime.timedelta(days=today.weekday())
        return [start_week + datetime.timedelta(days=i) for i in range(7)]

    def get_slot_datetime(self, slot):
        minutes = slot * 30  # 30-minute increments
        return datetime.datetime.combine(datetime.date.today(), 
                                       datetime.time(hour=minutes // 60, 
                                                   minute=minutes % 60))

    def timezone_changed(self, event):
        self.update_time_labels()
        self.update_meeting_proposal()

    def update_time_labels(self):
        print("Starting time label update...")
        local_disp = self.local_tz_cb.get()
        target_disp = self.target_tz_cb.get()
        print(f"Got timezone displays: {local_disp}, {target_disp}")
        
        local_tz_name = next((tz for disp, tz in self.timezone_list if disp == local_disp), "Etc/UTC")
        target_tz_name = next((tz for disp, tz in self.timezone_list if disp == target_disp), "Etc/UTC")
        print(f"Found timezone names: {local_tz_name}, {target_tz_name}")
        
        local_tz = pytz.timezone(local_tz_name)
        target_tz = pytz.timezone(target_tz_name)
        
        print(f"Starting slot updates...")
        for slot in range(self.total_slots):
            dt = self.get_slot_datetime(slot)
            try:
                dt_local = local_tz.localize(dt)
                dt_target = dt_local.astimezone(target_tz)
                
                self.local_time_labels[slot].config(text=dt_local.strftime("%H:%M"))
                self.other_time_labels[slot].config(text=dt_target.strftime("%H:%M"))
                
                # Update cell colors for this slot
                for day in range(7):
                    cell = self.slot_labels[(day, slot)]
                    is_selected = self.cell_states.get((day, slot), False)
                    is_business = self.is_business_hours(slot)
                    
                    if is_selected:
                        cell.config(bg="#FFDAB9")
                    else:
                        cell.config(bg="white" if is_business else "#C7C7C7")
                        
            except Exception as e:
                print(f"Error in slot {slot}: {e}")
                continue

    def is_business_hours(self, slot):
        # Get the base time for this slot
        time = self.get_slot_datetime(slot)
        
        # Get target timezone
        target_disp = self.target_tz_cb.get()
        target_tz_name = next((tz for disp, tz in self.timezone_list if disp == target_disp), "Etc/UTC")
        target_tz = pytz.timezone(target_tz_name)
        
        # Get local timezone for conversion
        local_disp = self.local_tz_cb.get()
        local_tz_name = next((tz for disp, tz in self.timezone_list if disp == local_disp), "Etc/UTC")
        local_tz = pytz.timezone(local_tz_name)
        
        # First localize base time to local timezone, then convert to target timezone
        local_dt = local_tz.localize(time)
        target_dt = local_dt.astimezone(target_tz)
        
        # Check if the target timezone time is within business hours
        return 8 <= target_dt.hour < 18

    def on_cell_click(self, event):
        cell = event.widget
        day, slot = cell.day, cell.slot
        
        self.selection_mode = not self.cell_states[(day, slot)]
        self.start_cell = (day, slot)
        self.last_cell = (day, slot)
        self.dragging = True
        
        self.set_cell_state(day, slot, self.selection_mode)
        self.update_meeting_proposal()

    def on_drag(self, event):
        if not self.dragging or not self.start_cell:
            return
            
        widget = self.winfo_containing(event.x_root, event.y_root)
        
        if hasattr(widget, 'day') and hasattr(widget, 'slot'):
            current_cell = (widget.day, widget.slot)
            
            if current_cell != self.last_cell:
                self.update_selection(self.start_cell, current_cell)
                self.last_cell = current_cell

    def on_release(self, event):
        if self.dragging:
            self.dragging = False
            self.start_cell = None
            self.last_cell = None
            self.update_meeting_proposal()

    def update_selection(self, start, end):
        start_day, start_slot = start
        end_day, end_slot = end
        
        start_ordinal = start_day * self.total_slots + start_slot
        end_ordinal = end_day * self.total_slots + end_slot
        
        min_ordinal = min(start_ordinal, end_ordinal)
        max_ordinal = max(start_ordinal, end_ordinal)
        
        updates = []
        for ordinal in range(min_ordinal, max_ordinal + 1):
            day = ordinal // self.total_slots
            slot = ordinal % self.total_slots
            updates.append((day, slot))
        
        for day, slot in updates:
            self.set_cell_state(day, slot, self.selection_mode)

    def set_cell_state(self, day, slot, state):
        self.cell_states[(day, slot)] = state
        self.update_cell_appearance(day, slot)

    def on_cell_right_click(self, event):
        cell = event.widget
        self.set_cell_state(cell.day, cell.slot, False)
        self.update_meeting_proposal()

    def update_meeting_proposal(self):
        duration = self.duration_cb.get()
        target_disp = self.target_tz_cb.get()
        
        # Get the target timezone
        target_tz_name = next((tz for disp, tz in self.timezone_list if disp == target_disp), "Etc/UTC")
        target_tz = pytz.timezone(target_tz_name)
        
        lines = [f"Would {duration} during any of the following times (all {target_disp}) work for you?"]
        
        for day in range(7):
            selected_slots = sorted([slot for slot in range(self.total_slots) 
                                if self.cell_states.get((day, slot), False)])
            
            if selected_slots:
                groups = []
                start_slot = selected_slots[0]
                prev_slot = selected_slots[0]
                
                for s in selected_slots[1:]:
                    if s == prev_slot + 1:
                        prev_slot = s
                    else:
                        groups.append((start_slot, prev_slot))
                        start_slot = s
                        prev_slot = s
                groups.append((start_slot, prev_slot))
                
                range_strs = []
                for start_s, end_s in groups:
                    # Convert slots to target timezone
                    start_time = self.get_slot_datetime(start_s)
                    end_time = self.get_slot_datetime(end_s + 1)
                    
                    local_tz_name = next((tz for disp, tz in self.timezone_list 
                                        if disp == self.local_tz_cb.get()), "Etc/UTC")
                    local_tz = pytz.timezone(local_tz_name)
                    
                    start_target = local_tz.localize(start_time).astimezone(target_tz)
                    end_target = local_tz.localize(end_time).astimezone(target_tz)
                    
                    range_strs.append(f"{start_target.strftime('%H:%M')} - {end_target.strftime('%H:%M')}")
                
                day_str = self.week_dates[day].strftime("%A, %b %d")
                lines.append(f"* {day_str}: " + ", ".join(range_strs))
        
        if len(lines) == 1:
            lines.append("No times selected yet.")
            
        lines.append("If none of these are convenient, I'm happy to adjust to your availability.")
        
        proposal = "\n".join(lines)
        self.meeting_text.config(state=tk.NORMAL)
        self.meeting_text.delete("1.0", tk.END)
        self.meeting_text.insert(tk.END, proposal)
        self.meeting_text.config(state=tk.DISABLED)

    def copy_to_clipboard(self):
        proposal = self.meeting_text.get("1.0", tk.END).strip()
        self.clipboard_clear()
        self.clipboard_append(proposal)
        messagebox.showinfo("Copied", "Meeting proposal copied to clipboard!")

if __name__ == "__main__":
    app = MeetingScheduler()
    app.mainloop()