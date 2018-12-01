module Subscriptions exposing (subscriptions)

import Time

import Model exposing (Model, Msg(..))

subscriptions : Model -> Sub Msg
subscriptions model = Sub.batch
    [ Time.every (30*1000) (always RefreshWanted)
    ]
