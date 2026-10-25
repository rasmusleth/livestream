# Livestream

Working name for a tool to make sports livestreams more polished, starting with futsal scoreboards.

## Initial goal

Turn camera footage of a physical scoreboard into digital scores and game time, then display those values in a clean OBS overlay.

The current streaming setup uses one camera for the match and a second camera pointed at the scoreboard. OBS places that scoreboard footage over the match video. This project should retain the scoreboard camera as an input while replacing its visible footage with a digital graphic.

The streaming computer runs macOS. An existing full-game scoreboard recording is available for development and validation; a shorter excerpt can be used for initial experiments.

## Proposed first version

1. Select the scoreboard video input.
2. Identify the regions containing each team's score and the game clock.
3. Read those values from the video and check them across successive frames.
4. Show the current readings and their status in an operator view.
5. Publish a transparent overlay that OBS can display as a browser source.
6. Allow the operator to correct values manually and resume automatic reading.

Start with one known scoreboard and camera setup. Support for other layouts can follow once the first setup works reliably.

## Reliability requirements to explore

- The clock must follow the physical scoreboard, including pauses and corrections.
- Uncertain or missing readings must not silently become zeroes or guessed values.
- Brief interruptions should preserve the last confirmed values, with an obvious stale-input indication for the operator.
- Recovery after a longer interruption, score resets, and clock corrections need explicit handling.
- The operator needs a way to override an incorrect reading during a match.
- Reading accuracy and delay should be measured against representative footage before relying on the tool live. Acceptable thresholds are still to be agreed.

## First development milestone

Use a short recording from the actual scoreboard camera to prove that both scores and the game clock can be extracted consistently. Include clock movement, a stopped clock, and score changes where available.

Inspect the footage before choosing a recognition approach or application stack. Save timestamped readings alongside the source recording so errors and delay can be checked. Once extraction is credible, connect it to the OBS overlay and then a live input.

## Open questions

- What does the physical scoreboard look like in the camera feed?
- How is the scoreboard camera connected to the streaming computer, and how does OBS receive it?
- What clock formats, periods, and reset behavior need to be supported?
- What delay is acceptable between the physical scoreboard and the digital overlay?
- Does this need to work at one venue initially or across several different scoreboards?

## Possible later scope

Team names and branding, periods, fouls, timeouts, player information, sponsor graphics, and broader match production controls could be added later. These are possibilities rather than requirements for the first version.

The product name and broader scope can stay open while the scoreboard workflow is proven.
