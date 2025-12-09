# A data-driven approach to create an approximate continuous discrete time-invariant state space model directly from test data

Assumes: we have chosen the relevent states to collect.  These states have been properly collected in actual flight.  We have a fixed invariant sample time interval. We have our data in hand and can wrangle it into new arrangements.

## Overview

The typical process of peforming frequency space analysis of a non-linear model involves carefully mining test data to build a complex non-linear model. In the domain of flight simulation this involves a complex series of equations fed by coefficients and lookup tables (stability derivatives) so the challenge is double ... first constructing the infrastructure of the model equations and coordinate systems correctly and then deriving the correct coefficients to populate the model.

Once the non-linear model is created, it can be "linearized" at a number of
points and then frequency analysis can be performed at those specific points.

This document outlines a novel approach to generating an accurate matrix
approximation to the non-linear model across the flight envelope as flown in the
test flights.  This matrix can then be manipulated into the form of a continuous state space model.  From there the transfer function can be computed and model analysis performed.

The difficult step of building the non-linear model and linearizing it at multiple points in the flight envelop is thus collapsed into a single automated step that can be derived directly from the flight data.

## Construct a global multi-input, multi-output state transition matrix

## Definitions

* $\mathbf{x}(k)$ = state vector at time $k$
* $\mathbf{u}(k)$ = input vector at time $k$
* $\mathbf{v}(k)$ = combined $\begin{bmatrix}\mathbf{x}(k)\\\mathbf{u}(k)\end{bmatrix}$

## Construct the Training Data

This is a direct least squares solution, not a black box AI deep learning system, but we can think of our input data as the data we use to train our system.  We could later "test" our system against other flights not included in the training set and evaluate the accuracy of our model.

* $n$ = number of data samples
* data = $\begin{bmatrix}\mathbf{v}(0), \mathbf{v}(1), \ldots, \mathbf{v}(n)\end{bmatrix}$
* $\mathbf{X} = \begin{bmatrix}\mathbf{v}(0), \mathbf{v}(1), \ldots, \mathbf{v}(n-1)\end{bmatrix}$ = data[:n-1]
* $\mathbf{Y} = \begin{bmatrix}\mathbf{v}(1), \mathbf{v}(2), \ldots, \mathbf{v}(n)\end{bmatrix}$ = data[1:]

Intuition:

* $\mathbf{X}$ and $\mathbf{Y}$ are constructed directly from flight test data.
* $\mathbf{X}$ can be thought of as the set of "current" states.
* $\mathbf{Y}$ can be thought of as the set of "next" states.
* $\mathbf{X}$ and $\mathbf{Y}$ are identical except the columns are shifted by one position and are trimmed so their dimensions match.
* When $\mathbf{X}$ and $\mathbf{Y}$ are postioned vertically, each column $\mathbf{v}(k)$ in $\mathbf{X}$ aligns with $\mathbf{v}(k+1)$ in $\mathbf{Y}$ where all columns in both matrices come from the same data set.

So ... let's go!

## The Big Equation!

Consider this equation constructed directly from our data. $\mathbf{X}$ and $\mathbf{Y}$ are known and complete, $\mathbf{M}$ is our unknown variable:

$\mathbf{Y} = \mathbf{M} \cdot \mathbf{X}$

> Important! If true, this equation states that there exists some hypothetical matrix $\mathbf{M}$ derived directly from our data that maps all "current" states to "all" next states.

The logical questions to ask at this point are: Is this simple equation
solvable? Does solving the equation product anything that is usable and make any
sense? Can this actually work?!?

Because of how matrix vs. vector multiplication works, if the full matrix equation is true, then a simpler vector in/out version of the equation is also true:

$\mathbf{v}(k+1) = \mathbf{M} \cdot \mathbf{v}(k)$

$\mathbf{M}$ is thus (or would be) a state transition matrix that predicts the
next state of our system from the current state and current input.

In the context of flight dynamics we know we can produce a non-linear flight dynamics model of an aircraft -- left as an exercise for the reader, hah!  We know we can linearize the model at any number of fixed state locations -- also left as an exercise for the reader, double hah!

So generically we can express our non-linear dynamics system as a function (which may actually be a complex collection of functions and algorithms):

$\mathbf{v}(k+1) = f(\mathbf{v}(k), \mathbf{u}(k))$

A flight simulator would iterate on this non-linear function endlessly, feeding in the current pilot input as it changes, and logging (or drawing the result graphically.)

It seems reasonable to assume we can replace $f()$ with a matrix approximation $\mathbf{M}$

## Solve for $\mathbf{M}$

The challenge to solving $\mathbf{Y} = \mathbf{M} \cdot \mathbf{X}$ is being able to invert the $\mathbf{X}$ matrix.  One approach to doing this is to take the singular value decomposition (SVD) of $\mathbf{X}$ and substitute that into our equation, then do the simple algebraic manipulations to isolate $\mathbf{M}$ on one side of the equation.

$\mathbf{X}$ is not square, but the python (and presumably matlab) svd functions are able to handle non-square matrices just fine.

Also, let's use the python dask module instead of numpy because dask is much more space/time efficient for large matrices

    import dask.array as da
    U, S, Vh = da.linalg.svd(X)

Back to a more mathematical representation:

* $\mathbf{Y} = \mathbf{M} \cdot \mathbf{X}$

Do the singular value decomposition on $\mathbf{X}$:

* $svd(\mathbf{X}) \rightarrow \mathbf{U} \cdot \mathbf{S} \cdot \mathbf{V}^{T}$
* note that: $\mathbf{X} = \mathbf{U} \cdot \mathbf{S} \cdot \mathbf{V}^{T}$

Substitute the SVD form into the first equation yields:
* $\mathbf{Y} = \mathbf{M} \cdot \mathbf{U} \cdot \mathbf{S} \cdot \mathbf{V}^{T}$

Peforming a bit of basic algebraic rearranging yields:

* $\mathbf{M} = \mathbf{Y} \cdot \mathbf{V} \cdot \mathbf{S}^{-1} \cdot \mathbf{U}^T$

In python/dask this can be written as:

    M = (Y @ (Vh.T * (1/S)) @ U.T).compute()

And that's it, we solved for $\mathbf{M}$ with a couple lines of python code.  And by using python/dask we were able to find a solution for very large input data sets.

## Discrete State Space Model

Much of control theory revolves around continuous state space models which have equivalent transfer functions and allow further analysis.  Our solution looks more like a discrete time invariant state space representation. So let's do a little bit of rearrangement to make this as close as we can to a continuous time invariant state space representation.  (i.e. let's find the A, B, C, D matrices and these matrices will be time-invariant.)

>note: in the following I am re-using the $n$ variable to mean something new!  It is now the number of states, not the number of data points in our data file.

* $\mathbf{x}(k)$, our state vector, has $n$ elements
* $\mathbf{u}(k)$, our input vector, has $m$ elements
* $\mathbf{M}$ has dimensions $(n+m) \times (n+m)$

By inspection and considering that we don't care or need to predict the next input, we can partition the $\mathbf{M}$ matrix as follows:

$$
\mathbf{M}_{(n+m)\times(n+m)} = \begin{bmatrix}\begin{array}{c|c}\mathbf{A}_{n \times n} & \mathbf{B}_{n \times m} \\ \hline \mathbf{O}_{m \times n} & \mathbf{O}_{m \times m}\end{array}\end{bmatrix}
$$

And expanding:

$$
\mathbf{v}(k) \rightarrow \begin{bmatrix}\mathbf{x}(k)\\\mathbf{u}(k)\end{bmatrix}
$$

We can write:

$$
\mathbf{v}(k+1) = \mathbf{M}_{(n+m)\times(n+m)} \cdot \mathbf{v}(k) = \begin{bmatrix}\begin{array}{c|c}\mathbf{A}_{n \times n} & \mathbf{B}_{n \times m} \\ \hline \mathbf{O}_{m \times n} & \mathbf{O}_{m \times m}\end{array}\end{bmatrix} \cdot \begin{bmatrix}\mathbf{x}(k)\\\mathbf{u}(k)\end{bmatrix}
$$

Collapsing out the zero sections of the $\mathbf{M}$ matrix yields:

$$
\mathbf{x}(k+1) = \begin{bmatrix}\begin{array}{c|c}\mathbf{A}_{n \times n} & \mathbf{B}_{n \times m} \end{array}\end{bmatrix} \cdot \begin{bmatrix}\mathbf{x}(k)\\\mathbf{u}(k)\end{bmatrix}
$$

The solution can then be rewritten in a more $discrete$ state space familiar form as:

$$
\mathbf{x}(k+1) = \mathbf{A} \cdot \mathbf{x}(k) + \mathbf{B} \cdot \mathbf{u}(k)
\\
\mathbf{y}(k+1) = \mathbf{C} \cdot \mathbf{x}(k) + \mathbf{D} \cdot \mathbf{u}(k)
$$

Assuming we don't care about $\mathbf{y}(k)$ for this system, we can set $\mathbf{C} = \mathbf{I}$ and $\mathbf{D} = \mathbf{O}$

## Continuous State Space Model

The continuous state space model takes the form:

$$
\mathbf{\dot{x}}(t) = \mathbf{A} \cdot \mathbf{x}(t) + \mathbf{B} \cdot \mathbf{u}(t)
\\
\mathbf{y}(t) = \mathbf{C} \cdot \mathbf{x}(t) + \mathbf{D} \cdot \mathbf{u}(t)
$$

The key differences to notice are that $k$ which is a sample in the sequence of samples is replaced with the state of the system at some arbitrary time t.  Also the result of the first equation is $\mathbf{\dot{x}}(t)$ (the rate of change of the state variable) instead of $\mathbf{x}(k)$ the next state of the system.

We can manipulate our discrete state space model to approximate a continuous state space model with a quick substitution, and in this case assuming our discrete system has state samples at 50hz. I am being a small bit sloppy with $t$ versus $k$ here:

$$
t \approx \frac{k}{50} \\
\mathbf{\dot{x}}(k) \approx \mathbf{x}(k+1) - \mathbf{x}(k) \\
\mathbf{\dot{x}}(t) \approx \mathbf{\dot{x}}(k) \cdot 50
$$
Rearranging and substituting:
$$
\mathbf{x}(k+1) = \mathbf{\dot{x}}(k) + \mathbf{x}(k)
\\
\mathbf{\dot{x}}(k) + \mathbf{x}(k) = \mathbf{A}_{discrete} \cdot \mathbf{x}(k) + \mathbf{B}_{discrete} \cdot \mathbf{u}(k)
\\
\mathbf{\dot{x}}(k) = \mathbf{A}_{discrete} \cdot \mathbf{x}(k) - \mathbf{x}(k) + \mathbf{B}_{discrete} \cdot \mathbf{u}(k)
\\
\mathbf{\dot{x}}(k) = (\mathbf{A}_{discrete} - \mathbf{I}) \cdot \mathbf{x}(k) + \mathbf{B}_{discrete} \cdot \mathbf{u}(k)
\\
\mathbf{\dot{x}}(t) = ((\mathbf{A}_{discrete} - \mathbf{I}) \cdot \mathbf{x}(k) + \mathbf{B}_{discrete} \cdot \mathbf{u}(k) ) \cdot 50
$$
By inspection (in this discussion our data sample rate was an invariant 50hz):
$$
\mathbf{A}_{continuous} = (\mathbf{A}_{discrete} - \mathbf{I}) \cdot 50
\\
\mathbf{B}_{continuous} = \mathbf{B}_{discrete} \cdot 50
$$
and we will call:
$$
\mathbf{A}_{continuous} = \mathbf{A}
\\
\mathbf{B}_{continuous} = \mathbf{B}
$$
 and further simplify the equation to continous state space form:

$$
\mathbf{\dot{x}}(t) = \mathbf{A}_{(cont)} \cdot \mathbf{x}(k) + \mathbf{B}_{(cont)} \cdot \mathbf{u}(k)
\\
\mathbf{y}(t) = \mathbf{C} \cdot \mathbf{x}(t) + \mathbf{D} \cdot \mathbf{u}(t)
\\
\mathbf{C} = \mathbf{I}, \mathbf{D} = \mathbf{O}
$$
