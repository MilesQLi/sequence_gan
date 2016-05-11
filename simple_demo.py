import model

import numpy as np
import tensorflow as tf
import random

NUM_EMB = 4
EMB_DIM = 5
HIDDEN_DIM = 10
SEQ_LENGTH = 5
START_TOKEN = 0

EPOCH_ITER = 1000
CURRICULUM_RATE = 0.03  # how quickly to move from supervised training to unsupervised
TRAIN_ITER = 100000  # generator/discriminator alternating
D_STEPS = 2  # how many times to train the discriminator per generator step
LEARNING_RATE = 0.01 * SEQ_LENGTH
SEED = 88


def get_trainable_model():
    return model.GRU(
        NUM_EMB, EMB_DIM, HIDDEN_DIM,
        SEQ_LENGTH, START_TOKEN,
        learning_rate=LEARNING_RATE)


def verify_sequence(seq):
    downhill = True
    prev = NUM_EMB
    for tok in seq:
        if tok == START_TOKEN:
            return False
        if downhill:
            if tok > prev:
                downhill = False
        elif tok < prev:
            return False
        prev = tok
    return True


def get_random_sequence():
    """Returns random valley sequence."""
    tokens = set(range(NUM_EMB))
    tokens.discard(START_TOKEN)
    tokens = list(tokens)

    pivot = int(random.random() * SEQ_LENGTH)
    left_of_pivot = []
    right_of_pivot = []
    for i in xrange(SEQ_LENGTH):
        tok = random.choice(tokens)
        if i <= pivot:
            left_of_pivot.append(tok)
        else:
            right_of_pivot.append(tok)

    left_of_pivot.sort(reverse=True)
    right_of_pivot.sort(reverse=False)

    return left_of_pivot + right_of_pivot


def train_epoch(sess, trainable_model, num_iter,
                proportion_supervised, g_steps, d_steps):
    """Perform training for model.

    sess: tensorflow session
    trainable_model: the model
    num_iter: number of iterations
    proportion_supervised: what proportion of iterations should the generator
        be trained in a supervised manner (rather than trained via discriminator).
    g_steps: number of generator training steps per iteration
    d_steps: number of discriminator training steps per iteration

    """
    supervised_g_losses = [0]  # we put in 0 to avoid empty slices
    unsupervised_g_losses = [0]  # we put in 0 to avoid empty slices
    d_losses = [0]
    expected_rewards = [0]
    supervised_correct_generation = [0]
    unsupervised_correct_generation = [0]
    supervised_gen_x = None
    unsupervised_gen_x = None
    print 'running %d iterations with %d g steps and %d d steps' % (num_iter, g_steps, d_steps)
    print 'of the g steps, %.2f will be supervised' % proportion_supervised
    for it in xrange(num_iter):
        for _ in xrange(g_steps):
            if random.random() < proportion_supervised:
                seq = get_random_sequence()
                _, g_loss, g_pred = trainable_model.pretrain_step(sess, seq)
                supervised_g_losses.append(g_loss)

                supervised_gen_x = np.argmax(g_pred, axis=1)
                supervised_correct_generation.append(
                    verify_sequence(supervised_gen_x))
            else:
                _, _, g_loss, expected_reward, unsupervised_gen_x = \
                    trainable_model.train_g_step(sess)
                expected_rewards.append(expected_reward)
                unsupervised_g_losses.append(g_loss)

                unsupervised_correct_generation.append(
                    verify_sequence(unsupervised_gen_x))

        for _ in xrange(d_steps):
            if random.random() < 0.5:
                seq = get_random_sequence()
                _, d_loss = trainable_model.train_d_real_step(sess, seq)
            else:
                _, d_loss = trainable_model.train_d_gen_step(sess)
            d_losses.append(d_loss)

    print 'epoch statistics:'
    print '>>>> discriminator loss:', np.mean(d_losses)
    print '>>>> generator loss:', np.mean(supervised_g_losses), np.mean(unsupervised_g_losses)
    print '>>>> correct generations (supervised, unsupervised):', np.mean(supervised_correct_generation), np.mean(unsupervised_correct_generation)
    print '>>>> sampled generations (supervised, unsupervised):', supervised_gen_x, unsupervised_gen_x
    print '>>>> expected rewards:', np.mean(expected_rewards)


def main():
    random.seed(SEED)
    np.random.seed(SEED)

    trainable_model = get_trainable_model()
    sess = tf.Session()
    sess.run(tf.initialize_all_variables())

    print 'training'
    for epoch in xrange(TRAIN_ITER // EPOCH_ITER):
        print 'epoch', epoch
        proportion_supervised = max(0.0, 1.0 - CURRICULUM_RATE * epoch)
        train_epoch(sess, trainable_model, EPOCH_ITER,
                    proportion_supervised=proportion_supervised,
                    g_steps=1, d_steps=D_STEPS)


if __name__ == '__main__':
    main()