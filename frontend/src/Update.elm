module Update exposing (update, init)

import Task
import Time

import Model exposing (Model, Msg(..))

update : Msg -> Model -> (Model, Cmd Msg)
update msg model =
    case msg of
        NewData (Ok new)  -> ({model | err = Nothing, data = new}, Cmd.none)
        NewData (Err err) -> ({model | err = Just err},            Cmd.none)
        NewNow  date      -> ({model | now = date},                Cmd.none)
        RefreshWanted     -> ( model,                              refresh )

-- COMMANDS --

-- get_data : Cmd Msg
-- get_data = Http.send NewData Tw.get_request

get_now : Cmd Msg
get_now = Task.perform NewNow Time.now

refresh : Cmd Msg
refresh = Cmd.batch [get_now]
-- refresh = Cmd.batch [get_now, get_data]

-- INIT --

init : Cmd Msg
init = refresh
