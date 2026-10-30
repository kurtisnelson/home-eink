# Weather source evaluation

The sign fetches weather on the ESP32 itself. The source has to fit in the
ESP32-S3's RAM, survive HTTPS, and still fill every field the panel draws:
current temperature, humidity, wind, condition, high/low for three days, and
sunrise/sunset.

This note records the comparison that led to NWS as the primary source and
Open-Meteo as the fallback. The sample values are from one evaluation moment
in San Francisco; they are illustrative, not a statistical accuracy study.

## Candidates

| Source | Requests | Measured payloads | Coverage |
| --- | ---: | --- | --- |
| Open-Meteo | 1 | 1,023 B | current + daily + sun |
| NWS | 3 | points 3,935 B; forecast 13,317 B; observation 4,053-4,337 B | current + forecast + sun |
| Met.no | 1 | 39,556 B (89 hourly points) | current + hourly; no sun or daily high/low |

NWS station discovery was not used: `/stations?limit=...` is 74,446 B. The
device uses a configured station instead, which keeps the request small and
avoids a fourth round trip.

### Sample comparison

| Field | Open-Meteo | NWS | Met.no |
| --- | --- | --- | --- |
| Current temp | 62.3 F | 64.4 F (KSFO) | 63.9 F (17.8 C) |
| Humidity | 66% | 52% (KSFO) | 52.5% |
| Wind | 6.5 mph | missing at KSFO/SFOC1 | 6.3 mph (2.8 m/s) |
| Fri high/low | 64.5 / 52.7 F | 65 / 54 F | not provided |
| Sat high/low | 62.4 / 52.4 F | 63 / 53 F | not provided |
| Sun | yes | yes | no |

The forecast numbers agree closely. The current conditions differ mostly
because the NWS observation is from the airport and can be older than
Open-Meteo's model output. NWS also returned a null wind value at both tested
stations, which is why the firmware falls back to the forecast wind when the
latest observation has none.

## Why NWS primary

- It is the official US forecast and includes the sunrise/sunset data the
  panel already displays, without an extra request.
- Its forecast payload is comfortably below the device's buffer budget; the
  firmware uses a 32 KB buffer, an 8 KB buffer for points and observations,
  and a 4 KB buffer for the Open-Meteo fallback.
- Three small requests are acceptable on the always-on build and on the
  sleep build's 75-second awake window.

## Why Open-Meteo stays

- One request and the smallest payload make it the safest fallback.
- It covers non-US locations, where `api.weather.gov` does not apply.
- If any NWS step fails (network, non-200, parse, missing observation fields),
  the same fetch run continues with Open-Meteo instead of leaving the panel
  blank.

## Why Met.no is not used

- The single payload is roughly 39 KB and contains 89 hourly entries, most of
  which the sign does not need.
- It has no sunrise/sunset fields and no direct daily high/low, so those would
  still require another source or additional derivation.

## Implementation notes

- NWS requires a descriptive `User-Agent`; the value is the
  `${nws_user_agent}` substitution in each device file.
- `${nws_station}` selects the observation station (default `KSFO`); change it
  together with the sign's location.
- NWS is considered successful only when the forecast yields three future
  daytime periods and the observation has temperature and humidity. Otherwise
  Open-Meteo runs in the same cycle. A missing sunrise/sunset in the points
  response does not by itself discard valid NWS weather.
- The sleep build's 75-second minimum awake window is only a floor: it also
  refuses to sleep while the fetch chain is running or until 35 seconds after
  the panel refresh starts, so a slow NWS fallback cannot be cut off.
- `verify_ssl` remains `false`, matching the previous Open-Meteo setup. All
  candidates are HTTPS-only. Enabling the ESP-IDF certificate bundle is a
  separate memory/configuration trade-off and was not changed here.

## Known limitations

- NWS observations are point measurements, usually at an airport, and can lag
  the model-based current conditions. The forecast is still the better match
  for the sign's daily high/low.
- Observation wind is sometimes null; the firmware uses the first forecast
  period's wind as a fallback and draws `--` if neither source has a value.
- Runtime availability can only be confirmed by deploying the sign; local
  validation covers YAML, C++ compilation, and the request/parse paths.
