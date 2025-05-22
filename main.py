# Imports

import pyrebase
import requests
import os
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.scrollview import ScrollView
from kivy.uix.textinput import TextInput
from kivy.uix.screenmanager import ScreenManager, Screen, FadeTransition
from kivy.utils import get_color_from_hex
from kivy.uix.popup import Popup
from kivy.uix.widget import Widget
from kivy.uix.relativelayout import RelativeLayout
from kivy.graphics import Color, Rectangle, Ellipse
from kivy.properties import NumericProperty
from kivy.core.window import Window
from kivy.clock import Clock
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.stacklayout import StackLayout
from kivy.metrics import dp, sp
from kivy.animation import Animation
from functools import partial # Import partial for button callbacks
from kivy.network.urlrequest import UrlRequest

# Lock orientation to portrait
Window.orientation = 'portrait'

# Firebase Configuration

config = {
    "apiKey": "AIzaSyBzhPxemvqtZykNHGuyoPNVTQqxutUnYNE",
    "authDomain": "foodi-woodi.firebaseapp.com",
    "databaseURL": "https://foodi-woodi-default-rtdb.firebaseio.com/",
    "storageBucket": "foodi-woodi.appspot.com"
}
firebase = pyrebase.initialize_app(config)
auth = firebase.auth()
db = firebase.database()

def refresh_token(refresh_token):
    api_key = config["apiKey"]
    request_url = f"https://securetoken.googleapis.com/v1/token?key={api_key}"
    headers = {"content-type": "application/x-www-form-urlencoded"}
    data = {"grant_type": "refresh_token", "refresh_token": refresh_token}

    try:
        response = requests.post(request_url, headers=headers, data=data)
        response.raise_for_status()
        return response.json().get('id_token'), response.json().get('refresh_token')
    except Exception as e:
        pass


def save_tokens(id_token, refresh_token):
    with open("auth_tokens.txt", "w") as f:
        f.write(f"{id_token}\n{refresh_token}")


def load_tokens():
    try:
        with open("auth_tokens.txt", "r") as f:
            tokens = f.read().splitlines()
            if len(tokens) >= 2:
                return tokens[0], tokens[1]
            return None, None
    except (FileNotFoundError, ValueError, IndexError):
        return None, None

# ----------------------------------------------------------------------------------------------------------------------

# Popup Classes

class EmailNotVerifiedPopup(Popup):
    def __init__(self, id_token, **kwargs):
        super().__init__(**kwargs)
        self.id_token = id_token
        self.title = "Email Not Verified"
        self.size_hint = (0.8, None)
        self.height = dp(400)

        content = BoxLayout(orientation='vertical', padding=10, spacing=10)
        content.add_widget(Label(
            text="Your email is not verified. Please check your inbox or resend the verification email.",
            halign='center',
            valign='middle',
            size_hint_y=None,
            height=100
        ))

        button_layout = BoxLayout(orientation='horizontal', size_hint_y=None, height=44)
        resend_button = Button(text="Resend Email", size_hint=(None, None), size=(120, 44))
        close_button = Button(text="Close", size_hint=(None, None), size=(100, 44))

        resend_button.bind(on_press=self.resend_verification)
        close_button.bind(on_press=self.dismiss)

        button_layout.add_widget(resend_button)
        button_layout.add_widget(close_button)
        content.add_widget(button_layout)
        self.content = content

    def resend_verification(self, instance):
        try:
            auth.send_email_verification(self.id_token)
            SuccessEmail().open()
            self.dismiss()
        except Exception as e:
            Failiure().open()

class TitleErrorPopup(Popup):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.title = "Error"
        self.size_hint = (0.8, None)
        self.height = dp(400)

        content = BoxLayout(
            orientation='vertical',
            padding=10,
            spacing=10
        )
        content.add_widget(Label(text="Title for recipe is required"))

        button_layout = BoxLayout(
            orientation='horizontal',
            size_hint_y=None,
            height=44
        )
        close_button = Button(
            text="Close",
            size_hint=(None, None),
            size=(100, 44)
        )

        close_button.bind(on_press=self.dismiss)
        button_layout.add_widget(Widget())
        button_layout.add_widget(close_button)
        button_layout.add_widget(Widget())
        content.add_widget(button_layout)
        self.content = content


class Verifacation(Popup):
    def __init__(self, email, password, username, **kwargs):
        super().__init__(**kwargs)
        self.email = email
        self.password = password
        self.username = username
        self.title = "Verify"
        self.size_hint = (0.8, None)
        self.height = dp(400)

        content = BoxLayout(
            orientation='vertical',
            padding=10,
            spacing=10
        )
        content.add_widget(Label(
            text="An email will be sent to this email address. Please open the email and verify your account."))

        button_layout = BoxLayout(
            orientation='horizontal',
            size_hint_y=None,
            height=44
        )
        send_email_btn = Button(
            text="Send email",
            size_hint=(None, None),
            size=(100, 44)
        )

        send_email_btn.bind(on_press=self.signup)
        button_layout.add_widget(Widget())
        button_layout.add_widget(send_email_btn)
        button_layout.add_widget(Widget())
        content.add_widget(button_layout)
        self.content = content

    def signup(self, instance):
        try:
            user = auth.create_user_with_email_and_password(self.email, self.password)
            auth.send_email_verification(user['idToken'])
            save_tokens(user['idToken'], user['refreshToken'])

            db.child("users").child(user['localId']).set({
                "email": self.email,
                "username": self.username
            })

            with open("user.txt", "w") as f:
                f.write(self.username)

            # Switch to log in screen
            App.get_running_app().root.current = 'login'
            self.dismiss()
        except Exception as e:
            error_str = str(e)
            if "WEAK_PASSWORD" in error_str:
                PasswordErrorPopup().open()
            elif "INVALID_EMAIL" in error_str:
                EmailErrorPopup().open()
            elif "EMAIL_EXISTS" in error_str:
                ExistsErrorPopup().open()
            else:
                Failiure().open()

class IngredientsErrorPopup(Popup):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.title = "Error"
        self.size_hint = (0.8, None)
        self.height = dp(400)

        content = BoxLayout(
            orientation='vertical',
            padding=10,
            spacing=10
        )
        content.add_widget(Label(text="Ingredients for recipe is required"))

        button_layout = BoxLayout(
            orientation='horizontal',
            size_hint_y=None,
            height=44
        )
        close_button = Button(
            text="Close",
            size_hint=(None, None),
            size=(100, 44)
        )

        close_button.bind(on_press=self.dismiss)
        button_layout.add_widget(Widget())
        button_layout.add_widget(close_button)
        button_layout.add_widget(Widget())
        content.add_widget(button_layout)
        self.content = content

class StepsErrorPopup(Popup):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.title = "Error"
        self.size_hint = (0.8, None)
        self.height = dp(400)

        content = BoxLayout(
            orientation='vertical',
            padding=10,
            spacing=10
        )
        content.add_widget(Label(text="At least one step is required"))

        button_layout = BoxLayout(
            orientation='horizontal',
            size_hint_y=None,
            height=44
        )
        close_button = Button(
            text="Close",
            size_hint=(None, None),
            size=(100, 44)
        )

        close_button.bind(on_press=self.dismiss)
        button_layout.add_widget(Widget())
        button_layout.add_widget(close_button)
        button_layout.add_widget(Widget())
        content.add_widget(button_layout)
        self.content = content


class PasswordErrorPopup(Popup):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.title = "Password Error"
        self.size_hint = (0.8, None)
        self.height = dp(400)

        content = BoxLayout(
            orientation='vertical',
            padding=10,
            spacing=10
        )
        content.add_widget(Label(text="Password must be 6 characters or more"))

        button_layout = BoxLayout(
            orientation='horizontal',
            size_hint_y=None,
            height=44
        )
        close_button = Button(
            text="Close",
            size_hint=(None, None),
            size=(100, 44)
        )

        close_button.bind(on_press=self.dismiss)
        button_layout.add_widget(Widget())
        button_layout.add_widget(close_button)
        button_layout.add_widget(Widget())
        content.add_widget(button_layout)
        self.content = content


class EmailErrorPopup(Popup):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.title = "Email Error"
        self.size_hint = (0.8, None)
        self.height = dp(400)
        content = BoxLayout(
            orientation='vertical',
            padding=10,
            spacing=10
        )

        content.add_widget(Label(text="Email is invalid"))
        button_layout = BoxLayout(
            orientation='horizontal',
            size_hint_y=None,
            height=44)

        close_button = Button(
            text="Close",
            size_hint=(None, None),
            size=(100, 44))

        close_button.bind(on_press=self.dismiss)
        button_layout.add_widget(Widget())
        button_layout.add_widget(close_button)
        button_layout.add_widget(Widget())
        content.add_widget(button_layout)
        self.content = content


class CredentialsErrorPopup(Popup):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.title = "Invalid Credentials"
        self.size_hint = (0.8, None)
        self.height = dp(400)
        content = BoxLayout(
            orientation='vertical',
            padding=10,
            spacing=10)

        content.add_widget(Label(text="Invalid email or password"))
        button_layout = BoxLayout(
            orientation='horizontal',
            size_hint_y=None,
            height=44)

        close_button = Button(
            text="Close",
            size_hint=(None, None),
            size=(100, 44))

        close_button.bind(on_press=self.dismiss)
        button_layout.add_widget(Widget())
        button_layout.add_widget(close_button)
        button_layout.add_widget(Widget())
        content.add_widget(button_layout)
        self.content = content


class ExistsErrorPopup(Popup):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.title = "Exists"
        self.size_hint = (0.8, None)
        self.height = dp(400)

        content = BoxLayout(
            orientation='vertical',
            padding=10,
            spacing=10)

        content.add_widget(Label(text="Account Already Exists"))
        button_layout = BoxLayout(
            orientation='horizontal',
            size_hint_y=None,
            height=44)

        close_button = Button(
            text="Close",
            size_hint=(None, None),
            size=(100, 44))

        close_button.bind(on_press=self.dismiss)
        button_layout.add_widget(Widget())
        button_layout.add_widget(close_button)
        button_layout.add_widget(Widget())
        content.add_widget(button_layout)
        self.content = content

class ServerError(Popup):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.title = "Server error"
        self.size_hint = (0.8, None)
        self.height = dp(400)

        content = BoxLayout(
            orientation='vertical',
            padding=10,
            spacing=10)

        content.add_widget(Label(text="There is a server error. We are trying hard to fix it. Please check back later."))
        button_layout = BoxLayout(
            orientation='horizontal',
            size_hint_y=None,
            height=44)

        close_button = Button(
            text="Close",
            size_hint=(None, None),
            size=(100, 44))

        close_button.bind(on_press=self.dismiss)
        button_layout.add_widget(Widget())
        button_layout.add_widget(close_button)
        button_layout.add_widget(Widget())
        content.add_widget(button_layout)
        self.content = content

class SuccessEmail(Popup):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.title = "Success"
        self.size_hint = (0.8, None)
        self.height = dp(400)

        content = BoxLayout(
            orientation='vertical',
            padding=10,
            spacing=10)

        content.add_widget(Label(text="Email Successfully sent"))
        button_layout = BoxLayout(
            orientation='horizontal',
            size_hint_y=None,
            height=44)

        close_button = Button(
            text="Close",
            size_hint=(None, None),
            size=(100, 44))

        close_button.bind(on_press=self.dismiss)
        button_layout.add_widget(Widget())
        button_layout.add_widget(close_button)
        button_layout.add_widget(Widget())
        content.add_widget(button_layout)
        self.content = content

class Success(Popup):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.title = "Success"
        self.size_hint = (0.8, None)
        self.height = dp(400)

        content = BoxLayout(
            orientation='vertical',
            padding=10,
            spacing=10)

        content.add_widget(Label(text="Recipe Submitted successfully"))
        button_layout = BoxLayout(
            orientation='horizontal',
            size_hint_y=None,
            height=44)

        close_button = Button(
            text="Close",
            size_hint=(None, None),
            size=(100, 44))

        close_button.bind(on_press=self.dismiss)
        button_layout.add_widget(Widget())
        button_layout.add_widget(close_button)
        button_layout.add_widget(Widget())
        content.add_widget(button_layout)
        self.content = content

class Failiure(Popup):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.title = "Error"
        self.size_hint = (0.8, None)
        self.height = dp(400)

        content = BoxLayout(
            orientation='vertical',
            padding=10,
            spacing=10)

        content.add_widget(Label(text="Unexpected error"))
        button_layout = BoxLayout(
            orientation='horizontal',
            size_hint_y=None,
            height=44)

        close_button = Button(
            text="Close",
            size_hint=(None, None),
            size=(100, 44))

        close_button.bind(on_press=self.dismiss)
        button_layout.add_widget(Widget())
        button_layout.add_widget(close_button)
        button_layout.add_widget(Widget())
        content.add_widget(button_layout)
        self.content = content

# New Popup for Recipe Deletion Success
class RecipeDeletedSuccessPopup(Popup):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.title = "Success"  # Keeping the title "Success" for theme consistency
        self.size_hint = (0.8, None)
        self.height = dp(400)

        content_layout = BoxLayout(
            orientation='vertical',
            padding=dp(10),
            spacing=dp(10)
        )

        message_label = Label(text="Recipe deleted successfully")
        content_layout.add_widget(message_label)

        button_layout = BoxLayout(
            orientation='horizontal',
            size_hint_y=None,
            height=dp(44), # Using dp
            spacing=dp(10) # Added spacing for consistency if multiple buttons were here
        )
        
        close_button = Button(
            text="Close",
            size_hint=(None, None), # Let button size itself
            size=(dp(100), dp(44))  # Using dp
        )
        close_button.bind(on_press=self.dismiss)

        # Center the button
        button_layout.add_widget(Widget()) # Spacer
        button_layout.add_widget(close_button)
        button_layout.add_widget(Widget()) # Spacer

        content_layout.add_widget(button_layout)
        self.content = content_layout


class PasswordConfirmDeletePopup(Popup):
    def __init__(self, recipe_info, delete_callback, **kwargs):
        super().__init__(**kwargs)
        self.recipe_info = recipe_info
        self.delete_callback = delete_callback

        self.title = "Confirm Deletion"
        self.size_hint = (0.8, None)
        self.height = dp(400)

        content = BoxLayout(orientation='vertical', padding=dp(10), spacing=dp(10))
        
        message_label = Label(
            text=f"Enter password to delete:\n'{self.recipe_info.get('title', 'N/A')}'",
            halign='center',
            valign='middle'
        )
        content.add_widget(message_label)

        self.password_input = TextInput(
            hint_text='Password',
            multiline=False,
            password=True,
            size_hint_y=None,
            height=dp(44)
        )
        content.add_widget(self.password_input)

        self.status_label = Label(text='', size_hint_y=None, height=dp(30), color=(1,0,0,1))
        content.add_widget(self.status_label)

        button_layout = BoxLayout(orientation='horizontal', size_hint_y=None, height=dp(44), spacing=dp(10))
        
        confirm_button = Button(text="Confirm Delete")
        confirm_button.bind(on_press=self.check_password_and_delete)
        
        cancel_button = Button(text="Cancel")
        cancel_button.bind(on_press=self.dismiss)

        button_layout.add_widget(confirm_button)
        button_layout.add_widget(cancel_button)
        content.add_widget(button_layout)
        
        self.content = content

    def check_password_and_delete(self, instance):
        entered_password = self.password_input.text.strip()
        if not entered_password:
            self.status_label.text = "Password cannot be empty."
            return

        current_email = ""
        try:
            with open("email.txt", "r") as f:
                current_email = f.read().strip()
        except FileNotFoundError:
            self.status_label.text = "Error: Email file not found."
            return
        
        if not current_email:
            self.status_label.text = "Error: Current email not found."
            return

        try:
            auth.sign_in_with_email_and_password(current_email, entered_password)
            self.status_label.text = "Password correct. Deleting..."
            self.delete_callback(self.recipe_info)
            self.dismiss()
            RecipeDeletedSuccessPopup().open() # Use the new specific success popup

        except Exception as e:
            error_str = str(e)
            if "INVALID_LOGIN_CREDENTIALS" in error_str or "INVALID_PASSWORD" in error_str:
                self.status_label.text = "Incorrect password."
            else:
                self.status_label.text = "Authentication failed."
                print(f"Password check error: {e}")

# ----------------------------------------------------------------------------------------------------------------------

# Screens

class Settings(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        layout = FloatLayout(size_hint=(1, 1))

        screen_width, screen_height = Window.size
        base_font_size = min(screen_width, screen_height) / 20

        self.settings_label = Label(
            text="Settings:",
            font_size=sp(28),
            color=get_color_from_hex('#ffffff'),
            size_hint=(None, None),
            pos_hint={'center_x': 0.5, 'top': 1},
            halign='center',
            valign='middle'
        )

        self.Back = Button(
            text="Back",
            font_size=sp(26),
            color=get_color_from_hex('#ffffff'),
            pos_hint={'center_x': 0.5, 'top': 0.8},
            size_hint=(0.7, None),
            height=(dp(70)),
            halign='center',
            background_color=get_color_from_hex('#0f62fe'),
            background_normal=''
        )

        self.Reset_Password = Button(
            text="Forgot Password",
            bold=True,
            font_size=sp(26),
            color=get_color_from_hex('#0f62fe'),
            pos_hint={'center_x': 0.5, 'top': 0.6},
            size_hint=(0.7, None),
            height=(dp(70)),
            halign='center',
            valign='middle',
            background_color=get_color_from_hex('#03ff46'),
            background_normal='',
            padding=(dp(10), dp(5))  # Add padding
        )

        self.Delete_Recipe_Button = Button(
            text="delete recipe",
            bold=True,
            font_size=sp(26),
            color=get_color_from_hex('#FFFFFF'),
            pos_hint={'center_x': 0.5, 'top': 0.4},
            size_hint=(0.7, None),
            height=(dp(70)),
            halign='center',
            background_color=get_color_from_hex('#fc03cf'),
            background_normal=''
        )

        self.Back.bind(on_press=self.Return_to_main_app)
        self.Reset_Password.bind(on_press=self.Go_to_Forgot_Password_screen)
        self.Delete_Recipe_Button.bind(on_press=self.go_to_delete_recipe_screen)

        layout.add_widget(self.settings_label)
        layout.add_widget(self.Back)
        layout.add_widget(self.Reset_Password)
        layout.add_widget(self.Delete_Recipe_Button)
        self.add_widget(layout)

        # Window.bind(size=self.update_label_size)
        Clock.schedule_once(lambda dt: self.update_label_size(Window, Window.size), 0)

    def update_label_size(self, instance, size):
        screen_width, screen_height = size
        base_font_size = min(screen_width, screen_height) / 20

        self.settings_label.font_size = self.scale_font(base_font_size * 1.5)
        self.Back.font_size = self.scale_font(base_font_size * 1.5)
        self.Reset_Password.font_size = self.scale_font(base_font_size * 1.2)
        self.Delete_Recipe_Button.font_size = self.scale_font(base_font_size * 1.2)

        self.settings_label.size = (dp(200), dp(60))
        self.Back.size = (dp(450), dp(50))
        self.Reset_Password.size = (dp(450), dp(50))
        self.Delete_Recipe_Button.size = (dp(450), dp(50))

        self.Back.y = self.settings_label.y - self.settings_label.height - dp(10)
        self.Reset_Password.y = self.Back.y - self.Back.height - dp(10)
        self.Delete_Recipe_Button.y = self.Reset_Password.y - self.Reset_Password.height - dp(10)

    def scale_font(self, size):
        return dp(size)

    def Return_to_main_app(self, instance):
        self.manager.current = 'app'

    def Go_to_Forgot_Password_screen(self, instance):
        self.manager.current = 'forgot'

    def go_to_delete_recipe_screen(self, instance):
        self.manager.current = 'deleterecipe'

class ForgotPassword(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        # Create main layout with proportional spacing
        self.layout = BoxLayout(
            orientation='vertical',
            padding=dp(20),
            spacing=dp(20)
        )

        # Title label
        self.Forgot_password = Label(
            text="Forgot your password?",
            bold=True,
            color=get_color_from_hex('#ff0303'),
            halign='center',
            valign='middle',
            size_hint=(1, None)
        )

        # Instruction label
        self.Instructions = Label(
            text="We'll send an email to reset your password. Close the app and return to login after sending.",
            bold=True,
            color=get_color_from_hex('#030fff'),
            halign='center',
            valign='middle',
            size_hint=(1, None)
        )

        # Action buttons
        self.Ok = Button(
            text="Send Email",
            size_hint=(0.6, None),
            height=dp(50),
            background_color=get_color_from_hex('#fc7303'),
            background_normal='',
            color="black",
            pos_hint={'center_x': 0.5}
        )

        self.Back = Button(
            text="Go Back",
            size_hint=(0.6, None),
            height=dp(50),
            background_color=get_color_from_hex('#ff1303'),
            background_normal='',
            color="black",
            pos_hint={'center_x': 0.5}
        )

        self.Close = Button(
            text="Close app",
            size_hint=(0.6, None),
            height=dp(50),
            background_color=get_color_from_hex('#1eff05'),
            background_normal='',
            color="black",
            opacity=0,
            disabled=True,
            pos_hint={'center_x': 0.5}
        )

        # Add widgets correctly
        self.layout.add_widget(self.Forgot_password)
        self.layout.add_widget(self.Back)
        self.layout.add_widget(self.Instructions)
        self.layout.add_widget(self.Ok)
        self.layout.add_widget(self.Close)  # Corrected from self.Close_App
        self.add_widget(self.layout)

        # Bindings
        self.bind(size=self._update_layout)
        self.Ok.bind(on_press=self.reset_password)
        self.Close.bind(on_press=self.Close_App)  # Corrected binding
        self.Back.bind(on_press=self.go_back)

        # Initial layout calculation
        Clock.schedule_once(lambda dt: self._update_layout(), 0)

    def _update_layout(self, *args):
        """Update all elements with proportional spacing"""
        # Base dimensions
        screen_width = self.width
        screen_height = self.height
        base_size = min(screen_width, screen_height)

        # Font scaling
        self.Forgot_password.font_size = base_size * 0.075
        self.Instructions.font_size = base_size * 0.05
        self.Ok.font_size = base_size * 0.045
        self.Close.font_size = base_size * 0.045

        # Text wrapping
        self.Forgot_password.text_size = (screen_width * 0.9, None)
        self.Instructions.text_size = (screen_width * 0.9, None)

        # Dynamic spacing
        self.layout.spacing = base_size * 0.15

        # Label heights
        self.Forgot_password.height = self.Forgot_password.texture_size[1] * 1.2
        self.Instructions.height = self.Instructions.texture_size[1] * 1.2

    def go_back(self, instance):
        self.manager.current = 'Settings'

    def on_pre_enter(self):
        """Force layout update before screen becomes visible"""
        self._update_layout()
        Clock.schedule_once(lambda dt: self._update_layout(), 0.001)

    def reset_password(self, instance):
        """Handle password reset request"""
        try:
            with open("email.txt", "r") as f:
                email = f.read().strip()

            if email:
                auth.send_password_reset_email(email)
                SuccessEmail().open()
                self.show_close_button()
        except Exception as e:
            ServerError().open()

    def show_close_button(self):
        """Reveal close button with smooth animation"""
        Animation(opacity=1, duration=0.3).start(self.Close)
        self.Close.disabled = False

    def Close_App(self, instance):
        """Close application"""
        App.get_running_app().stop()

class WelcomeScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.loading_popup = None
        self.show_welcome_ui()  # Always show welcome UI first, then goes to the login screen, or auto-logins the user

    def show_welcome_ui(self):
        self.clear_widgets()
        layout = BoxLayout(
            orientation='vertical',
            spacing=dp(20),
            padding=dp(50)
        )

        welcome_label = Label(
            text=f"Welcome to \n Foodi Woodi!!!",
            font_size=sp(32),
            bold=True,
            color=get_color_from_hex('#ffffff')
        )

        proceed_button = Button(
            text="Proceed",
            size_hint=(0.6, 0.15),
            pos_hint={'center_x': 0.5},
            background_color=get_color_from_hex('#0f62fe'),
            background_normal='',
            color="white",
            font_size=sp(24),
        )
        proceed_button.bind(on_press=self.on_proceed_clicked)

        layout.add_widget(welcome_label)
        layout.add_widget(proceed_button)
        self.add_widget(layout)

    def on_proceed_clicked(self, instance):
        self.show_loading("Checking for saved login...")
        Clock.schedule_once(lambda dt: self.attempt_auto_login(), 0.1)

    def attempt_auto_login(self):
        token_result = list(load_tokens())

        try:
            if token_result and len(token_result) == 2:
                stored_id_token, stored_refresh_token = token_result

                # Refresh tokens (to auto-login user to the app)
                new_id_token, new_refresh_token = refresh_token(stored_refresh_token)
                if new_id_token:
                    # Verify token with Firebase
                    user_info = auth.get_account_info(new_id_token)
                    user_id = user_info['users'][0]['localId']

                    # Check user exists in database
                    user_data = db.child("users").child(user_id).get(token=new_id_token).val()
                    if not user_data:
                        raise Exception("User account not found")

                    # Save new tokens and username
                    save_tokens(new_id_token, new_refresh_token)
                    if 'username' in user_data:
                        with open("user.txt", "w") as f:
                            f.write(user_data['username'])

                    # Login successful - goes to main app
                    if self.manager:
                        self.dismiss_loading()
                        self.manager.current = 'app'
                        return

            # If token check fails, the go to the login page
            self.fallback_to_login()

        except Exception as e:
            self.fallback_to_login()

    def fallback_to_login(self):
        self.dismiss_loading()
        try:
            os.remove("auth_tokens.txt")
        except (FileNotFoundError, PermissionError):
            pass
        if self.manager:
            self.manager.current = 'login'

    def show_loading(self, message="Loading..."):
        self.loading_popup = Popup(
            title=message,
            content=BoxLayout(
                orientation='vertical',
                spacing=10,
                children=[
                    Label(text="Checking saved credentials..."),
                    Button(
                        text="Cancel",
                        size_hint_y=None,
                        height=40,
                        on_press=lambda x: self.fallback_to_login()
                    )
                ]
            ),
            size_hint=(None, None),
            size=(300, 200)
        )
        self.loading_popup.open()

    def dismiss_loading(self):
        if self.loading_popup:
            self.loading_popup.dismiss()
            self.loading_popup = None


class LoginScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        main_layout = BoxLayout(
            orientation='vertical',
            spacing=dp(10),
            padding=dp(10)
        )

        input_layout = BoxLayout(
            orientation='vertical',
            spacing=dp(10)
        )

        self.email_input = TextInput(
            hint_text='Email',
            multiline=False,
            background_color=(0, 0, 0, 1),
            font_size=sp(28),
            hint_text_color=(0, 1, 0, 1),
            foreground_color=(1, 1, 1, 1)
        )

        self.password_input = TextInput(
            hint_text='Password',
            multiline=False,
            password=True,
            background_color=(0, 0, 0, 1),
            font_size=sp(28),
            hint_text_color=(0, 1, 0, 1),
            foreground_color=(1, 1, 1, 1)
        )

        input_layout.add_widget(self.email_input)
        input_layout.add_widget(self.password_input)

        self.login_button = Button(
            text='Login',
            size_hint=(1, 0.2),
            background_color=get_color_from_hex('#f57905'),
            background_normal='',
            bold=True,
            font_size=sp(22),
            color="black"
        )
        self.login_button.bind(on_press=self.login)
        main_layout.add_widget(input_layout)
        main_layout.add_widget(self.login_button)

        self.signup_button = Button(
            text=f"Don't have an account?\nCreate one here.",
            size_hint=(1, 0.2),
            background_color=get_color_from_hex('#0f62fe'),
            background_normal='',
            bold=True,
            font_size=sp(22),
            color="white"
        )
        self.signup_button.bind(on_press=self.open_signup_screen)
        main_layout.add_widget(self.signup_button)
        self.add_widget(main_layout)

    def login(self, instance):
        email = self.email_input.text.strip()
        password = self.password_input.text.strip()
        try:
            user = auth.sign_in_with_email_and_password(email, password)

            # Check email verification status
            account_info = auth.get_account_info(user['idToken'])
            email_verified = account_info['users'][0]['emailVerified']

            if not email_verified:
                EmailNotVerifiedPopup(id_token=user['idToken']).open()
                return

            save_tokens(user['idToken'], user['refreshToken'])
            user_data = db.child("users").child(user['localId']).get().val()

            if user_data and 'username' in user_data:
                with open("user.txt", "w") as f:
                    f.write(user_data['username'])

            with open("email.txt", "w") as f:
                f.write(email)

            self.manager.current = 'app'

        except Exception as e:
            error_str = str(e)
            if "INVALID_LOGIN_CREDENTIALS" in error_str or "invalid email" in error_str.lower():
                CredentialsErrorPopup().open()

    def open_signup_screen(self, instance):
        self.manager.current = 'signup'


class SignupScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        layout = BoxLayout(
            orientation='vertical',
            spacing=10,
            padding=10
        )

        self.email_input = TextInput(
            hint_text='Email',
            multiline=False,
            background_color=(0, 0, 0, 1),
            font_size=sp(28),
            hint_text_color=(0, 1, 0, 1),
            foreground_color=(1, 1, 1, 1)
        )

        self.password_input = TextInput(
            password=True,
            hint_text='Password',
            multiline=False,
            background_color=(0, 0, 0, 1),
            font_size=sp(28),
            hint_text_color=(0, 1, 0, 1),
            foreground_color=(1, 1, 1, 1)
        )

        self.Name = TextInput(
            hint_text='Your Name',
            multiline=False,
            background_color=(0, 0, 0, 1),
            font_size=sp(28),
            hint_text_color=(0, 1, 0, 1),
            foreground_color=(1, 1, 1, 1)
        )

        signup_button = Button(
            text="Create Account",
            size_hint=(1, 0.2),
            background_color=get_color_from_hex('#31f505'),
            background_normal='',
            bold=True,
            font_size=sp(22),
            color="black"
        )
        signup_button.bind(on_press=self.verifyopen)


        back_to_login_button = Button(
            text="Back to login",
            size_hint=(1, 0.2),
            background_color=get_color_from_hex('#a905f5'),
            background_normal='',
            bold=True,
            font_size=sp(22),
            color="black"
        )
        back_to_login_button.bind(on_press=self.back_to_login)
        layout.add_widget(self.email_input)
        layout.add_widget(self.password_input)
        layout.add_widget(self.Name)
        layout.add_widget(signup_button)
        layout.add_widget(back_to_login_button)
        self.add_widget(layout)

    def back_to_login(self, instance):
        self.manager.current = 'login'

    def verifyopen(self, instance):
        email = self.email_input.text.strip()
        password = self.password_input.text.strip()
        username = self.Name.text.strip()
        # Pass inputs to the popup
        Verifacation(email=email, password=password, username=username).open()



class AddRecipe(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.cuisine_name = ""  # Store selected cuisine name
        self.layout = BoxLayout(
            orientation='vertical',
            padding=dp(20),
            spacing=dp(20),
        )

        # Add keyboard handling
        self._keyboard = Window.request_keyboard(self._keyboard_closed, self)
        self._keyboard.bind(on_key_down=self._on_keyboard_down)

        self.Back_Button = Button(
            text='Back',
            size_hint=(None, None),
            size=(dp(100), dp(50)),
            pos_hint={'x': 0, 'top': 1},
            background_color=get_color_from_hex('#ff2121'),
            background_normal='',
            bold=True,
            font_size=sp(22),
            color="black"
        )
        self.Back_Button.bind(on_press=self.back)
        self.layout.add_widget(self.Back_Button)

        self.Add_Step = Button(
            text='add step',
            size_hint=(None, None),
            size=(dp(100), dp(50)),
            pos_hint={'y': 0, 'top': 1},
            background_color=get_color_from_hex('#2125ff'),
            background_normal='',
            bold=True,
            font_size=sp(22),
            color="black"
        )
        self.Add_Step.bind(on_press=self.add_step)
        self.layout.add_widget(self.Add_Step)

        # Title input
        self.title_input = TextInput(
            hint_text='Recipe Title goes here',
            background_color=(0, 0, 0, 1),
            foreground_color=(1, 1, 1, 1),
            font_size=sp(28),
            multiline=False,
            padding=dp(10),
        )
        self.layout.add_widget(self.title_input)

        self.ingredients = TextInput(
            hint_text='Ingredients goes here',
            background_color=(0, 0, 0, 1),
            foreground_color=(1, 1, 1, 1),
            font_size=sp(28),
            multiline=False,
            padding=dp(10),
        )
        self.layout.add_widget(self.ingredients)

        # Message label
        self.message = Label(
            font_size=sp(28),
            halign='center',
            size_hint_y=None,
            height=dp(60)
        )
        self.layout.add_widget(self.message)

        # ScrollView for steps
        scroll = ScrollView()
        self.step_grid = GridLayout(cols=1, spacing=dp(10), size_hint_y=None, size_hint_x=1)
        self.step_grid.bind(minimum_height=self.step_grid.setter('height'))

        self.step_inputs = []
        for i in range(1, 8):
            step_row = BoxLayout(orientation='horizontal', size_hint_y=None, height=dp(80), padding=dp(10))
            step_label = Label(
                text=f"Step {i}:",
                font_size=sp(28),
                size_hint=(None, 1),  # Fix size hint to None for width
                width=dp(100),  # Set a fixed width
                halign='left'
            )

            step_input = TextInput(
                background_color=(0, 0, 0, 1),
                foreground_color=(1, 1, 1, 1),
                font_size=sp(28),
                multiline=False,
                padding=dp(10),
            )

            self.step_inputs.append(step_input)
            step_row.add_widget(step_label)
            step_row.add_widget(step_input)
            self.step_grid.add_widget(step_row)

        scroll.add_widget(self.step_grid)
        self.layout.add_widget(scroll)

        # Submit button
        submit_button = Button(
            text='Submit Recipe',
            size_hint=(1, None),
            height=dp(50),
            background_color=get_color_from_hex('#31f505'),
            background_normal='',
            bold=True,
            font_size=sp(22),
            color="black"
        )

        submit_button.bind(on_press=self.submit_recipe)
        self.layout.add_widget(submit_button)

        self.add_widget(self.layout)

    def _keyboard_closed(self):
        if self._keyboard:
            self._keyboard.unbind(on_key_down=self._on_keyboard_down)
            self._keyboard = None

    def _on_keyboard_down(self, keyboard, keycode, text, modifiers):
        if keycode[1] == 'escape':
            self.manager.current = 'app'
            return True

    def on_leave(self):
        # Clear any pending operations
        if self._keyboard:
            self._keyboard.unbind(on_key_down=self._on_keyboard_down)
            self._keyboard = None

    def add_step(self, instance=None):
        step_row = BoxLayout(orientation='horizontal', size_hint_y=None, height=dp(80), padding=dp(10))
        step_label = Label(
            text=f"Step {len(self.step_inputs) + 1}:",
            font_size=sp(28),
            size_hint=(None, 1),  # Fix size hint to None for width
            width=dp(100),  # Set a fixed width
            halign='left'
        )
        step_input = TextInput(
            background_color=(0, 0, 0, 1),
            foreground_color=(1, 1, 1, 1),
            font_size=sp(28),
            multiline=False,
            padding=dp(10),
        )
        self.step_inputs.append(step_input)
        step_row.add_widget(step_label)
        step_row.add_widget(step_input)
        self.step_grid.add_widget(step_row)

    def update_cuisine_name(self, cuisine_name):
        self.message.text = f"Add recipe to {cuisine_name}:"
        self.cuisine_name = cuisine_name  # Store the cuisine name

    def submit_recipe(self, instance):
        # Collect data from inputs
        title = self.title_input.text.strip()
        ingredients = self.ingredients.text.strip()
        steps = [step.text.strip() for step in self.step_inputs if step.text.strip()]

        if not title:
            TitleErrorPopup().open()
            return

        if not steps:
            StepsErrorPopup().open()
            return

        if not ingredients:
            IngredientsErrorPopup().open()
            return

        # Push to Firebase
        try:
            with open("user.txt", "r") as file:  # Lowercase filename
                username = file.read().strip()
        except FileNotFoundError:
            username = "Unknown"

        recipe_data = {
            "Ingredients": ingredients,
            "steps": steps,
            "author": username,
        }

        try:
            (db.child("recipes/cuisines")
             .child(self.cuisine_name)
             .child(username)
             .child(title)
             .set(recipe_data))

            self.clear_inputs()
            Success().open()
        except Exception as e:
            ServerError().open()  # Debugging help

    def clear_inputs(self):
        self.title_input.text = ""
        for step_input in self.step_inputs:
            step_input.text = ""

    def back(self, instance):
        self.manager.current = 'app'


class MainApp(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        Window.clearcolor = [0, 0, 0, 0]
        self.layout = RelativeLayout()
        self.add_widget(self.layout)

        # Create a vertical layout for ALWAYS VISIBLE cuisine buttons in the middle
        self.middle_cuisine_layout = BoxLayout(
            orientation='vertical',
            size_hint=(None, None),
            width=dp(200),
            height=Window.height * 0.8,  # Make it 80% of window height
            spacing=dp(5),
            padding=dp(5),
            pos_hint={'center_x': 0.5, 'top': 0.95}  # Position near the top
        )

        with self.middle_cuisine_layout.canvas.before:
            Color(0, 0, 0, 0.7)
            self.middle_cuisine_layout.bg_rect = Rectangle(
                pos=self.middle_cuisine_layout.pos,
                size=self.middle_cuisine_layout.size
            )
        self.middle_cuisine_layout.bind(pos=self.update_bg_rect, size=self.update_bg_rect)
        self.layout.add_widget(self.middle_cuisine_layout)

        # Add label below middle buttons
        self.cuisine_label = Label(
            text="select a cuisine to view recipes",
            color=(1, 1, 1, 1),  # White color
            font_size='20sp',
            bold=True,
            size_hint=(None, None),
            size=(dp(400), dp(50)),
            pos_hint={'center_x': 0.5, 'y': 0.1}  # Position below the buttons
        )
        self.layout.add_widget(self.cuisine_label)

        # Create a vertical layout for ADD RECIPE cuisine buttons (hidden by default)
        self.add_recipe_cuisine_layout = BoxLayout(
            orientation='vertical',
            size_hint=(None, None),
            width=dp(200),
            height=dp(400),
            spacing=dp(5),
            padding=dp(5),
            opacity=0  # Hidden by default
        )

        with self.add_recipe_cuisine_layout.canvas.before:
            Color(0, 0, 0, 0.7)
            self.add_recipe_cuisine_layout.bg_rect = Rectangle(
                pos=self.add_recipe_cuisine_layout.pos,
                size=self.add_recipe_cuisine_layout.size
            )
        self.add_recipe_cuisine_layout.bind(pos=self.update_bg_rect, size=self.update_bg_rect)
        self.layout.add_widget(self.add_recipe_cuisine_layout)

        cuisines = [
            "Italian",
            "Jamaican",
            "Hispanic",
            "Indian",
            "American",
            "Chinese",
            "General"
        ]

        # Add buttons to both layouts
        for cuisine in cuisines:
            # Middle buttons for viewing recipes
            middle_btn = Button(
                text=cuisine,
                size_hint_y=1,
                background_normal=f'{cuisine}.png',
                color=(0, 0, 0, 1),
                bold=True,
                font_size='18sp',
                border=(0, 0, 0, 1))
            middle_btn.button_type = 'view'  # Add identifier
            middle_btn.cuisine_name = cuisine  # Store cuisine name
            middle_btn.bind(on_press=self.on_cuisine_selected)
            self.middle_cuisine_layout.add_widget(middle_btn)

            # Add recipe buttons for adding recipes
            add_recipe_btn = Button(
                text=cuisine,
                size_hint_y=1,
                background_normal=f'{cuisine}.png',
                color=(0, 0, 0, 1),
                bold=True,
                font_size='18sp',
                border=(0, 0, 0, 1))
            add_recipe_btn.button_type = 'add'  # Add identifier
            add_recipe_btn.cuisine_name = cuisine  # Store cuisine name
            add_recipe_btn.bind(on_press=self.on_add_recipe_selected)
            self.add_recipe_cuisine_layout.add_widget(add_recipe_btn)

        # Keep the add recipe button
        self.add_recipe_button = CircularButton(
            text="+",
            size_hint=(None, None),
            size=(dp(60), dp(60)),
            pos_hint={'bottom': 1, 'right': 0.1}
        )
        self.add_recipe_button.bind(
            on_press=self.toggle_add_recipe_menu,
            pos=self.update_add_recipe_position,
            size=self.update_add_recipe_position)
        self.layout.add_widget(self.add_recipe_button)

        # Keep the settings button
        self.Settings = Button(
            size_hint=(None, None),
            size=(dp(60), dp(60)),
            pos_hint={'bottom': 1, 'right': 1},
            background_normal='settings.png')
        self.Settings.bind(
            on_press=self.open_settings)
        self.layout.add_widget(self.Settings)

    def update_bg_rect(self, instance, value):
        instance.bg_rect.pos = instance.pos
        instance.bg_rect.size = instance.size

    def update_add_recipe_position(self, *args):
        btn = self.add_recipe_button
        btn_x = btn.x
        btn_top = btn.y + btn.height
        
        # Calculate the center position of the button
        btn_center_x = btn_x + (btn.width / 2)
        
        # Calculate the menu position to be centered on the button
        menu_width = self.add_recipe_cuisine_layout.width
        menu_x = btn_center_x - (menu_width / 2)
        
        # Ensure the menu stays within screen bounds
        if menu_x < 0:
            menu_x = 0
        elif menu_x + menu_width > Window.width:
            menu_x = Window.width - menu_width
            
        self.add_recipe_cuisine_layout.pos = (menu_x, btn_top)
        self.add_recipe_cuisine_layout.height = Window.height - btn_top

    def toggle_add_recipe_menu(self, instance):
        if self.add_recipe_cuisine_layout.opacity == 0:
            self.update_add_recipe_position()
            self.add_recipe_cuisine_layout.opacity = 1
            self.middle_cuisine_layout.opacity = 0  # Hide middle buttons
            self.cuisine_label.opacity = 0  # Hide the label
        else:
            self.add_recipe_cuisine_layout.opacity = 0
            self.middle_cuisine_layout.opacity = 1  # Show middle buttons
            self.cuisine_label.opacity = 1  # Show the label

    def on_cuisine_selected(self, instance):
        # Only handle clicks from middle buttons
        if not hasattr(instance, 'button_type') or instance.button_type != 'view':
            return
        # Only proceed if the middle buttons are visible
        if self.middle_cuisine_layout.opacity == 0:
            return
        cuisine_screen = self.manager.get_screen('cuisine_recipes')
        cuisine_screen.update_cuisine_name(instance.cuisine_name)
        self.manager.current = 'cuisine_recipes'

    def on_add_recipe_selected(self, instance):
        # Only handle clicks from add recipe buttons
        if not hasattr(instance, 'button_type') or instance.button_type != 'add':
            return
        # Only proceed if the add recipe menu is visible
        if self.add_recipe_cuisine_layout.opacity == 0:
            return
        add_recipe_screen = self.manager.get_screen('cuisine')
        add_recipe_screen.update_cuisine_name(instance.cuisine_name)
        self.manager.current = 'cuisine'

    def open_settings(self, *args):
        self.manager.current = 'Settings'

    def on_pre_enter(self, *args):
        # Make sure middle buttons and their label are visible
        # and the add recipe menu is hidden when returning to main screen.
        self.middle_cuisine_layout.opacity = 1
        self.add_recipe_cuisine_layout.opacity = 0
        self.cuisine_label.opacity = 1 # Ensure the label is also visible


# ----------------------------------------------------------------------------------------------------------------------

# Define the CuisineRecipesScreen class first
class CuisineRecipesScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.layout = BoxLayout(orientation='vertical')
        self.add_widget(self.layout)

        # Label at the top
        self.cuisine_label = Label(
            text="Recipes for selected cuisine will appear here",
            font_size=sp(24),
            color=(1, 1, 1, 1),
            size_hint_y=None,
            height=dp(50)
        )
        self.layout.add_widget(self.cuisine_label)

        # ScrollView for recipes
        self.scroll_view = ScrollView(size_hint=(1, 1))
        self.recipe_list = GridLayout(cols=1, spacing=10, size_hint_y=None)
        self.recipe_list.bind(minimum_height=self.recipe_list.setter('height'))
        self.scroll_view.add_widget(self.recipe_list)
        self.layout.add_widget(self.scroll_view)

        # Back button
        self.back_button = Button(
            text="Back",
            size_hint=(None, None),
            size=(dp(100), dp(50)),
            pos_hint={'center_x': 0.5},
            background_color=get_color_from_hex('#fc8403'),  # Orange color
            background_normal='',  # Important for background_color to take effect
            color=(0, 0, 0, 1)  # Black text for contrast, adjust if needed
        )
        self.back_button.bind(on_press=self.go_back)
        self.layout.add_widget(self.back_button)

    def update_cuisine_name(self, cuisine_name):
        self.cuisine_label.text = f"Recipes for {cuisine_name}:"
        self.fetch_recipes(cuisine_name)

    def fetch_recipes(self, cuisine_name):
        # Clear existing recipes
        self.recipe_list.clear_widgets()

        try:
            # Fetch recipes from Firebase
            recipes = db.child("recipes/cuisines").child(cuisine_name).get().val()
            if recipes:
                for author, author_recipes in recipes.items():
                    for title, recipe_data in author_recipes.items():
                        recipe_button = Button(
                            text=f"{title} by {author}",
                            size_hint_y=None,
                            height=dp(44), # Using dp for consistent height
                            color=(1, 1, 1, 1),  # White text color for visibility
                            background_color=(0, 0, 0, 1),  # Black background
                            background_normal='',  # Crucial for background_color to work
                            border=(0,0,0,0) # Remove border to make it look like text on a black bg
                        )
                        recipe_button.bind(on_press=self.on_recipe_selected)
                        self.recipe_list.add_widget(recipe_button)
            else:
                no_recipes_label = Label(
                    text="No recipes found for this cuisine.",
                    size_hint_y=None,
                    height=dp(44), # Using dp
                    color=(1, 1, 1, 1)
                )
                self.recipe_list.add_widget(no_recipes_label)
        except Exception as e:
            error_label = Label(
                text=f"Error fetching recipes: {e}", # Show the actual error
                size_hint_y=None,
                height=dp(44), # Using dp
                color=(1, 0, 0, 1) # Red color for error
            )
            self.recipe_list.add_widget(error_label)

    def on_recipe_selected(self, instance):
        # Extract recipe title and author from the button text
        button_text_parts = instance.text.split(" by ")
        if len(button_text_parts) < 2:
            print(f"Error: Button text '{instance.text}' is not in the expected format 'Title by Author'")
            return

        extracted_title = button_text_parts[0].strip()
        extracted_author = button_text_parts[1].strip()

        # Extract cuisine name from the cuisine_label
        # Assuming self.cuisine_label.text is like "Recipes for CuisineName:"
        full_cuisine_label_text = self.cuisine_label.text
        cuisine_name = "UnknownCuisine" # Default
        if "Recipes for " in full_cuisine_label_text and ":" in full_cuisine_label_text:
            try:
                cuisine_name = full_cuisine_label_text.split("Recipes for ")[1].split(":")[0].strip()
            except IndexError:
                print(f"Error parsing cuisine name from label: {full_cuisine_label_text}")
        else:
            print(f"Cuisine label text not in expected format: {full_cuisine_label_text}")
        
        if not all([extracted_title, extracted_author, cuisine_name != "UnknownCuisine"]):
            print(f"Error: Missing key information. Title='{extracted_title}', Author='{extracted_author}', Cuisine='{cuisine_name}'")
            return

        # Construct the correct path including the author
        path = f"recipes/cuisines/{cuisine_name}/{extracted_author}/{extracted_title}"
        print(f"[CuisineRecipesScreen.on_recipe_selected] Attempting to fetch from path: {path}")
        
        try:
            recipe_data = db.child(path).get().val()

            if recipe_data:
                print(f"Recipe data found for '{extracted_title}': {recipe_data}")
                ingredients = recipe_data.get("Ingredients", "No ingredients available")
                # Ensure steps is a list, even if Firebase returns a dict for a single step like {"0": "step_text"}
                steps_data = recipe_data.get("steps", [])
                if isinstance(steps_data, dict): # Convert dict like {"0": "step1", "1": "step2"} to list
                    steps = [steps_data[str(i)] for i in range(len(steps_data))]
                elif isinstance(steps_data, list):
                    steps = steps_data
                else:
                    steps = ["No steps available or steps format is incorrect."]

                view_recipe_screen = self.manager.get_screen('view_recipe')
                # Pass the correctly extracted title
                view_recipe_screen.update_recipe(extracted_title, ingredients, steps) 
                self.manager.current = 'view_recipe'
            else:
                print(f"Recipe not found at path: {path}")
        except Exception as e:
            print(f"Error fetching or displaying recipe in on_recipe_selected: {e}")

    def go_back(self, instance):
        self.manager.current = 'app'

# Circular button properties (used in MainApp class)
class CircularButton(Button):
    radius = NumericProperty(20)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.background_color = (0, 0, 0, 0)
        self.color = (1, 1, 1, 1)
        self.bind(
            pos=self.update_radius,
            size=self.update_radius)
        self.update_radius()

    def update_radius(self, *args):
        self.radius = min(self.width, self.height) / 2
        self.canvas.before.clear()
        with self.canvas.before:
            Color(*get_color_from_hex('#971df5'))
            Ellipse(pos=self.pos, size=(self.radius * 2, self.radius * 2))

# Define the ViewRecipeScreen class first
class ViewRecipeScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Add keyboard handling
        self._keyboard = Window.request_keyboard(self._keyboard_closed, self)
        self._keyboard.bind(on_key_down=self._on_keyboard_down)

        # Main layout will be vertical
        self.main_layout = BoxLayout(orientation='vertical', spacing=dp(10), padding=dp(10))
        self.add_widget(self.main_layout)

        # 1. Recipe Title (Top)
        self.title_label = Label(
            text="Recipe Title", # Placeholder
            font_size=dp(28),   # Larger font for title
            color=get_color_from_hex('#FFFFFF'), # White color
            size_hint_y=None,
            height=dp(60),     # Give it a bit more height
            halign='center',
            valign='middle',
            bold=True
        )
        self.title_label.bind(texture_size=self.title_label.setter('size')) # Adjust size to text
        self.main_layout.add_widget(self.title_label)

        # 2. Ingredients (Middle)
        ingredients_scroll = ScrollView(
            size_hint=(1, 0.4), # Occupies 40% of the available vertical space after title and button
            do_scroll_x=False
        )
        self.ingredients_label = Label(
            text="Ingredients", # Placeholder
            font_size=dp(16),
            color=get_color_from_hex('#FFFFFF'),
            size_hint_y=None, # Height will be determined by content
            text_size=(self.width - dp(40), None), # Allow wrapping, adjust for padding
            halign='left',
            valign='top'
        )
        self.ingredients_label.bind(texture_size=self.ingredients_label.setter('size'))
        ingredients_scroll.add_widget(self.ingredients_label)
        self.main_layout.add_widget(ingredients_scroll)

        # 3. Steps (Bottom)
        steps_scroll = ScrollView(
            size_hint=(1, 0.6), # Occupies 60% of the available vertical space after title and button
            do_scroll_x=False
        )
        self.steps_label = Label(
            text="Steps", # Placeholder
            font_size=dp(16),
            color=get_color_from_hex('#FFFFFF'),
            size_hint_y=None, # Height will be determined by content
            text_size=(self.width - dp(40), None), # Allow wrapping, adjust for padding
            halign='left',
            valign='top'
        )
        self.steps_label.bind(texture_size=self.steps_label.setter('size'))
        steps_scroll.add_widget(self.steps_label)
        self.main_layout.add_widget(steps_scroll)

        # 4. Back Button (Very Bottom)
        self.back_button = Button(
            text="Back",
            font_size=sp(22),
            size_hint=(1, None), # Full width
            height=dp(50),
            background_color=get_color_from_hex('#fc0303'), # Red color
            background_normal='',  # Important for background_color to take effect
            color=get_color_from_hex('#FFFFFF') # White text for contrast
        )
        self.back_button.bind(on_press=self.go_back)
        self.main_layout.add_widget(self.back_button)

        # Bind label widths to screen width for proper text_size updates on resize
        Window.bind(width=self._update_label_widths)
        Clock.schedule_once(lambda dt: self._update_label_widths(Window, Window.width))


    def _update_label_widths(self, instance, width):
        # Adjust text_size of labels when window width changes for proper wrapping
        # Consider padding of the main_layout and scrollviews if any
        effective_width = width - dp(40) # e.g. dp(20) padding on each side of main_layout + scrollview internal padding
        self.ingredients_label.text_size = (effective_width, None)
        self.steps_label.text_size = (effective_width, None)


    def update_recipe(self, title, ingredients, steps):
        print(f"[ViewRecipeScreen.update_recipe] Received title: '{title}'")
        
        # Set the title directly
        self.title_label.text = title

        # Set ingredients text without "Ingredients:" prefix
        if not isinstance(ingredients, str):
            ingredients = str(ingredients) if ingredients is not None else "No ingredients available"
        self.ingredients_label.text = ingredients

        # Set steps text without "Steps:" prefix, but keep numbering
        if not isinstance(steps, list):
            steps = [str(steps)] if steps is not None else ["No steps available"]
        
        # Just join the steps, assuming they are already formatted or just need listing
        formatted_steps = "\n".join(step_item for step_item in steps)
        self.steps_label.text = formatted_steps
        
        # Force a layout update for the labels inside scrollviews
        self.ingredients_label.texture_update()
        self.steps_label.texture_update()
        Clock.schedule_once(lambda dt: self._update_label_widths(Window, Window.width))


    def go_back(self, instance):
        self.manager.current = 'cuisine_recipes'

    def _keyboard_closed(self):
        if self._keyboard:
            self._keyboard.unbind(on_key_down=self._on_keyboard_down)
            self._keyboard = None

    def _on_keyboard_down(self, keyboard, keycode, text, modifiers):
        if keycode[1] == 'escape':
            self.manager.current = 'cuisine_recipes'
            return True

    def on_leave(self):
        # Clear any pending operations
        if self._keyboard:
            self._keyboard.unbind(on_key_down=self._on_keyboard_down)
            self._keyboard = None

# Define the DeleteRecipeScreen class
class DeleteRecipeScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.layout = BoxLayout(orientation='vertical', padding=dp(10), spacing=dp(30))

        title_label = Label(
            text="Your Uploaded Recipes",
            font_size=sp(26),
            size_hint_y=None,
            height=dp(50),
            color=get_color_from_hex('#FFFFFF')
        )
        self.layout.add_widget(title_label)

        self.scroll_view = ScrollView(size_hint=(1, 1)) 
        self.recipe_list_layout = GridLayout(cols=1, spacing=dp(5), size_hint_y=None)
        self.recipe_list_layout.bind(minimum_height=self.recipe_list_layout.setter('height'))
        self.scroll_view.add_widget(self.recipe_list_layout)
        self.layout.add_widget(self.scroll_view)

        back_button = Button(
            text="Back to Settings",
            size_hint=(1, None),
            height=dp(50),
            background_color=get_color_from_hex('#fc8403'),
            background_normal='',
            color=get_color_from_hex('#000000')
        )
        back_button.bind(on_press=self.go_back_to_settings)
        self.layout.add_widget(back_button)

        self.add_widget(self.layout)

    def go_back_to_settings(self, instance):
        self.manager.current = 'Settings'

    def load_user_recipes(self):
        self.recipe_list_layout.clear_widgets()
        username = ""
        try:
            with open("user.txt", "r") as f:
                username = f.read().strip()
        except FileNotFoundError:
            error_label = Label(text="Error: User file not found.", color=(1,0,0,1), size_hint_y=None, height=dp(44))
            error_label.texture_update() # Force texture update
            self.recipe_list_layout.add_widget(error_label)
            return

        if not username:
            error_label = Label(text="Error: Username is empty.", color=(1,0,0,1), size_hint_y=None, height=dp(44))
            error_label.texture_update() # Force texture update
            self.recipe_list_layout.add_widget(error_label)
            return

        all_recipes_data = db.child("recipes/cuisines").get().val()
        found_recipes_for_user = False
        if all_recipes_data:
            for cuisine_name, authors in all_recipes_data.items():
                if isinstance(authors, dict) and username in authors:
                    user_recipes_in_cuisine = authors[username]
                    if isinstance(user_recipes_in_cuisine, dict):
                        for recipe_title, recipe_data_val in user_recipes_in_cuisine.items():
                            found_recipes_for_user = True
                            recipe_info = {
                                'title': recipe_title,
                                'cuisine': cuisine_name,
                                'author': username
                            }
                            recipe_btn = Button(
                                text=f"{recipe_title} (Cuisine: {cuisine_name})",
                                size_hint_y=None,
                                height=dp(44),
                                background_color=(0.1, 0.1, 0.1, 1), 
                                background_normal='',
                                color=(1,1,1,1)
                            )
                            recipe_btn.bind(on_press=partial(self.open_confirm_delete_popup, recipe_info))
                            self.recipe_list_layout.add_widget(recipe_btn)
        
        if not found_recipes_for_user:
            no_recipes_label = Label(
                text="You have not uploaded any recipes.",
                color=(1,1,1,1),
                size_hint_y=None,
                height=dp(60), 
                halign='center', 
                valign='middle'  
            )
            no_recipes_label.bind(width=lambda instance, value: setattr(instance, 'text_size', (value, None)))
            self.recipe_list_layout.add_widget(no_recipes_label)
            # It's good practice to schedule an update for the label's texture
            # after adding it and its properties might affect its size.
            Clock.schedule_once(lambda dt, label=no_recipes_label: label.texture_update(), -1)


    def open_confirm_delete_popup(self, recipe_info, instance_button):
        popup = PasswordConfirmDeletePopup(
            recipe_info=recipe_info,
            delete_callback=self.execute_delete_recipe
        )
        popup.open()

    def execute_delete_recipe(self, recipe_info):
        try:
            path = f"recipes/cuisines/{recipe_info['cuisine']}/{recipe_info['author']}/{recipe_info['title']}"
            db.child(path).remove()
            print(f"Recipe '{recipe_info['title']}' deleted from Firebase at path: {path}")
            self.load_user_recipes() 
        except Exception as e:
            print(f"Error deleting recipe from Firebase: {e}")
            Failiure(title="DeletionError", content=Label(text="Could not delete recipe.")).open()


    def on_pre_enter(self, *args):
        self.load_user_recipes()

# Screen manager (used to switch screens via buttons)
class MyScreenManager(ScreenManager):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.add_widget(WelcomeScreen(name='welcome'))
        self.add_widget(LoginScreen(name='login'))
        self.add_widget(MainApp(name='app'))
        self.add_widget(SignupScreen(name='signup'))
        self.add_widget(AddRecipe(name='cuisine'))
        self.add_widget(Settings(name='Settings'))
        self.add_widget(ForgotPassword(name='forgot'))
        self.add_widget(CuisineRecipesScreen(name='cuisine_recipes'))
        self.add_widget(ViewRecipeScreen(name='view_recipe'))
        self.add_widget(DeleteRecipeScreen(name='deleterecipe'))

# Build and run the app
class MyApp(App):
    def build(self):
        return MyScreenManager(transition=FadeTransition())


if __name__ == '__main__':
    MyApp().run()
