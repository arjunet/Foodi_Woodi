# The screen's dictionary contains the objects of the models and controllers
# of the screens of the application.

from Model.recipe_screen import RecipeScreenModel
from Controller.recipe_screen import RecipeScreenController
from Model.settings_screen import SettingsScreenModel
from Controller.settings_screen import SettingsScreenController
from Model.cuisines_screen import CuisinesScreenModel
from Controller.cuisines_screen import CuisinesScreenController
from Model.authentication_screen import AuthenticationScreenModel
from Controller.authentication_screen import AuthenticationScreenController
from Model.welcome_screen import WelcomeScreenModel
from Controller.welcome_screen import WelcomeScreenController

screens = {
    'welcome screen': {
        'model': WelcomeScreenModel,
        'controller': WelcomeScreenController,
    },
    'authentication screen': {
        'model': AuthenticationScreenModel,
        'controller': AuthenticationScreenController,
    },
    'cuisines screen': {
        'model': CuisinesScreenModel,
        'controller': CuisinesScreenController,
    },
    'recipe screen': {
        'model': RecipeScreenModel,
        'controller': RecipeScreenController,
    },
    'settings screen': {
        'model': SettingsScreenModel,
        'controller': SettingsScreenController,
    },
}