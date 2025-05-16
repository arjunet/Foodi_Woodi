
from View.WelcomeScreen.welcome_screen import WelcomeScreenView


class WelcomeScreenController:
    """
    The `WelcomeScreenController` class represents a controller implementation.
    Coordinates work of the view with the model.
    The controller implements the strategy pattern. The controller connects to
    the view to control its actions.
    """

    def __init__(self, model):
        self.model = model  # Model.welcome_screen.WelcomeScreenModel
        self.view = WelcomeScreenView(controller=self, model=self.model)

    def get_view(self) -> WelcomeScreenView:
        return self.view
