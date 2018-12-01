module Main exposing (main)

import Browser

import Model
import Update
import View
import Subscriptions

main = Browser.document
    { init   = \flags -> (Model.init flags, Update.init)
    , update = Update.update
    , view   = View.view
    , subscriptions = Subscriptions.subscriptions
    }
