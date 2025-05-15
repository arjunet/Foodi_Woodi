
from View.AuthenticationScreen.authentication_screen import AuthenticationScreenView


class AuthenticationScreenController:
    """
    The `AuthenticationScreenController` class represents a controller implementation.
    Coordinates work of the view with the model.
    The controller implements the strategy pattern. The controller connects to
    the view to control its actions.
    """

    def __init__(self, model):
        self.model = model  # Model.authentication_screen.AuthenticationScreenModel
        self.view = AuthenticationScreenView(controller=self, model=self.model)

    def get_view(self) -> AuthenticationScreenView:
        return self.view
