
from View.RecipeScreen.recipe_screen import RecipeScreenView


class RecipeScreenController:
    """
    The `RecipeScreenController` class represents a controller implementation.
    Coordinates work of the view with the model.
    The controller implements the strategy pattern. The controller connects to
    the view to control its actions.
    """

    def __init__(self, model):
        self.model = model  # Model.recipe_screen.RecipeScreenModel
        self.view = RecipeScreenView(controller=self, model=self.model)

    def get_view(self) -> RecipeScreenView:
        return self.view
