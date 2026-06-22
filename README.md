# Simulation and Control Law Development

NOTICE: This project has moved to Codeberg.org <https://codeberg.org/NorthStarUAS>

This project explores techniques to derive dynamics models and flight control
laws directly from flight test data.

## Simulation

Using flight test data we can derive an approximate flight dynamics model. It is
not perfect (no model is!) but it is useful for control law validation and
demonstration.

## Control Law Development

We can derive a set of control laws directly from flight test data.

Often, the process of developing control laws involves building a dynamics model
of the aircraft using flight test data.  Then developing an outline of the
desired control laws. Finally (using a variety of advanced techniques) the
control laws can be tuned and validated against the dynamics model. Another
approach is to just send your aircraft and tune the control law gains based on
real in-flight behavior until the system "feels about right".

However, in this project I am exploring a technique to directly derive control
laws from flight data.

## Demonstration and Validation

This will sound like circular logic (and it is) ... but I prefer the word
iterative. :-)

If I can derive a dynamics model from flight test data, and derive control laws
from flight test data, then I can demonstrate the control laws flying the
simulation model.  That would (will!) be a major objective and mile stone when I
reach that.

The real proof will be to install the derived control laws on the original
aircraft and have them work flawlessly out of the box on the first flight.

I am driving towards a real world demonstration with a small (RC scale) type
fixed wing flying model.

## Warnings to all who enter here

The approaches I explore here are not the typical path.  There are significant
advantages (potentially) but there are also significant limitations and
downsides to be aware of depending on your use case and goals.  It would be
important to have some understanding of the boundaries before proceeding with
anything here.

That said, my initial investigations (beginning in 2021) shows that all this
stuff works, and can work pretty well.  This is a DIY project and I am doing in
my spare time whenever I get a rainy Saturday, so I don't have a specific time
line.  It is whatever I can do whenever I can do it.

Feel free to ask questions if you have any!
