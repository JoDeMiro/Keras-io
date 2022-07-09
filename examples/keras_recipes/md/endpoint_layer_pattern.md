# Endpoint layer pattern

**Author:** [fchollet](https://twitter.com/fchollet)<br>
**Date created:** 2019/05/10<br>
**Last modified:** 2019/05/10<br>
**Description:** Demonstration of the "endpoint layer" pattern (layer that handles loss management).


<img class="k-inline-icon" src="https://colab.research.google.com/img/colab_favicon.ico"/> [**View in Colab**](https://colab.research.google.com/github/keras-team/keras-io/blob/master/examples/keras_recipes/ipynb/endpoint_layer_pattern.ipynb)  <span class="k-dot">•</span><img class="k-inline-icon" src="https://github.com/favicon.ico"/> [**GitHub source**](https://github.com/keras-team/keras-io/blob/master/examples/keras_recipes/endpoint_layer_pattern.py)



---
## Setup



```python
import tensorflow as tf
from tensorflow import keras
import numpy as np

```

---
## Usage of endpoint layers in the Functional API

An "endpoint layer" has access to the model's targets, and creates arbitrary losses and
metrics using `add_loss` and `add_metric`. This enables you to define losses and
 metrics that don't match the usual signature `fn(y_true, y_pred, sample_weight=None)`.

Note that you could have separate metrics for training and eval with this pattern.



```python

class LogisticEndpoint(keras.layers.Layer):
    def __init__(self, name=None):
        super(LogisticEndpoint, self).__init__(name=name)
        self.loss_fn = keras.losses.BinaryCrossentropy(from_logits=True)
        self.accuracy_fn = keras.metrics.BinaryAccuracy(name="accuracy")

    def call(self, logits, targets=None, sample_weight=None):
        if targets is not None:
            # Compute the training-time loss value and add it
            # to the layer using `self.add_loss()`.
            loss = self.loss_fn(targets, logits, sample_weight)
            self.add_loss(loss)

            # Log the accuracy as a metric (we could log arbitrary metrics,
            # including different metrics for training and inference.
            self.add_metric(self.accuracy_fn(targets, logits, sample_weight))

        # Return the inference-time prediction tensor (for `.predict()`).
        return tf.nn.softmax(logits)


inputs = keras.Input((764,), name="inputs")
logits = keras.layers.Dense(1)(inputs)
targets = keras.Input((1,), name="targets")
sample_weight = keras.Input((1,), name="sample_weight")
preds = LogisticEndpoint()(logits, targets, sample_weight)
model = keras.Model([inputs, targets, sample_weight], preds)

data = {
    "inputs": np.random.random((1000, 764)),
    "targets": np.random.random((1000, 1)),
    "sample_weight": np.random.random((1000, 1)),
}

model.compile(keras.optimizers.Adam(1e-3))
model.fit(data, epochs=2)

```

<div class="k-default-codeblock">
```
Epoch 1/2
32/32 [==============================] - 0s 898us/step - loss: 0.3674 - accuracy: 0.0000e+00
Epoch 2/2
32/32 [==============================] - 0s 847us/step - loss: 0.3563 - accuracy: 0.0000e+00

<tensorflow.python.keras.callbacks.History at 0x14b31d090>

```
</div>
---
## Exporting an inference-only model

Simply don't include `targets` in the model. The weights stay the same.



```python
inputs = keras.Input((764,), name="inputs")
logits = keras.layers.Dense(1)(inputs)
preds = LogisticEndpoint()(logits, targets=None, sample_weight=None)
inference_model = keras.Model(inputs, preds)

inference_model.set_weights(model.get_weights())

preds = inference_model.predict(np.random.random((1000, 764)))

```

---
## Usage of loss endpoint layers in subclassed models



```python

class LogReg(keras.Model):
    def __init__(self):
        super(LogReg, self).__init__()
        self.dense = keras.layers.Dense(1)
        self.logistic_endpoint = LogisticEndpoint()

    def call(self, inputs):
        # Note that all inputs should be in the first argument
        # since we want to be able to call `model.fit(inputs)`.
        logits = self.dense(inputs["inputs"])
        preds = self.logistic_endpoint(
            logits=logits,
            targets=inputs["targets"],
            sample_weight=inputs["sample_weight"],
        )
        return preds


model = LogReg()
data = {
    "inputs": np.random.random((1000, 764)),
    "targets": np.random.random((1000, 1)),
    "sample_weight": np.random.random((1000, 1)),
}

model.compile(keras.optimizers.Adam(1e-3))
model.fit(data, epochs=2)

```

<div class="k-default-codeblock">
```
Epoch 1/2
32/32 [==============================] - 0s 833us/step - loss: 0.3499 - accuracy: 0.0000e+00
Epoch 2/2
32/32 [==============================] - 0s 643us/step - loss: 0.3443 - accuracy: 0.0000e+00

<tensorflow.python.keras.callbacks.History at 0x14afb6850>

```
</div>