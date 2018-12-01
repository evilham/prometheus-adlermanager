module Model exposing (Model, Msg(..), init)

import Http
import Time

import Utils

type alias Model =
    { loading  : Bool
    , data     : List String
    , now      : Time.Posix
    , err      : Maybe Http.Error
    }

type Msg = NewData       (Result Http.Error (List String))
         | NewNow        Time.Posix
         | RefreshWanted

-- INIT --

init : () -> Model
init flags =
    { loading  = True
    , data     = []
    , now      = Utils.time_0
    , err      = Nothing
    }
