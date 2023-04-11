import math

import matplotlib
import numpy as np
import matplotlib.pyplot as plt
from SIR_model import simulate_stochastic_SIR, simulate_deterministic_SIR, vectorised_SIR_simulator


### Try to simulate transmisson (SIR) model with Bayesian inference
### https://researchonline.lshtm.ac.uk/id/eprint/4654745/1/1-s2.0-S175543651930026X-main.pdf

## Set-up ABC model - manually
def ABC_SIR(n_days, n_infected, beta, gamma, N, n_particles, distance_threshold,
            simulate_gamma=None, simulate_n_infected=None, simulate_beta=None, simulate_N=None):
    """

    :param n_days:
    :param n_infected:
    :param beta:
    :param gamma:
    :param N:
    :param n_particles:
    :param distance_threshold:
    :return: res: array of shape (n_particles, n_par_estimated+1)
    """
    par_to_estimate = {
        "simulate_gamma": simulate_gamma,
        'simulate_n_infected': simulate_n_infected,
        'simulate_beta': simulate_beta,
        'simulate_N': simulate_N
    }
    n_par_estimated = len(par_to_estimate)  # number of estimated parameters
    s_observed, i_observed, r_observed = simulate_deterministic_SIR(n_days=n_days, n_infected=n_infected, beta=beta,
                                                                    gamma=gamma, N=N)[1:]

    res = np.zeros((n_particles, n_par_estimated, 2))  # model parameter(s) and distance

    key_idx = 0
    for key, item in par_to_estimate.items():
        if not item: continue
        par_accepted_counter = 0  # count of accepted parameters
        par_all_counter = 0  # count of all proposed parameters
        while par_accepted_counter < n_particles:
            # Generate random parameters
            beta = np.random.uniform(0, 1) if key == 'simulate_beta' else beta
            gamma = np.random.uniform(0, 1) if key == 'simulate_gamma' else gamma
            n_infected = np.random.randint(1, 1000) if key == 'simulate_n_infected' else n_infected
            N = np.random.randint(10, 1000) if key == 'simulate_N' else N
            n_days = np.random.randint(10, 300) if key == 'simulate_n_days' else n_days
            # Simulate model ### prior distribution  ###TODO: how to implement summary statistics here?
            s_simulated, i_simulated, r_simulated = simulate_stochastic_SIR(n_days=n_days, n_infected=n_infected,
                                                                            beta=beta, gamma=gamma, N=N)[1:]
            # Calculate distance
            distance = np.linalg.norm(i_observed - i_simulated)  ## Euclidean distance
            if distance < distance_threshold:
                par_value = beta if key == 'simulate_beta' else gamma if key == 'simulate_gamma' else n_infected if key == 'simulate_n_infected' else N
                res[par_accepted_counter, key_idx, :] = np.asarray([par_value, distance])
                par_accepted_counter += 1
                print(f'Accepted {par_accepted_counter} of {n_particles} for {key}. Distance: {distance}')

            par_all_counter += 1
        key_idx += 1
    return res, par_to_estimate


def plot_distances(res, par_to_estimate):
    # plt.hist(res[:,1])
    # plt.scatter(res[:,0], y)
    plt.figure(figsize=(18, 21))
    plt.subplots_adjust(hspace=0.5)
    idx = 0
    for parameter, bool_value in par_to_estimate.items():
        if not bool_value: continue
        # x --> parameter value
        # y --> 1/distance
        ax = plt.subplot(3, 3, idx + 1)
        x, y = res[:, idx, 0], 1 / res[:, idx, 1]  # inverse distance
        ax.scatter(x, y)
        ax.set_ylabel("1/Distance")
        ax.set_xlabel(f"{parameter} values")
        idx += 1
    plt.show()

    """plot_distances(*ABC_SIR(
        n_particles=100,
        distance_threshold = 500,
        beta = 0.3, #true values
        gamma = 0.1, #true values
        n_infected = 3, #true values
        N = 1000, #true values --> population size
        n_days = 150, #true values
        simulate_beta = True,
        simulate_gamma=True,
        simulate_n_infected=True,
        simulate_N=True
    ))"""


### Try ELFI ### only works with Python 3.7
import elfi
import scipy.stats as ss


# print(vectorised_SIR_simulator(0.3, 0.1, 3, 1000, 10, 2))

def plot_sir_matrix(sir_matrix, separate_plots=False):
    plt.figure(figsize=(10, 5))
    plt.xlabel('Days')
    plt.ylabel('Number of people')

    if separate_plots:
        for i in range(sir_matrix.shape[2]):
            ax = plt.subplot(2, 3, i + 1)
            ax.plot(sir_matrix[:, 0, i], label='infected')
            ax.plot(sir_matrix[:, 1, i], label='recovered')
            ax.plot(sir_matrix[:, 2, i], label='susceptible')
    else:
        ## Plot all in one
        plt.plot(sir_matrix[:, 0, :], label='infected', c='r', alpha=0.5)
        plt.plot(sir_matrix[:, 1, :], label='recovered', c='g', alpha=0.5)
        plt.plot(sir_matrix[:, 2, :], label='susceptible', c='b', alpha=0.5)

    handles, labels = plt.gca().get_legend_handles_labels()
    by_label = dict(zip(labels, handles))
    plt.legend(by_label.values(), by_label.keys())
    plt.show()


# plot_sir_matrix(vectorised_SIR_simulator([0.3,0.5,0.9], [0.01,0.2,0.7], 5, 50, 100, 3), separate_plots=True)


def elfi_parameter_trial(gamma_true, beta_true, n_infected_init=10, N=1000, n_days=128, number_of_batches=1,
                         rejection_threshold=0.5, n_samples=1000):
    gamma = elfi.Prior(ss.uniform, 0, 1)
    beta = elfi.Prior(ss.uniform, 0, 1)

    # gamma_init = np.array([0.2, 0.2, 0.2])
    gamma_true = [gamma_true]
    # beta_init = np.array([0.4, 0.4, 0.4])
    beta_true = [beta_true]

    y_obs = vectorised_SIR_simulator(
        beta=beta_true,
        gamma=gamma_true,
        n_init_infected=n_infected_init,
        N=N,
        n_days=n_days,
        n_obs=number_of_batches
    )

    # Add the simulator node and observed data to the model
    sim = elfi.Simulator(vectorised_SIR_simulator, beta, gamma, n_infected_init, N, n_days, number_of_batches,
                         observed=y_obs)

    # Add summary statistics to the model
    S1 = elfi.Summary(total_infected, sim, number_of_batches, name="total_infected_summary")
    S2 = elfi.Summary(peak_infected, sim, number_of_batches, name="peak_infected_summary")

    # Specify distance as euclidean between summary vectors (S1, S2) from simulated and
    # observed data
    d = elfi.Distance('euclidean', S1, S2)
    # d = elfi.Distance('seuclidean', S1, S2)

    # Plot the complete model (requires graphviz)
    # elfi.draw(d, filename="./elfi_SIR")

    # Run the rejection sampler
    rej = elfi.Rejection(d, batch_size=number_of_batches, seed=1)

    elfi.set_client('multiprocessing')
    res = rej.sample(n_samples, threshold=rejection_threshold)

    # np.save('gamma_data.npy', res.samples['gamma'])
    # np.save('beta_data.npy', res.samples['beta'])
    ## Tries to create different thresholds for each batch

    print(res.method_name, f"\nAcceptance rate: {res.meta['accept_rate']}\n Means:\n{res.sample_means_and_95CIs}", )

    res.plot_marginals()
    plt.show()


def summarise_recovery(x, n_batches=1):
    rv = np.array([sigmoid(-x[:, 1, j]) for j in range(n_batches)])
    return rv


def summarise_infected_sigmoid(x, n_batches=1):
    rv = np.array([sigmoid(x[:, 0, j]) for j in range(n_batches)])
    return rv


def summarise_infected(x, n_batches=1):
    r_array = np.zeros([n_batches, x.shape[0]])
    for j in range(n_batches):
        var_infected = np.var(x[:, 0, j])
        mean_infected = np.mean(x[:, 0, j])
        g = gaussian(x[:, 0, j], sigma=np.sqrt(var_infected), mu=mean_infected)
        r_array[j] = g

    return r_array


def sigmoid(x):
    return 1 / (1 + np.exp(-x))


def gaussian(x, mu, sigma):
    return 1 / (sigma * np.sqrt(2 * np.pi)) * np.exp(-(x - mu) ** 2 / (2 * sigma ** 2))


def total_infected(x, n_batches=1):
    rv = np.array([np.sum(x[:, 0, j]) for j in range(n_batches)])
    return rv


def peak_infected(x, n_batches=1):
    rv = np.array([np.max(x[:, 0, j]) for j in range(n_batches)])
    return rv


def recovery_variance(x, n_batches=1):
    rv = np.array([np.var(x[:, 1, j]) for j in range(n_batches)])
    return rv


"""elfi_parameter_trial(gamma_true=0.1, beta_true=0.6, number_of_batches=3,
                     rejection_threshold=0.5, n_samples=100,
                     n_days=32, N=100, n_infected_init=3)"""


## Write BOLFI (Bayesian Optimisation LFI) code here

def create_elfi_model_SIR(
        gamma_true, beta_true, n_infected_init=3, N=100, n_days=32, number_of_batches=1
):
    gamma = elfi.Prior(ss.uniform, 0, 1)
    beta = elfi.Prior(ss.uniform, 0, 1)

    # gamma_init = np.array([0.2, 0.2, 0.2])
    gamma_true = [gamma_true]
    # beta_init = np.array([0.4, 0.4, 0.4])
    beta_true = [beta_true]

    y_obs = vectorised_SIR_simulator(
        beta=beta_true,
        gamma=gamma_true,
        n_init_infected=n_infected_init,
        N=N,
        n_days=n_days,
        n_obs=number_of_batches
    )

    # Add the simulator node and observed data to the model
    sim = elfi.Simulator(vectorised_SIR_simulator, beta, gamma, n_infected_init, N, n_days, number_of_batches,
                         observed=y_obs, name="SIR_simulator")

    # Add summary statistics to the model
    # S1 = elfi.Summary(summarise_recovery, sim, number_of_batches, name="recovered_summary")
    # S2 = elfi.Summary(summarise_infected, sim, number_of_batches, name="infected_summary")

    S1 = elfi.Summary(total_infected, sim, number_of_batches, name="total_infected_summary")
    S2 = elfi.Summary(peak_infected, sim, number_of_batches, name="peak_infected_summary")
    S3 = elfi.Summary(recovery_variance, sim, number_of_batches, name="recovery_variance_summary")

    # Specify distance as euclidean between summary vectors (S1, S2) from simulated and
    # observed data
    d = elfi.Distance('euclidean', S1, S2, S3)

    return d


def bolfi_sir_trial():
    # Set an arbitrary global seed to keep the randomly generated quantities the same
    seed = 1
    np.random.seed(seed)
    elfi.set_client('multiprocessing')
    model = create_elfi_model_SIR(gamma_true=0.1, beta_true=0.4, number_of_batches=1)
    # elfi.draw(model, filename="./bolfi_SIR")

    ## Take the log of the distance to reduce the influence of outliers on Gaussian Process
    log_distance = elfi.Operation(np.log, model)

    # Set up the inference method
    bolfi = elfi.BOLFI(
        log_distance, batch_size=1, initial_evidence=20,
        update_interval=1, bounds={'beta': (0, 1), 'gamma': (0, 1)},
        seed=seed)

    # Fit the surrogate model
    post = bolfi.fit(n_evidence=1200)
    # post2 = bolfi.extract_posterior(-1.)

    print(bolfi.target_model)

    # Plot the results
    # bolfi.plot_state()
    bolfi.plot_discrepancy()
    plt.show()
    # post.plot(logpdf=True)
    # post2.plot(logpdf=True)

    ### Sample from the posterior
    result_BOLFI = bolfi.sample(2000, algorithm='metropolis')

    print(result_BOLFI)

    result_BOLFI.plot_traces()
    result_BOLFI.plot_marginals()
    plt.show()


#bolfi_sir_trial()

## Fisher Wright model bolfi trial
from FW_model import fisher_wright_simulator


def bolfi_FW_trial():
    seed = 1
    np.random.seed(seed)
    elfi.set_client('multiprocessing')
    model = create_elfi_model_FW(mutation_true=0.1, n_individuals=100, n_generations=50,
                                 number_of_batches=1, n_alleles=2)

    #elfi.draw(model, filename="./bolfi_FW")

    ## Take the log of the distance to reduce the influence of outliers on Gaussian Process
    log_distance = elfi.Operation(np.log, model)

    # Set up the inference method
    bolfi = elfi.BOLFI(
        log_distance, batch_size=1, initial_evidence=30,
        update_interval=1, bounds={'mutation': (0.0, 0.5)},
        seed=seed, acq_noise_var=[0.0, 0.0])

    # Fit the surrogate model
    post = bolfi.fit(n_evidence=1200)
    # post2 = bolfi.extract_posterior(-1.)

    print(bolfi.target_model)

    # Plot the results
    # bolfi.plot_state()
    bolfi.plot_discrepancy()
    plt.show()
    # post.plot(logpdf=True)
    # post2.plot(logpdf=True)

    ### Sample from the posterior
    result_BOLFI = bolfi.sample(20, algorithm='metropolis')

    print(result_BOLFI)

    result_BOLFI.plot_traces()
    result_BOLFI.plot_marginals()
    plt.show()


def create_elfi_model_FW(
        mutation_true=0.3, n_individuals=100, n_generations=100,
        number_of_batches=1, n_alleles=3,
        random_state=None, batch_size=None
):
    mutation = elfi.Prior(ss.uniform, 0, 1)
    mutation_true = [mutation_true]
    y_obs = fisher_wright_simulator(
        n_alleles=n_alleles,
        n_repeats=number_of_batches,
        n_generations=n_generations,
        n_individuals=n_individuals,
        mutation_rates=mutation_true,
        plot=False,
        set_allele_freq_equal=True,
    )

    ##n_repeats, n_generations, n_individuals, n_alleles=None,alleles=None, mutation_rates:np.array=None,
    # Add the simulator node and observed data to the model
    sim = elfi.Simulator(
        fisher_wright_simulator,
        number_of_batches, n_generations, n_individuals, n_alleles, None, mutation,
        observed=y_obs, name="FW_simulator"
    )

    # Add summary statistics to the model
    S1 = elfi.Summary(sumarise_mean, sim, n_alleles, number_of_batches, name="allele_freq_mean_summary")
    S2 = elfi.Summary(summarise_variance, sim, n_alleles, number_of_batches, name="allele_freq_var_summary")
    # Specify distance as euclidean between summary vectors (S1, S2) from simulated and
    # observed data
    d = elfi.Distance('euclidean', S1, S2)

    return d


def summarise_variance(allele_freqs, n_alleles, n_batches=1):
    rv = [np.array([np.var(allele_freqs[:, b, i]) for i in range(n_alleles)]) for b in range(n_batches)]
    return rv


def sumarise_mean(allele_freqs, n_alleles, n_batches=1):
    rv = [np.array([np.mean(allele_freqs[:, b, i]) for i in range(n_alleles)]) for b in range(n_batches)]
    return rv


bolfi_FW_trial()