import flet as ft
from srcs.agents.agent_mbpp import Mbpp
from srcs.models.tasks import MBPPTaskInput


class MbppGui:
    """Interface Flet pour visualiser une tâche MBPP."""
 
    def __init__(self):
        self.page: ft.Page | None = None
        self.task_view: ft.Column | None = None
 
    def main(self, page: ft.Page):
        self.page = page
        page.title = "Agent Smith"
        page.theme_mode = ft.ThemeMode.DARK
        page.padding = 30
        page.scroll = ft.ScrollMode.AUTO
 
        self.task_view = ft.Column(spacing=2.5, expand=True)
 
        page.add(
            ft.Row(
                [
                    ft.Text("Agent Smith", size=26, weight=ft.FontWeight.BOLD),
                ],
            ),
            ft.Text("Mostly Basic Python Problems", size=13, italic=True),
            ft.Divider(),
            self.task_view,
        )
 
    def _code_block(self, code: str) -> ft.Container:
        return ft.Container(
            content=ft.Text(code, font_family="Consolas, Menlo, monospace", size=13, selectable=True),
            bgcolor=ft.Colors.BLACK26,
            border_radius=8,
            padding=12,
        )
 
    def build_task_card(self, task: MBPPTaskInput) -> ft.Card:
        """Construit une carte visuelle pour une tâche MBPP."""
 
        content_items = [
            ft.Row(
                [
                    ft.Container(
                        content=ft.Text(f"Task #{task.task_id}", weight=ft.FontWeight.BOLD, size=12),
                        bgcolor=ft.Colors.DEEP_PURPLE_400,
                        border_radius=20,
                        padding=10,
                    )
                ]
            ),
            ft.Text(task.task_definition, size=15, weight=ft.FontWeight.W_500),
            ft.Text("Signature", size=12, weight=ft.FontWeight.BOLD),
            self._code_block(task.function_definition),
        ]
 
        if task.test_imports:
            content_items.append(ft.Text("Imports tests", size=12, weight=ft.FontWeight.BOLD))
            content_items.append(self._code_block("\n".join(task.test_imports)))
 
        if task.test_list:
            content_items.append(ft.Text("Tests", size=12, weight=ft.FontWeight.BOLD))
            content_items.append(self._code_block("\n".join(task.test_list)))
 
        return ft.Card(
            content=ft.Container(
                content=ft.Column(content_items, spacing=10),
                padding=20,
            ),
            elevation=6,
        )
 
    def update_task(self, task: MBPPTaskInput):
        if self.task_view is not None:
            self.task_view.controls = self.build_task_card(task)
        if self.page:
            self.page.update()
    
    