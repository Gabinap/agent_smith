from srcs.agents.agent_mbpp import Mbpp
import flet as ft
from srcs.gui.app import MbppGui 
import threading

def main():
    gui = MbppGui()
    def flet_main(page: ft.Page):
        gui.main(page) 
        agent = Mbpp(
            task_file="moulinette/task.json",
            api_url="https://generativelanguage.googleapis.com/v1/interactions",
            model_name="gemma-4-31b-it",
            update_state=gui.update_task
        )
        threading.Thread(target=agent.run_agent, daemon=True).start()
        
    ft.run(flet_main)

if __name__ == "__main__":
    main()
