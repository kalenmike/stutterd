#!/usr/bin/env bash

STATUS=$(cat /tmp/stutterd_status)

if [ "$STATUS" == "OFF" ]; then
    echo %{F#f38ba8}%{F-}
else
    echo %{F#a6e3a1}$STATUS${F-}
fi
