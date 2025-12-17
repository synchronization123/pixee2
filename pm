import tkinter as tk
from tkinter import ttk, messagebox
import json
import os

DATA_FILE = "projects.json"


def load_projects():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return []


def save_projects(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)


class ProjectManagerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Project Management Tool")
        self.root.geometry("1100x650")

        self.projects = load_projects()
        self.edit_index = None

        self.tabs = ttk.Notebook(root)
        self.tabs.pack(fill="both", expand=True)

        self.create_add_project_tab()
        self.create_view_projects_tab()

    # ---------------- ADD PROJECT TAB ----------------
    def create_add_project_tab(self):
        self.add_tab = ttk.Frame(self.tabs)
        self.tabs.add(self.add_tab, text="Add / Edit Project")

        frame = ttk.Frame(self.add_tab, padding=10)
        frame.pack(fill="both", expand=True)

        labels = [
            "Project Name", "Owners", "Value Addition", "Project Category",
            "Start Date (YYYY-MM-DD)", "Expected Completion Date",
            "Status", "Completed Date",
            "Milestones (• bullet points)",
            "Challenges",
            "Tracker / Report / Remarks",
            "Action Items (1,2,3...)"
        ]

        self.entries = {}

        row = 0
        for label in labels:
            ttk.Label(frame, text=label).grid(row=row, column=0, sticky="w", pady=5)

            if label in ["Project Category", "Status"]:
                combo = ttk.Combobox(frame, state="readonly")
                combo["values"] = (
                    ["Internal", "Client", "Compliance", "Security", "Other"]
                    if label == "Project Category"
                    else ["Planned", "In Progress", "Blocked", "Completed"]
                )
                combo.grid(row=row, column=1, sticky="ew")
                self.entries[label] = combo

            elif label in [
                "Milestones (• bullet points)",
                "Challenges",
                "Tracker / Report / Remarks",
                "Action Items (1,2,3...)"
            ]:
                text = tk.Text(frame, height=4)
                text.grid(row=row, column=1, sticky="ew")
                self.entries[label] = text

            else:
                entry = ttk.Entry(frame)
                entry.grid(row=row, column=1, sticky="ew")
                self.entries[label] = entry

            row += 1

        frame.columnconfigure(1, weight=1)

        ttk.Button(frame, text="Save Project", command=self.save_project)\
            .grid(row=row, column=1, pady=15, sticky="e")

    # ---------------- SAVE PROJECT ----------------
    def save_project(self):
        project = {}

        for key, widget in self.entries.items():
            if isinstance(widget, tk.Text):
                project[key] = widget.get("1.0", "end").strip()
            else:
                project[key] = widget.get().strip()

        if not project["Project Name"]:
            messagebox.showerror("Error", "Project Name is mandatory")
            return

        if self.edit_index is None:
            self.projects.append(project)
        else:
            self.projects[self.edit_index] = project
            self.edit_index = None

        save_projects(self.projects)
        self.clear_form()
        self.refresh_table()
        messagebox.showinfo("Success", "Project saved successfully")

    # ---------------- CLEAR FORM ----------------
    def clear_form(self):
        for widget in self.entries.values():
            if isinstance(widget, tk.Text):
                widget.delete("1.0", "end")
            else:
                widget.set("") if isinstance(widget, ttk.Combobox) else widget.delete(0, "end")

    # ---------------- VIEW PROJECTS TAB ----------------
    def create_view_projects_tab(self):
        self.view_tab = ttk.Frame(self.tabs)
        self.tabs.add(self.view_tab, text="View Projects")

        cols = ("Project Name", "Owners", "Category", "Status", "Start Date", "Expected Completion")
        self.tree = ttk.Treeview(self.view_tab, columns=cols, show="headings")

        for col in cols:
            self.tree.heading(col, text=col)
            self.tree.column(col, width=150)

        self.tree.pack(fill="both", expand=True, padx=10, pady=10)

        ttk.Button(self.view_tab, text="Edit Selected Project", command=self.edit_project)\
            .pack(pady=5)

        self.refresh_table()

    # ---------------- REFRESH TABLE ----------------
    def refresh_table(self):
        self.tree.delete(*self.tree.get_children())
        for idx, p in enumerate(self.projects):
            self.tree.insert("", "end", iid=idx, values=(
                p.get("Project Name", ""),
                p.get("Owners", ""),
                p.get("Project Category", ""),
                p.get("Status", ""),
                p.get("Start Date (YYYY-MM-DD)", ""),
                p.get("Expected Completion Date", "")
            ))

    # ---------------- EDIT PROJECT ----------------
    def edit_project(self):
        selected = self.tree.focus()
        if not selected:
            messagebox.showwarning("Select", "Please select a project")
            return

        self.edit_index = int(selected)
        project = self.projects[self.edit_index]

        for key, widget in self.entries.items():
            value = project.get(key, "")
            if isinstance(widget, tk.Text):
                widget.delete("1.0", "end")
                widget.insert("1.0", value)
            else:
                widget.set(value) if isinstance(widget, ttk.Combobox) else widget.insert(0, value)

        self.tabs.select(self.add_tab)


if __name__ == "__main__":
    root = tk.Tk()
    app = ProjectManagerApp(root)
    root.mainloop()