# Variational Autoencoder with Structured Latent Space

## Abstract

We propose StructVAE, a variational autoencoder that enforces cluster
structure in the latent space using a mixture of Gaussians prior.

## 1. Method

### 1.1 Objective

The ELBO loss is: L = E_q[log p(x|z)] - beta * KL(q(z|x) || p(z))
where p(z) = sum_k pi_k N(mu_k, sigma_k^2) is a Gaussian mixture prior.

### 1.2 Reparameterization

We use the reparameterization trick: z = mu + sigma * epsilon, where epsilon ~ N(0, I).
The KL divergence has closed form: KL = 0.5 * sum(sigma^2 + mu^2 - 1 - log sigma^2)

### 1.3 Cluster Assignment

The posterior cluster assignment: p(k|x) = pi_k * N(z|mu_k, sigma_k^2) / sum_j pi_j * N(z|mu_j, sigma_j^2)

## 2. Experiments

We evaluate on MNIST and Fashion-MNIST for clustering quality.
NMI score: 0.82 on MNIST, outperforming standard VAE (0.65).
