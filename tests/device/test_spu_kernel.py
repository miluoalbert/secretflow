from typing import Tuple

import jax.numpy as jnp
import numpy as np

import secretflow as sf
from secretflow.device.device.spu import SPUCompilerNumReturnsPolicy


def _test_single_return(devices):
    def add(x, y):
        return jnp.add(x, y)

    x, y = devices.alice(np.random.rand)(3, 4), devices.alice(np.random.rand)(3, 4)
    x_, y_ = x.to(devices.spu), y.to(devices.spu)
    z_ = devices.spu(
        add,
        num_returns_policy=sf.device.SPUCompilerNumReturnsPolicy.FROM_USER,
        user_specified_num_returns=1,
    )(x_, y_)

    np.testing.assert_almost_equal(
        (sf.reveal(x) + sf.reveal(y)), sf.reveal(z_), decimal=6
    )

    z_1 = devices.spu(
        add,
        num_returns_policy=sf.device.SPUCompilerNumReturnsPolicy.FROM_COMPILER,
    )(x_, y_)

    np.testing.assert_almost_equal(sf.reveal(z_), sf.reveal(z_1), decimal=6)

    np.testing.assert_almost_equal(
        (sf.reveal(x) + sf.reveal(y)), sf.reveal(z_1), decimal=6
    )

    z_2 = devices.spu(add)(x_, y_)

    np.testing.assert_almost_equal(
        (sf.reveal(x) + sf.reveal(y)), sf.reveal(z_2), decimal=6
    )


def test_single_return_prod(sf_production_setup_devices):
    _test_single_return(sf_production_setup_devices)


def test_single_return_sim(sf_simulation_setup_devices):
    _test_single_return(sf_simulation_setup_devices)


def _test_multiple_return(devices):
    def foo(x, y) -> Tuple[int, int]:
        return x, y

    x, y = devices.alice(np.random.rand)(3, 4), devices.alice(np.random.rand)(3, 4)
    x_, y_ = x.to(devices.spu), y.to(devices.spu)

    z_ = devices.spu(foo)(x_, y_)

    np.testing.assert_almost_equal(
        (sf.reveal(x), sf.reveal(y)), sf.reveal(z_), decimal=6
    )

    x_hat, y_hat = devices.spu(
        foo, num_returns_policy=SPUCompilerNumReturnsPolicy.FROM_COMPILER
    )(x_, y_)
    np.testing.assert_almost_equal(
        (sf.reveal(x), sf.reveal(y)),
        (sf.reveal(x_hat), sf.reveal(y_hat)),
        decimal=6,
    )

    x_hat_2, y_hat_2 = devices.spu(
        foo,
        num_returns_policy=SPUCompilerNumReturnsPolicy.FROM_USER,
        user_specified_num_returns=2,
    )(x_, y_)
    np.testing.assert_almost_equal(
        (sf.reveal(x), sf.reveal(y)),
        (sf.reveal(x_hat_2), sf.reveal(y_hat_2)),
        decimal=6,
    )


def test_multiple_return_prod(sf_production_setup_devices):
    _test_multiple_return(sf_production_setup_devices)


def test_multiple_return_sim(sf_simulation_setup_devices):
    _test_multiple_return(sf_simulation_setup_devices)


def _test_selu(devices):
    def selu(x, alpha=1.67, lmbda=1.05):
        return lmbda * jnp.where(x > 0, x, alpha * jnp.exp(x) - alpha)

    # PYU
    x = devices.alice(np.random.rand)(3, 4)
    y = devices.alice(selu)(x, 1.34)

    # SPU
    x_ = x.to(devices.spu)
    y_ = devices.spu(selu)(x_, 1.34).to(devices.bob)

    np.testing.assert_almost_equal(sf.reveal(y), sf.reveal(y_), decimal=6)


def test_selu_prod(sf_production_setup_devices):
    _test_selu(sf_production_setup_devices)


def test_selu_sim(sf_simulation_setup_devices):
    _test_selu(sf_simulation_setup_devices)


def _test_mean(devices):
    def get_weights():
        import tensorflow as tf

        model = tf.keras.Sequential(
            [
                tf.keras.layers.Dense(
                    10, activation=tf.nn.relu, input_shape=(4,)
                ),  # input shape required
                tf.keras.layers.Dense(10, activation=tf.nn.relu),
                tf.keras.layers.Dense(3),
            ]
        )

        model.compile(
            optimizer='adam',
            loss=tf.keras.losses.SparseCategoricalCrossentropy(from_logits=True),
            metrics=['accuracy'],
        )

        return model.get_weights()

    def average(*values, weights=None):
        return [
            jnp.average(
                jnp.array(values_zip),
                axis=0,
                weights=jnp.array(weights) if weights else None,
            )
            for values_zip in zip(*values)
        ]

    # PYU
    w1, w2 = devices.alice(get_weights)(), devices.alice(get_weights)()
    w = devices.alice(average)(w1, w2.to(devices.alice), weights=[1, 2])

    # SPU
    w1_, w2_ = w1.to(devices.spu), w2.to(devices.spu)
    w_ = devices.spu(average)(w1_, w2_, weights=[1, 2])

    for expected, actual in zip(sf.reveal(w), sf.reveal(w_)):
        np.testing.assert_almost_equal(expected, actual, decimal=5)


def test_mean_prod(sf_production_setup_devices):
    _test_mean(sf_production_setup_devices)


def test_mean_sim(sf_simulation_setup_devices):
    _test_mean(sf_simulation_setup_devices)


def _test_min(devices):
    def min(*values):
        return jnp.min(jnp.stack(values), axis=0)

    # PYU
    m1, m2, m3 = (
        devices.alice(np.random.rand)(3, 4),
        devices.bob(np.random.rand)(3, 4),
        devices.carol(np.random.rand)(3, 4),
    )
    m = devices.alice(min)(m1, m2.to(devices.alice), m3.to(devices.alice))

    # SPU
    m1_, m2_, m3_ = m1.to(devices.spu), m2.to(devices.spu), m3.to(devices.spu)
    m_ = devices.spu(min)(m1_, m2_, m3_).to(devices.bob)

    np.testing.assert_almost_equal(sf.reveal(m), sf.reveal(m_), decimal=6)


def test_min_prod(sf_production_setup_devices):
    _test_min(sf_production_setup_devices)


def test_min_sim(sf_simulation_setup_devices):
    _test_min(sf_simulation_setup_devices)


def _test_max(devices):
    def max(*values):
        return jnp.min(jnp.stack(values), axis=0)

    # PYU
    m1, m2, m3 = (
        devices.alice(np.random.rand)(3, 4),
        devices.bob(np.random.rand)(3, 4),
        devices.carol(np.random.rand)(3, 4),
    )
    m = devices.alice(max)(m1, m2.to(devices.alice), m3.to(devices.alice))

    # SPU
    m1_, m2_, m3_ = m1.to(devices.spu), m2.to(devices.spu), m3.to(devices.spu)
    m_ = devices.spu(max)(m1_, m2_, m3_).to(devices.bob)

    np.testing.assert_almost_equal(sf.reveal(m), sf.reveal(m_), decimal=6)


def test_max_prod(sf_production_setup_devices):
    _test_max(sf_production_setup_devices)


def test_max_sim(sf_simulation_setup_devices):
    _test_max(sf_simulation_setup_devices)


def _test_static_argument(devices):
    def func(x, axis):
        return jnp.split(x, 2, axis)

    x = devices.alice(lambda: np.arange(10))()
    x_ = x.to(devices.spu)

    y = devices.alice(func)(x, 0)
    y_ = devices.spu(func, static_argnames='axis')(x_, axis=0)
    np.testing.assert_almost_equal(sf.reveal(y), sf.reveal(y_), decimal=6)

    def init_w(base: float, num_feat: int) -> np.ndarray:
        # last one is bias
        return jnp.full((num_feat + 1, 1), base, dtype=jnp.float32)

    spu_w = devices.spu(init_w, static_argnames=('base', 'num_feat'))(
        base=0, num_feat=30
    )
    print(sf.reveal(spu_w))


def test_static_argument_prod(sf_production_setup_devices):
    _test_static_argument(sf_production_setup_devices)


def test_static_argument_sim(sf_simulation_setup_devices):
    _test_static_argument(sf_simulation_setup_devices)


def test_matmul(sf_production_setup_devices):
    # PYU
    x = sf_production_setup_devices.alice(np.random.rand)(3, 4)
    y = sf_production_setup_devices.bob(np.random.rand)(4, 5)

    # SPU
    z_ = sf_production_setup_devices.spu2(lambda a, b: a @ b)(
        x.to(sf_production_setup_devices.spu2), y.to(sf_production_setup_devices.spu2)
    )

    # FIXME: precision is not good.
    np.testing.assert_almost_equal(
        sf.reveal(x) @ sf.reveal(y), sf.reveal(z_), decimal=3
    )
