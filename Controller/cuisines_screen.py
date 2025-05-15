
from View.CuisinesScreen.cuisines_screen import CuisinesScreenView


class CuisinesScreenController:
    """
    The `CuisinesScreenController` class represents a controller implementation.
    Coordinates work of the view with the model.
    The controller implements the strategy pattern. The controller connects to
    the view to control its actions.
    """

    def __init__(self, model):
        self.model = model  # Model.cuisines_screen.CuisinesScreenModel
        self.view = CuisinesScreenView(controller=self, model=self.model)

    def get_view(self) -> CuisinesScreenView:
        return self.view
