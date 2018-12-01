module View exposing (view)

import Browser
import Html    exposing (text)

import Model exposing (Model, Msg(..))

view : Model -> Browser.Document Msg
view model =
    { title = "Hello World"
    , body  = [text "hello", text "world"]
    }
