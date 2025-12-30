#include <bits/stdc++.h>
using namespace std;

const int N = 100;
const int L = 500000;

int T[N];
int O[N], E[N];
int a[N], b[N];
int best_a[N], best_b[N];
int global_best_err = 1e9;

// simulate the cleaning plan and compute error
int simulate(const int a[], const int b[], int t[]) {
    fill(t, t + N, 0);
    int cur = 0;
    for (int w = 0; w < L; ++w) {
        t[cur]++;
        if (w == L - 1) break;
        int cnt = t[cur];  // number of times cur has been assigned up to now
        if (cnt % 2 == 1) cur = a[cur];
        else cur = b[cur];
    }
    int err = 0;
    for (int i = 0; i < N; ++i) err += abs(t[i] - T[i]);
    return err;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    // read input
    int n, l;
    cin >> n >> l;  // n=100, l=500000 fixed
    for (int i = 0; i < n; ++i) cin >> T[i];

    // precompute O_i, E_i
    for (int i = 0; i < n; ++i) {
        O[i] = (T[i] + 1) / 2;  // ceil(T_i/2)
        E[i] = T[i] - O[i];     // floor(T_i/2)
    }

    // random device
    random_device rd;
    mt19937 rng(rd());
    uniform_int_distribution<int> dist(0, n-1);
    uniform_real_distribution<double> prob(0.0, 1.0);

    // try each possible final employee f
    for (int f = 0; f < n; ++f) {
        if (T[f] == 0) continue;  // final employee must appear at least once

        // compute adjusted odd/even departure counts
        int o_prime[N], e_prime[N];
        for (int i = 0; i < n; ++i) {
            if (i != f) {
                o_prime[i] = O[i];
                e_prime[i] = E[i];
            } else {
                if (T[f] % 2 == 1) { // last occurrence odd
                    o_prime[f] = O[f] - 1;
                    e_prime[f] = E[f];
                } else {             // last occurrence even
                    o_prime[f] = O[f];
                    e_prime[f] = E[f] - 1;
                }
            }
        }

        // compute target arrivals D_j
        int D[N];
        for (int j = 0; j < n; ++j) {
            D[j] = T[j] - (j == 0 ? 1 : 0);
        }

        // simulated annealing to assign a_i, b_i
        int cur_a[N], cur_b[N];
        int cur_sum[N] = {0};
        int cur_err = 0;

        // random initial assignment
        for (int i = 0; i < n; ++i) {
            cur_a[i] = dist(rng);
            cur_b[i] = dist(rng);
            cur_sum[cur_a[i]] += o_prime[i];
            cur_sum[cur_b[i]] += e_prime[i];
        }
        for (int j = 0; j < n; ++j) {
            cur_err += abs(cur_sum[j] - D[j]);
        }

        int best_local_err = cur_err;
        int best_local_a[N], best_local_b[N];
        memcpy(best_local_a, cur_a, sizeof(cur_a));
        memcpy(best_local_b, cur_b, sizeof(cur_b));

        double temp = 1000.0;
        const double cool = 0.9995;
        const int iterations = 20000;

        for (int iter = 0; iter < iterations; ++iter) {
            int i = dist(rng);
            int type = rng() % 2; // 0: change a_i, 1: change b_i
            int old_j = (type == 0 ? cur_a[i] : cur_b[i]);
            int new_j;
            do {
                new_j = dist(rng);
            } while (new_j == old_j);

            int val = (type == 0 ? o_prime[i] : e_prime[i]);
            int old_cur_old = cur_sum[old_j];
            int old_cur_new = cur_sum[new_j];
            int new_cur_old = old_cur_old - val;
            int new_cur_new = old_cur_new + val;

            int delta = (abs(new_cur_old - D[old_j]) + abs(new_cur_new - D[new_j]))
                      - (abs(old_cur_old - D[old_j]) + abs(old_cur_new - D[new_j]));

            if (delta < 0 || prob(rng) < exp(-delta / temp)) {
                // accept move
                cur_sum[old_j] = new_cur_old;
                cur_sum[new_j] = new_cur_new;
                if (type == 0) cur_a[i] = new_j;
                else cur_b[i] = new_j;
                cur_err += delta;

                if (cur_err < best_local_err) {
                    best_local_err = cur_err;
                    memcpy(best_local_a, cur_a, sizeof(cur_a));
                    memcpy(best_local_b, cur_b, sizeof(cur_b));
                    if (best_local_err == 0) break; // perfect
                }
            }
            temp *= cool;
        }

        // keep global best
        if (best_local_err < global_best_err) {
            global_best_err = best_local_err;
            memcpy(best_a, best_local_a, sizeof(best_local_a));
            memcpy(best_b, best_local_b, sizeof(best_local_b));
            if (global_best_err == 0) break; // found perfect solution
        }
    }

    // output the best found assignment
    for (int i = 0; i < n; ++i) {
        cout << best_a[i] << " " << best_b[i] << "\n";
    }

    return 0;
}