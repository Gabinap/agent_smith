from srcs.agents.agent_mbpp import Mbpp
from srcs.gui.main import gui_thread_worker
import threading
import queue
import time


def main():

    ui_queue = queue.Queue()

    gui_thread = threading.Thread(target=gui_thread_worker,
                                  args=(ui_queue,),
                                  daemon=True)
    gui_thread.start()

    time.sleep(1)

    agent = Mbpp(
        task_file="moulinette/task.json",
        api_url="https://generativelanguage.googleapis.com/v1/interactions",
        model_name="gemma-4-31b-it",
        ui_queue_push=ui_queue.put
    )
    agent.run_agent()

    ui_queue.put("Stop")
    gui_thread.join()


if __name__ == "__main__":
    main()
