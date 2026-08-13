import customtkinter
import queue
from srcs.agents.agent_mbpp import Mbpp
from srcs.models.tasks import MBPPTaskInput
from srcs.models.metrics import StepMetrics


class MbppGui(customtkinter.CTk):
    def __init__(self, ui_queue: queue.Queue = None):
        super().__init__()
        self.ui_queue = ui_queue
        self.task = None

        self.title(f"Agent Smith")
        self.geometry("1280x720")
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        self.header = customtkinter.CTkFrame(self, height=60, corner_radius=0)
        self.header.grid(row=0, column=0, sticky="ew")
        self.header.grid_columnconfigure(0, weight=1)

        self.title_label = customtkinter.CTkLabel(
            self.header,
            text="Agent Smith: MBPP",
            font=customtkinter.CTkFont(size=22, weight="bold"),
        )
        self.title_label.grid(row=0, column=0, sticky="w", padx=20, pady=10)

        self.history_frame = customtkinter.CTkScrollableFrame(self)
        self.history_frame.grid(row=1, column=0, sticky="nsew", padx=20, pady=(20, 20))
        self.history_frame.grid_columnconfigure(0, weight=1)
        
        self._task_row_count = 0

        self._current_task_frame = None
        self._current_step_row_count = 0

        if self.ui_queue is not None:
            self.after(100, self.check_queue)

    def check_queue(self):
        try:
            while True:
                data = self.ui_queue.get_nowait()
                if isinstance(data, MBPPTaskInput):
                    self.insert_task(data)
                elif isinstance(data, StepMetrics):
                    self.insert_step(data)
                elif data is None:
                    self.destroy()
                    return
        except queue.Empty:
            pass

        self.after(100, self.check_queue)

    def insert_task(self, task: MBPPTaskInput):
        self.task = task

        row_wrapper = customtkinter.CTkFrame(self.history_frame, fg_color="transparent")
        row_wrapper.grid(
            row=self._task_row_count, column=0, sticky="ew", padx=5, pady=(0, 6)
        )
        row_wrapper.grid_columnconfigure(0, weight=0)
        row_wrapper.grid_columnconfigure(1, weight=1)
        self._task_row_count += 1


        bubble = customtkinter.CTkFrame(
            row_wrapper,
            corner_radius=16,
            fg_color="#2b2d31",
        )
        bubble.grid(row=0, column=0, sticky="w")
        bubble.grid_columnconfigure(0, weight=1)
        bubble_max_width = 900

        title = customtkinter.CTkLabel(
            bubble,
            text=f"Task #{task.task_id}",
            font=customtkinter.CTkFont(size=16, weight="bold"),
            anchor="w",
        )
        title.grid(row=0, column=0, sticky="ew", padx=16, pady=(12, 4))

        definition_label = customtkinter.CTkLabel(
            bubble,
            text=task.task_definition,
            anchor="w",
            justify="left",
            wraplength=bubble_max_width,
            font=customtkinter.CTkFont(size=13),
        )
        definition_label.grid(row=1, column=0, sticky="ew", padx=16, pady=(0, 8))

        self._add_section_title(bubble, "Signature", row=2, padx=16)
        self._add_code_block(bubble, task.function_definition, row=3, padx=16)

        self._add_section_title(bubble, "Tests", row=4, padx=16)
        tests_text = "\n".join(task.test_list)
        self._add_code_block(bubble, tests_text, row=5, padx=16, last=True)



        steps_wrapper = customtkinter.CTkFrame(self.history_frame, fg_color="transparent")
        steps_wrapper.grid(
            row=self._task_row_count, column=0, sticky="ew", padx=5, pady=(0, 12)
        )
        steps_wrapper.grid_columnconfigure(0, weight=0)
        steps_wrapper.grid_columnconfigure(1, weight=1)
        self._task_row_count += 1

        steps_container = customtkinter.CTkFrame(steps_wrapper, fg_color="transparent")
        steps_container.grid(row=0, column=0, sticky="w", padx=(16, 0))
        steps_container.grid_columnconfigure(0, weight=1)

        self._current_task_frame = steps_container
        self._current_step_row_count = 0

        self._scroll_to_bottom()

    def _add_section_title(self, parent, text: str, row: int, padx: int = 10):
        label = customtkinter.CTkLabel(
            parent,
            text=text,
            anchor="w",
            font=customtkinter.CTkFont(size=11, weight="bold"),
            text_color="#9a9a9a",
        )
        label.grid(row=row, column=0, sticky="ew", padx=padx, pady=(2, 1))
        return label

    def _add_code_block(self, parent, content: str, row: int, padx: int = 10, last: bool = False):
        n_lines = max(1, content.count("\n") + 1)
        height = min(120, 20 * n_lines + 8)

        box = customtkinter.CTkTextbox(
            parent,
            height=height,
            width=850,
            font=customtkinter.CTkFont(family="Consolas", size=12),
            fg_color="#1e1e1e",
            text_color="#d4d4d4",
            wrap="none",
            corner_radius=8,
        )
        box.grid(row=row, column=0, sticky="ew", padx=padx, pady=(0, 12 if last else 6))
        box.insert("1.0", content)
        box.configure(state="disabled")
        return box

    def insert_step(self, step: StepMetrics):
        if self._current_task_frame is None:
            return

        steps_container = self._current_task_frame

        row_wrapper = customtkinter.CTkFrame(steps_container, fg_color="transparent")
        row_wrapper.grid(
            row=self._current_step_row_count, column=0, sticky="ew", pady=(0, 8)
        )
        row_wrapper.grid_columnconfigure(0, weight=0)
        row_wrapper.grid_columnconfigure(1, weight=1)
        self._current_step_row_count += 1


        bubble = customtkinter.CTkFrame(
            row_wrapper,
            corner_radius=16,
            fg_color="#1b3855",
        )
        bubble.grid(row=0, column=0, sticky="w")
        bubble.grid_columnconfigure(0, weight=1)
        bubble_max_width = 900

        title = customtkinter.CTkLabel(
            bubble,
            text=f"Calling {step.model_name}",
            font=customtkinter.CTkFont(size=13, weight="bold"),
            anchor="w",
        )
        title.grid(row=0, column=0, sticky="ew", padx=14, pady=(10, 4))

        self._add_code_block(bubble, step.llm_output, row=1, padx=14, last=True)
        row_wrapper_sandbox = customtkinter.CTkFrame(steps_container, fg_color="transparent")
        row_wrapper_sandbox.grid(
            row=self._current_step_row_count, column=0, sticky="ew", pady=(0, 8)
        )
        row_wrapper_sandbox.grid_columnconfigure(0, weight=0)
        row_wrapper_sandbox.grid_columnconfigure(1, weight=1)
        self._current_step_row_count += 1

        sandbox_bubble = customtkinter.CTkFrame(
            row_wrapper_sandbox,
            corner_radius=16,
            fg_color="#3b2f1f", 
        )
        sandbox_bubble.grid(row=0, column=0, sticky="w")
        sandbox_bubble.grid_columnconfigure(0, weight=1)

        sandbox_title = customtkinter.CTkLabel(
            sandbox_bubble,
            text="Sandbox",
            font=customtkinter.CTkFont(size=13, weight="bold"),
            anchor="w",
        )
        sandbox_title.grid(row=0, column=0, sticky="ew", padx=14, pady=(10, 4))

        self._add_section_title(sandbox_bubble, "Python code:", row=1, padx=16)
        self._add_code_block(sandbox_bubble, step.sandbox_input, row=2, padx=14)
        self._add_section_title(sandbox_bubble, "Output", row=3, padx=16)
        self._add_code_block(sandbox_bubble, step.sandbox_output, row=4, padx=14, last=True)

        self._scroll_to_bottom()

    def _scroll_to_bottom(self):
        self.history_frame._parent_canvas.yview_moveto(1.0)


def gui_thread_worker(ui_queue: queue.Queue):
    app = MbppGui(ui_queue=ui_queue)
    app.mainloop()