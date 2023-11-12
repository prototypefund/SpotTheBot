import os
import random

from loguru import logger
from nicegui import ui, Client

from src.dataobjects import ViewCallbacks, Field
from src.gui.elements.content_class import ContentPage
from src.gui.elements.dialogs import info_dialog, result_dialog
from src.gui.elements.frame import frame
from src.gui.elements.interactive_text import InteractiveText
from src.gui.tools import get_from_local_storage


class GameContent(ContentPage):
    def __init__(self, client: Client, callbacks: ViewCallbacks) -> None:
        super().__init__(client, callbacks)
        self.points = 25
        self.text_points = None
        self.timer = None

        self.submit_human = "I am sure it is fine..."
        self.submit_bot = "It is a bot!"

        self.user = None

    def init_javascript(self, button_id: str) -> None:
        init_js = (
            "window.spotTheBot = {",
            "    tag_count: {},",
            f"    submit_button: document.getElementById('{button_id}'),",
            "    increment: function(tag) {",
            f"        console.log(\"incrementing \" + tag + \"...\"); "
            "        this.tag_count[tag] = (this.tag_count[tag] || 0) + 1;",
            "        this.submit_button.children[1].children[0].innerText = '" + self.submit_bot + "';",
            "        return this.tag_count[tag];",
            "    },",
            "    decrement: function(tag) {",
            f"        console.log(\"decrementing \" + tag + \"...\"); ",
            "        this.tag_count[tag]--;",
            "        let sum = 0;",
            "        for (let key in this.tag_count) {",
            "            sum += this.tag_count[key];",
            "        }",
            "        if (sum === 0) {",
            f"            this.submit_button.children[1].children[0].innerText = '{self.submit_human}';",
            "        }",
            "        return this.tag_count[tag];",
            "    }",
            "};"
        )
        _ = ui.run_javascript("\n".join(init_js))

    def decrement_points(self) -> None:
        if 5 < self.points:
            self.points -= 1
        else:
            self.timer.deactivate()

        self.text_points.content = f"{self.points} points remaining"

    async def create_content(self) -> None:
        logger.info("Game page")

        await self.client.connected()

        # app.on_connect(self.init_tag_count)

        name_hash = await get_from_local_storage("name_hash")
        if name_hash is None:
            ui.open("/")

        self.user = self.callbacks.get_user(name_hash)
        snippet = self.callbacks.get_next_snippet(self.user)

        word_count = len(snippet.text.split())
        self.points = word_count // 4

        with frame() as _frame:
            interactive_text = InteractiveText(snippet)

            with ui.column() as column:
                text_display = interactive_text.get_content()

                self.text_points = ui.markdown(f"{self.points} points remaining")

                with ui.row() as row:
                    # retrieve stats
                    text_paranoid = ui.markdown("paranoid")
                    element_diagram = ui.element()
                    text_gullible = ui.markdown("gullible")

            submit_button = ui.button(
                self.submit_human,
                on_click=lambda: self.submit(interactive_text, self.points)
            )
            submit_button.classes("w-full justify-center")
            self.init_javascript(f"c{submit_button.id}")

        self.timer = ui.timer(1, self.decrement_points)

    async def submit(self, interactive_text: InteractiveText, points: int) -> None:
        identity_file = await get_from_local_storage("identity_file")
        if identity_file is not None and os.path.isfile(identity_file):
            os.remove(identity_file)

        correct = interactive_text.snippet.is_bot == (0 < len(interactive_text.selected_tags))
        correct_str = "correctly" if correct else "incorrectly"

        snippet_id = interactive_text.snippet.db_id
        self.user.recent_snippet_ids.append(snippet_id)

        if correct and interactive_text.snippet.is_bot:
            # precise
            state = Field.TRUE_POSITIVES

        elif correct:
            # specific
            state = Field.TRUE_NEGATIVES

        elif interactive_text.snippet.is_bot:
            # gullible
            state = Field.FALSE_NEGATIVES

        else:
            # paranoid
            state = Field.FALSE_POSITIVES

        self.callbacks.update_user_state(self.user, state)

        tags = interactive_text.selected_tags
        if len(tags) < 1:
            selection = await result_dialog(
                f"{self.user.secret_name_hash} {correct_str.upper()} assumed {interactive_text.snippet.db_id} "
                f"as HUMAN with {points} points"
            )
        else:
            self.callbacks.update_markers(tags, correct)
            selection = await result_dialog(
                f"{self.user.secret_name_hash} {correct_str.upper()} assumed {interactive_text.snippet.db_id} "
                f"as BOT with {points} points because of {str(tags)}"
            )

        if selection == "continue":
            ui.open("/game")
        else:
            ui.open("/")
