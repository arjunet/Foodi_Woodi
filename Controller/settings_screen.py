
from View.SettingsScreen.settings_screen import SettingsScreenView


class SettingsScreenController:
    """
    The `SettingsScreenController` class represents a controller implementation.
    Coordinates work of the view with the model.
    The controller implements the strategy pattern. The controller connects to
    the view to control its actions.
    """

    def __init__(self, model):
        self.model = model  # Model.settings_screen.SettingsScreenModel
        self.view = SettingsScreenView(controller=self, model=self.model)

    def get_view(self) -> SettingsScreenView:
        return self.view
