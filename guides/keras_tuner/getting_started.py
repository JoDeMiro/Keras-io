"""
Title: Getting started with KerasTuner
Authors: Luca Invernizzi, James Long, Francois Chollet, Tom O'Malley, Haifeng Jin
Date created: 2019/05/31
Last modified: 2021/10/27
Description: The basics of using KerasTuner to tune model hyperparameters.
"""

"""shell
pip install keras-tuner -q
"""


"""
## Introduction

KerasTuner is a general-purpose hyperparameter tuning library. It has strong
integration with Keras workflows, but it isn't limited to them: you could use
it to tune scikit-learn models, or anything else. In this tutorial, you will
see how to tune model architecture, training process, and data preprocessing
steps with KerasTuner. Let's start from a simple example.

## Tune the model architecture

The first thing we need to do is writing a function, which returns a compiled
Keras model. It takes an argument `hp` for defining the hyperparameters while
building the model.

### Define the search space

In the following code example, we define a Keras model with two `Dense` layers.
We want to tune the number of units in the first `Dense` layer. We just define
an integer hyperparameter with `hp.Int('units', min_value=32, max_value=512, step=32)`,
whose range is from 32 to 512 inclusive. When sampling from it, the minimum
step for walking through the interval is 32.
"""

from tensorflow import keras
from tensorflow.keras import layers


def build_model(hp):
    model = keras.Sequential()
    model.add(layers.Flatten())
    model.add(
        layers.Dense(
            # Define the hyperparameter.
            units=hp.Int("units", min_value=32, max_value=512, step=32),
            activation="relu",
        )
    )
    model.add(layers.Dense(10, activation="softmax"))
    model.compile(
        optimizer="adam", loss="categorical_crossentropy", metrics=["accuracy"],
    )
    return model


"""
You can quickly test if the model builds successfully.
"""

import keras_tuner

build_model(keras_tuner.HyperParameters())

"""
There are many other types of hyperparameters as well. We can define multiple
hyperparameters in the function. In the following code, we tune the whether to
use a `Dropout` layer with `hp.Boolean()`, tune which activation function to
use with `hp.Choice()`, tune the learning rate of the optimizer with
`hp.Float()`.
"""


def build_model(hp):
    model = keras.Sequential()
    model.add(layers.Flatten())
    model.add(
        layers.Dense(
            # Tune number of units.
            units=hp.Int("units", min_value=32, max_value=512, step=32),
            # Tune the activation function to use.
            activation=hp.Choice("activation", ["relu", "tanh"]),
        )
    )
    # Tune whether to use dropout.
    if hp.Boolean("dropout"):
        model.add(layers.Dropout(rate=0.25))
    model.add(layers.Dense(10, activation="softmax"))
    # Define the optimizer learning rate as a hyperparameter.
    learning_rate = hp.Float("lr", min_value=1e-4, max_value=1e-2, sampling="log")
    model.compile(
        optimizer=keras.optimizers.Adam(learning_rate=learning_rate),
        loss="categorical_crossentropy",
        metrics=["accuracy"],
    )
    return model


build_model(keras_tuner.HyperParameters())

"""
As shown below, the hyperparameters are actual values. In fact, they are just
functions returning actual values. For example, `hp.Int()` returns an `int`
value. Therefore, you can put them into variables, for loops, or if
conditions.
"""

hp = keras_tuner.HyperParameters()
print(hp.Int("units", min_value=32, max_value=512, step=32))

"""
You can also define the hyperparameters in advance and keep your Keras code in
a separate function.
"""


def call_existing_code(units, activation, dropout, lr):
    model = keras.Sequential()
    model.add(layers.Flatten())
    model.add(layers.Dense(units=units, activation=activation))
    if dropout:
        model.add(layers.Dropout(rate=0.25))
    model.add(layers.Dense(10, activation="softmax"))
    model.compile(
        optimizer=keras.optimizers.Adam(learning_rate=lr),
        loss="categorical_crossentropy",
        metrics=["accuracy"],
    )
    return model


def build_model(hp):
    units = hp.Int("units", min_value=32, max_value=512, step=32)
    activation = hp.Choice("activation", ["relu", "tanh"])
    dropout = hp.Boolean("dropout")
    lr = hp.Float("lr", min_value=1e-4, max_value=1e-2, sampling="log")
    # call existing model-building code with the hyperparameter values.
    model = call_existing_code(
        units=units, activation=activation, dropout=dropout, lr=lr
    )
    return model


build_model(keras_tuner.HyperParameters())

"""
Each of the hyperparameters is uniquely identified by its name (the first
argument). To tune the number of units in different `Dense` layers separately
as different hyperparameters, we give them different names as `f"units_{i}"`.

Notably, this is also an example of creating conditional hyperparameters.
There are many hyperparameters specifying the number of units in the `Dense`
layers. The number of such hyperparameters is decided by the number of layers,
which is also a hyperparameter. Therefore, the total number of hyperparameters
used may be different from trial to trial. Some hyperparameter is only used
when a certain condition is satisfied. For example, `units_3` is only used
when `num_layers` is larger than 3. With KerasTuner, you can easily define
such hyperparameters dynamically while creating the model.

"""


def build_model(hp):
    model = keras.Sequential()
    model.add(layers.Flatten())
    # Tune the number of layers.
    for i in range(hp.Int("num_layers", 1, 3)):
        model.add(
            layers.Dense(
                # Tune number of units separately.
                units=hp.Int(f"units_{i}", min_value=32, max_value=512, step=32),
                activation=hp.Choice("activation", ["relu", "tanh"]),
            )
        )
    if hp.Boolean("dropout"):
        model.add(layers.Dropout(rate=0.25))
    model.add(layers.Dense(10, activation="softmax"))
    learning_rate = hp.Float("lr", min_value=1e-4, max_value=1e-2, sampling="log")
    model.compile(
        optimizer=keras.optimizers.Adam(learning_rate=learning_rate),
        loss="categorical_crossentropy",
        metrics=["accuracy"],
    )
    return model


build_model(keras_tuner.HyperParameters())

"""
### Start the search

After defining the search space, we need to select a tuner class to run the
search. You may choose from `RandomSearch`, `BayesianOptimization` and
`Hyperband`, which correspond to different tuning algorithms. Here we use
`RandomSearch` as an example.

To initialize the tuner, we need to specify several arguments in the initializer.

* `hypermodel`. The model-building function, which is `build_model` in our case.
* `objective`. The name of the objective to optimize (whether to minimize or
maximize is automatically inferred for built-in metrics). We will introduce how
to use custom metrics later in this tutorial.
* `max_trials`. The total number of trials to run during the search.
* `executions_per_trial`. The number of models that should be built and fit for
each trial. Different trials have different hyperparameter values. The
executions within the same trial have the same hyperparameter values. The
purpose of having multiple executions per trial is to reduce results variance
and therefore be able to more accurately assess the performance of a model. If
you want to get results faster, you could set `executions_per_trial=1` (single
round of training for each model configuration).
* `overwrite`. Control whether to overwrite the previous results in the same
directory or resume the previous search instead. Here we set `overwrite=True`
to start a new search and ignore any previous results.
* `directory`. A path to a directory for storing the search results.
* `project_name`. The name of the sub-directory in the `directory`.

"""

tuner = keras_tuner.RandomSearch(
    hypermodel=build_model,
    objective="val_accuracy",
    max_trials=3,
    executions_per_trial=2,
    overwrite=True,
    directory="my_dir",
    project_name="helloworld",
)

"""
You can print a summary of the search space:
"""

tuner.search_space_summary()

"""
Before starting the search, let's prepare the MNIST dataset.
"""

from tensorflow import keras
import numpy as np

(x, y), (x_test, y_test) = keras.datasets.mnist.load_data()

x_train = x[:-10000]
x_val = x[-10000:]
y_train = y[:-10000]
y_val = y[-10000:]

x_train = np.expand_dims(x_train, -1).astype("float32") / 255.0
x_val = np.expand_dims(x_val, -1).astype("float32") / 255.0
x_test = np.expand_dims(x_test, -1).astype("float32") / 255.0

num_classes = 10
y_train = keras.utils.to_categorical(y_train, num_classes)
y_val = keras.utils.to_categorical(y_val, num_classes)
y_test = keras.utils.to_categorical(y_test, num_classes)

"""
Then, start the search for the best hyperparameter configuration.
All the arguments passed to `search` is passed to `model.fit()` in each
execution. Remember to pass `validation_data` to evaluate the model.
"""

tuner.search(x_train, y_train, epochs=2, validation_data=(x_val, y_val))

"""
During the `search`, the model-building function is called with different
hyperparameter values in different trial. In each trial, the tuner would
generate a new set of hyperparameter values to build the model. The model is
then fit and evaluated. The metrics are recorded. The tuner progressively
explores the space and finally finds a good set of hyperparameter values.

### Query the results

When search is over, you can retrieve the best model(s). The model is saved at
its best performing epoch evaluated on the `validation_data`.
"""

# Get the top 2 models.
models = tuner.get_best_models(num_models=2)
best_model = models[0]
# Build the model.
# Needed for `Sequential` without specified `input_shape`.
best_model.build(input_shape=(None, 28, 28))
best_model.summary()

"""
You can also print a summary of the search results.
"""

tuner.results_summary()

"""
You will find detailed logs, checkpoints, etc, in the folder
`my_dir/helloworld`, i.e. `directory/project_name`.

You can also visualize the tuning results using TensorBoard and HParams plugin.
For more information, please following
[this link](https://keras.io/guides/keras_tuner/visualize_tuning/).

### Retrain the model

If you want to train the model with the entire dataset, you may retrieve the
best hyperparameters and retrain the model by yourself.
"""

# Get the top 2 hyperparameters.
best_hps = tuner.get_best_hyperparameters(5)
# Build the model with the best hp.
model = build_model(best_hps[0])
# Fit with the entire dataset.
x_all = np.concatenate((x_train, x_val))
y_all = np.concatenate((y_train, y_val))
model.fit(x=x_all, y=y_all, epochs=1)

"""
## Tune model training

To tune the model building process, we need to subclass the `HyperModel` class,
which also makes it easy to share and reuse hypermodels.

We need to override `HyperModel.build()` and `HyperModel.fit()` to tune the
model building and training process respectively. A `HyperModel.build()`
method is the same as the model-building function, which creates a Keras model
using the hyperparameters and returns it.

In `HyperModel.fit()`, you can access the model returned by
`HyperModel.build()`,`hp` and all the arguments passed to `search()`. You need
to train the model and return the training history.

In the following code, we will tune the `shuffle` argument in `model.fit()`.

It is generally not needed to tune the number of epochs because a built-in
callback is passed to `model.fit()` to save the model at its best epoch
evaluated by the `validation_data`.

> **Note**: The `**kwargs` should always be passed to `model.fit()` because it
contains the callbacks for model saving and tensorboard plugins.
"""


class MyHyperModel(keras_tuner.HyperModel):
    def build(self, hp):
        model = keras.Sequential()
        model.add(layers.Flatten())
        model.add(
            layers.Dense(
                units=hp.Int("units", min_value=32, max_value=512, step=32),
                activation="relu",
            )
        )
        model.add(layers.Dense(10, activation="softmax"))
        model.compile(
            optimizer="adam", loss="categorical_crossentropy", metrics=["accuracy"],
        )
        return model

    def fit(self, hp, model, *args, **kwargs):
        return model.fit(
            *args,
            # Tune whether to shuffle the data in each epoch.
            shuffle=hp.Boolean("shuffle"),
            **kwargs,
        )


"""
Again, we can do a quick check to see if the code works correctly.
"""

hp = keras_tuner.HyperParameters()
hypermodel = MyHyperModel()
model = hypermodel.build(hp)
hypermodel.fit(hp, model, np.random.rand(100, 28, 28), np.random.rand(100, 10))

"""
## Tune data preprocessing

To tune data preprocessing, we just add an additional step in
`HyperModel.fit()`, where we can access the dataset from the arguments. In the
following code, we tune whether to normalize the data before training the
model. This time we explicitly put `x` and `y` in the function signature
because we need to use them.

"""


class MyHyperModel(keras_tuner.HyperModel):
    def build(self, hp):
        model = keras.Sequential()
        model.add(layers.Flatten())
        model.add(
            layers.Dense(
                units=hp.Int("units", min_value=32, max_value=512, step=32),
                activation="relu",
            )
        )
        model.add(layers.Dense(10, activation="softmax"))
        model.compile(
            optimizer="adam", loss="categorical_crossentropy", metrics=["accuracy"],
        )
        return model

    def fit(self, hp, model, x, y, **kwargs):
        if hp.Boolean("normalize"):
            x = layers.Normalization()(x)
        return model.fit(
            x,
            y,
            # Tune whether to shuffle the data in each epoch.
            shuffle=hp.Boolean("shuffle"),
            **kwargs,
        )


hp = keras_tuner.HyperParameters()
hypermodel = MyHyperModel()
model = hypermodel.build(hp)
hypermodel.fit(hp, model, np.random.rand(100, 28, 28), np.random.rand(100, 10))

"""
If a hyperparameter is used both in `build()` and `fit()`, you can define it in
`build()` and use `hp.get(hp_name)` to retrieve it in `fit()`. We use the
image size as an example. It is both used as the input shape in `build()`, and
used by data prerprocessing step to crop the images in `fit()`.
"""


class MyHyperModel(keras_tuner.HyperModel):
    def build(self, hp):
        image_size = hp.Int("image_size", 10, 28)
        inputs = keras.Input(shape=(image_size, image_size))
        outputs = layers.Flatten()(inputs)
        outputs = layers.Dense(
            units=hp.Int("units", min_value=32, max_value=512, step=32),
            activation="relu",
        )(outputs)
        outputs = layers.Dense(10, activation="softmax")(outputs)
        model = keras.Model(inputs, outputs)
        model.compile(
            optimizer="adam", loss="categorical_crossentropy", metrics=["accuracy"],
        )
        return model

    def fit(self, hp, model, x, y, validation_data=None, **kwargs):
        if hp.Boolean("normalize"):
            x = layers.Normalization()(x)
        image_size = hp.get("image_size")
        cropped_x = x[:, :image_size, :image_size, :]
        if validation_data:
            x_val, y_val = validation_data
            cropped_x_val = x_val[:, :image_size, :image_size, :]
            validation_data = (cropped_x_val, y_val)
        return model.fit(
            cropped_x,
            y,
            # Tune whether to shuffle the data in each epoch.
            shuffle=hp.Boolean("shuffle"),
            validation_data=validation_data,
            **kwargs,
        )


tuner = keras_tuner.RandomSearch(
    MyHyperModel(),
    objective="val_accuracy",
    max_trials=3,
    overwrite=True,
    directory="my_dir",
    project_name="tune_hypermodel",
)

tuner.search(x_train, y_train, epochs=2, validation_data=(x_val, y_val))

"""
### Retrain the model

Using `HyperModel` also allows you to retrain the best model by yourself.
"""

hypermodel = MyHyperModel()
best_hp = tuner.get_best_hyperparameters()[0]
model = hypermodel.build(best_hp)
hypermodel.fit(best_hp, model, x_all, y_all, epochs=1)

"""
## Specify the tuning objective

In all previous examples, we all just used validation accuracy
(`"val_accuracy"`) as the tuning objective to select the best model. Actually,
you can use any metric as the objective. The most commonly used metric is
`"val_loss"`, which is the validation loss.

### Built-in metric as the objective

There are many other built-in metrics in Keras you can use as the objective.
Here is [a list of the built-in metrics](https://keras.io/api/metrics/).

To use a built-in metric as the objective, you need to follow these steps:
* Compile the model with the the built-in metric. For example, you want to use
`MeanAbsoluteError()`. You need to compile the model with
`metrics=[MeanAbsoluteError()]`. You may also use its name string instead:
`metrics=["mean_absolute_error"]`. The name string of the metric is always
the snake case of the class name.

* Identify the objective name string. The name string of the objective is
always in the format of `f"val_{metric_name_string}"`. For example, the
objective name string of mean squared error evaluated on the validation data
should be `"val_mean_absolute_error"`.

* Wrap it into `keras_tuner.Objective`. We usually need to wrap the objective
into a `keras_tuner.Objective` object to specify the direction to optimize the
objective. For example, we want to minimize the mean squared error, we can use
`keras_tuner.Objective("val_mean_absolute_error", "min")`. The direction should
be either `"min"` or `"max"`.

* Pass the wrapped objective to the tuner.

You can see the following barebone code example.
"""


def build_regressor(hp):
    model = keras.Sequential(
        [
            layers.Dense(units=hp.Int("units", 32, 128, 32), activation="relu"),
            layers.Dense(units=1),
        ]
    )
    model.compile(
        optimizer="adam",
        loss="mean_squared_error",
        # Objective is one of the metrics.
        metrics=[keras.metrics.MeanAbsoluteError()],
    )
    return model


tuner = keras_tuner.RandomSearch(
    hypermodel=build_regressor,
    # The objective name and direction.
    # Name is the f"val_{snake_case_metric_class_name}".
    objective=keras_tuner.Objective("val_mean_absolute_error", direction="min"),
    max_trials=3,
    overwrite=True,
    directory="my_dir",
    project_name="built_in_metrics",
)

tuner.search(
    x=np.random.rand(100, 10),
    y=np.random.rand(100, 1),
    validation_data=(np.random.rand(20, 10), np.random.rand(20, 1)),
)

tuner.results_summary()

"""
### Custom metric as the objective

You may implement your own metric and use it as the hyperparameter search
objective. Here, we use mean squared error (MSE) as an example. First, we
implement the MSE metric by subclassing `keras.metrics.Metric`. Remember to
give a name to your metric using the `name` argument of `super().__init__()`,
which will be used later. Note: MSE is actully a build-in metric, which can be
imported with `keras.metrics.MeanSquaredError`. This is just an example to show
how to use a custom metric as the hyperparameter search objective.

For more information about implementing custom metrics, please see [this
tutorial](https://keras.io/api/metrics/#creating-custom-metrics). If you would
like a metric with a different function signature than `update_state(y_true,
y_pred, sample_weight)`, you can override the `train_step()` method of your
model following [this
tutorial](https://keras.io/guides/customizing_what_happens_in_fit/#going-lowerlevel).

"""

import tensorflow as tf


class CustomMetric(keras.metrics.Metric):
    def __init__(self, **kwargs):
        # Specify the name of the metric as "custom_metric".
        super().__init__(name="custom_metric", **kwargs)
        self.sum = self.add_weight(name="sum", initializer="zeros")
        self.count = self.add_weight(name="count", dtype=tf.int32, initializer="zeros")

    def update_state(self, y_true, y_pred, sample_weight=None):
        values = tf.math.squared_difference(y_pred, y_true)
        count = tf.shape(y_true)[0]
        if sample_weight is not None:
            sample_weight = tf.cast(sample_weight, self.dtype)
            values *= sample_weight
            count *= sample_weight
        self.sum.assign_add(tf.reduce_sum(values))
        self.count.assign_add(count)

    def result(self):
        return self.sum / tf.cast(self.count, tf.float32)

    def reset_states(self):
        self.sum.assign(0)
        self.count.assign(0)


"""
Run the search with the custom objective.
"""


def build_regressor(hp):
    model = keras.Sequential(
        [
            layers.Dense(units=hp.Int("units", 32, 128, 32), activation="relu"),
            layers.Dense(units=1),
        ]
    )
    model.compile(
        optimizer="adam",
        loss="mean_squared_error",
        # Put custom metric into the metrics.
        metrics=[CustomMetric()],
    )
    return model


tuner = keras_tuner.RandomSearch(
    hypermodel=build_regressor,
    # Specify the name and direction of the objective.
    objective=keras_tuner.Objective("val_custom_metric", direction="min"),
    max_trials=3,
    overwrite=True,
    directory="my_dir",
    project_name="custom_metrics",
)

tuner.search(
    x=np.random.rand(100, 10),
    y=np.random.rand(100, 1),
    validation_data=(np.random.rand(20, 10), np.random.rand(20, 1)),
)

tuner.results_summary()

"""
If your custom objective is hard to put into a custom metric, you can also
evaluate the model by yourself in `HyperModel.fit()` and return the objective
value. The objective value would be minimized by default. In this case, you
don't need to specify the `objective` when initializing the tuner. However, in
this case, the metric value will not be tracked in the Keras logs by only
KerasTuner logs. Therefore, these values would not be displayed by any
TensorBoard view using the Keras metrics.
"""


class HyperRegressor(keras_tuner.HyperModel):
    def build(self, hp):
        model = keras.Sequential(
            [
                layers.Dense(units=hp.Int("units", 32, 128, 32), activation="relu"),
                layers.Dense(units=1),
            ]
        )
        model.compile(
            optimizer="adam", loss="mean_squared_error",
        )
        return model

    def fit(self, hp, model, x, y, validation_data, **kwargs):
        model.fit(x, y, **kwargs)
        x_val, y_val = validation_data
        y_pred = model.predict(x_val)
        # Return a single float to minimize.
        return np.mean(np.abs(y_pred - y_val))


tuner = keras_tuner.RandomSearch(
    hypermodel=HyperRegressor(),
    # No objective to specify.
    # Objective is the return value of `HyperModel.fit()`.
    max_trials=3,
    overwrite=True,
    directory="my_dir",
    project_name="custom_eval",
)
tuner.search(
    x=np.random.rand(100, 10),
    y=np.random.rand(100, 1),
    validation_data=(np.random.rand(20, 10), np.random.rand(20, 1)),
)

tuner.results_summary()

"""
If you have multiple metrics to track in KerasTuner, but only use one of them
as the objective, you can return a dictionary, whose keys are the metric names
and the values are the metrics values, for example, return `{"metric_a": 1.0,
"metric_b", 2.0}`. Use one of the keys as the objective name, for example,
`keras_tuner.Objective("metric_a", "min")`.
"""


class HyperRegressor(keras_tuner.HyperModel):
    def build(self, hp):
        model = keras.Sequential(
            [
                layers.Dense(units=hp.Int("units", 32, 128, 32), activation="relu"),
                layers.Dense(units=1),
            ]
        )
        model.compile(
            optimizer="adam", loss="mean_squared_error",
        )
        return model

    def fit(self, hp, model, x, y, validation_data, **kwargs):
        model.fit(x, y, **kwargs)
        x_val, y_val = validation_data
        y_pred = model.predict(x_val)
        # Return a dictionary of metrics for KerasTuner to track.
        return {
            "metric_a": -np.mean(np.abs(y_pred - y_val)),
            "metric_b": np.mean(np.square(y_pred - y_val)),
        }


tuner = keras_tuner.RandomSearch(
    hypermodel=HyperRegressor(),
    # Objective is one of the keys.
    # Maximize the negative MAE, equivalent to minimize MAE.
    objective=keras_tuner.Objective("metric_a", "max"),
    max_trials=3,
    overwrite=True,
    directory="my_dir",
    project_name="custom_eval_dict",
)
tuner.search(
    x=np.random.rand(100, 10),
    y=np.random.rand(100, 1),
    validation_data=(np.random.rand(20, 10), np.random.rand(20, 1)),
)

tuner.results_summary()

"""
## Tune end-to-end workflows

In some cases, it is hard to align your code into build and fit functions. You
can also keep your end-to-end workflow in one place by overriding
`Tuner.run_trial()`, which gives you full control of a trial. You can see it
as a black-box optimizer for anything.

### Tune any function

For example, you can find a value of `x`, which minimizes `f(x)=x*x+1`. In the
following code, we just define `x` as a hyperparameter, and return `f(x)` as
the objective value. The `hypermodel` and `objective` argument for initializing
the tuner can be omitted.
"""


class MyTuner(keras_tuner.RandomSearch):
    def run_trial(self, trial, *args, **kwargs):
        # Get the hp from trial.
        hp = trial.hyperparameters
        # Define "x" as a hyperparameter.
        x = hp.Float("x", min_value=-1.0, max_value=1.0)
        # Return the objective value to minimize.
        return x * x + 1


tuner = MyTuner(
    # No hypermodel or objective specified.
    max_trials=20,
    overwrite=True,
    directory="my_dir",
    project_name="tune_anything",
)

# No need to pass anything to search()
# unless you use them in run_trial().
tuner.search()
print(tuner.get_best_hyperparameters()[0].get("x"))

"""
### Keep Keras code separate

You can keep all your Keras code unchanged and use KerasTuner to tune it. It
is useful if you cannot modify the Keras code for some reason.

It also gives you more flexibility. You don't have to separate the model
building and training code apart. However, this workflow would not help you
save the model or connect with the TensorBoard plugins.

To save the model, you can use `trial.trial_id`, which is a string to uniquely
identify a trial, to construct different paths to save the models from
different trials.
"""

import os


def keras_code(units, optimizer, saving_path):
    # Build model
    model = keras.Sequential(
        [layers.Dense(units=units, activation="relu"), layers.Dense(units=1),]
    )
    model.compile(
        optimizer=optimizer, loss="mean_squared_error",
    )

    # Prepare data
    x_train = np.random.rand(100, 10)
    y_train = np.random.rand(100, 1)
    x_val = np.random.rand(20, 10)
    y_val = np.random.rand(20, 1)

    # Train & eval model
    model.fit(x_train, y_train)

    # Save model
    model.save(saving_path)

    # Return a single float as the objective value.
    # You may also return a dictionary
    # of {metric_name: metric_value}.
    y_pred = model.predict(x_val)
    return np.mean(np.abs(y_pred - y_val))


class MyTuner(keras_tuner.RandomSearch):
    def run_trial(self, trial, **kwargs):
        hp = trial.hyperparameters
        return keras_code(
            units=hp.Int("units", 32, 128, 32),
            optimizer=hp.Choice("optimizer", ["adam", "adadelta"]),
            saving_path=os.path.join("/tmp", trial.trial_id),
        )


tuner = MyTuner(
    max_trials=3, overwrite=True, directory="my_dir", project_name="keep_code_separate",
)
tuner.search()
# Retraining the model
best_hp = tuner.get_best_hyperparameters()[0]
keras_code(**best_hp.values, saving_path="/tmp/best_model")

"""
## KerasTuner includes pre-made tunable applications: HyperResNet and HyperXception

These are ready-to-use hypermodels for computer vision.

They come pre-compiled with `loss="categorical_crossentropy"` and
`metrics=["accuracy"]`.

"""

from keras_tuner.applications import HyperResNet

hypermodel = HyperResNet(input_shape=(28, 28, 1), classes=10)

tuner = keras_tuner.RandomSearch(
    hypermodel,
    objective="val_accuracy",
    max_trials=2,
    overwrite=True,
    directory="my_dir",
    project_name="built_in_hypermodel",
)

tuner.search(
    x_train[:100], y_train[:100], epochs=1, validation_data=(x_val[:100], y_val[:100])
)
