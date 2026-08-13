import customtkinter
import queue
from srcs.agents.agent_mbpp import Mbpp
from srcs.models.tasks import MBPPTaskInput

class MyScrollableText(customtkinter.CTkScrollableFrame):
    def __init__(self, master, title, values):
        super().__init__(master, label_text=title)
        self.grid_columnconfigure(0, weight=1)
        self.values = values
        self.checkboxes = []
        self.labels = []

        for i, value in enumerate(self.values):
            label = customtkinter.CTkLabel(
                self,
                text=value,
                anchor="w",
                justify="left",
                wraplength=350
            )
            label.grid(row=i, column=0, padx=10, pady=(10, 0), sticky="ew")
            self.labels.append(label)

    def update_texts(self, new_values: list):
        for label in self.labels:
            label.destroy()
        self.labels.clear()

        for i, value in enumerate(new_values):
            label = customtkinter.CTkLabel(self, text=value, anchor="w", justify="left")
            label.grid(row=i, column=0, padx=10, pady=(10, 0), sticky="ew")
            self.labels.append(label)


class MbppGui(customtkinter.CTk):

    def __init__(self, ui_queue: queue.Queue = None):
        super().__init__()
        self.ui_queue = ui_queue

        self.title("MBPP Agent GUI")
        self.geometry("1280x720")
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self.scrollable_txt = MyScrollableText(self, title="Values", values=[])
        self.scrollable_txt.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")

        if self.ui_queue is not None:
            self.after(100, self.check_queue)

    def check_queue(self):
        try:
            data = self.ui_queue.get_nowait()
            if isinstance(data, Mbpp):
                # self.scrollable_txt.update_texts(values)
            else:
                self.destroy()
                return
        except queue.Empty:
            pass

        self.after(100, self.check_queue)


def gui_thread_worker(ui_queue: queue.Queue):
    app = MbppGui(ui_queue=ui_queue)
    app.mainloop()
