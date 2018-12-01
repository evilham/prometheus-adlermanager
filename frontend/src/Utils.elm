module Utils exposing (..)

import Time       exposing (Month(..), utc)
import Time.Extra as Time

time_0 : Time.Posix
time_0 = Time.Parts 1970 Jan 1 0 0 0 0 |> Time.partsToPosix utc

time_inf : Time.Posix -- TODO update by 2038 ;-)
time_inf = Time.Parts 2038 Jan 1 0 0 0 0 |> Time.partsToPosix utc

just_time : Maybe Time.Posix -> Time.Posix
just_time = Maybe.withDefault time_0
