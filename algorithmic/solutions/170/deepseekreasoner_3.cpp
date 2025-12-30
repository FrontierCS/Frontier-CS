#include <iostream>
#include <vector>
#include <cstdlib>
#include <cmath>
#include <algorithm>
#include <random>
#include <ctime>

using namespace std;

const int N = 100;
const long long L = 500000;

long long simulate(const vector<int>& a, const vector<int>& b, const vector<int>& T, vector<long long>& cnt) {
    fill(cnt.begin(), cnt.end(), 0);
    int cur = 0;
    cnt[cur] = 1; // week 1
    for (long long w = 2; w <= L; ++w) {
        int parity = cnt[cur] % 2;
        int nxt = (parity == 1) ? a[cur] : b[cur];
        cnt[nxt]++;
        cur = nxt;
    }
    long long error = 0;
    for (int i = 0; i < N; ++i) {
        error += llabs(cnt[i] - T[i]);
    }
    return error;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int N_in;
    long long L_in;
    cin >> N_in >> L_in; // N_in should be 100, L_in=500000
    vector<int> T(N);
    for (int i = 0; i < N; ++i) {
        cin >> T[i];
    }

    // random number generator
    mt19937 rng(time(0));
    uniform_int_distribution<int> emp_dist(0, N-1);
    uniform_int_distribution<int> choice_dist(0, 1);
    uniform_real_distribution<double> prob_dist(0.0, 1.0);

    // initial solution: simple cycle
    vector<int> a(N), b(N);
    for (int i = 0; i < N; ++i) {
        a[i] = b[i] = (i + 1) % N;
    }

    vector<long long> cnt(N);
    long long current_error = simulate(a, b, T, cnt);
    vector<int> best_a = a, best_b = b;
    long long best_error = current_error;

    // simulated annealing parameters
    const int ITER = 200;
    double temperature = 1000.0;
    const double COOL = 0.99;

    for (int iter = 0; iter < ITER; ++iter) {
        // pick random employee and which edge to change
        int i = emp_dist(rng);
        int change_a = choice_dist(rng); // 0 -> change a, 1 -> change b
        int old_value;
        if (change_a == 0) {
            old_value = a[i];
            a[i] = emp_dist(rng);
        } else {
            old_value = b[i];
            b[i] = emp_dist(rng);
        }

        // simulate new configuration
        long long new_error = simulate(a, b, T, cnt);
        bool accept = false;
        if (new_error < current_error) {
            accept = true;
        } else {
            double prob = exp((current_error - new_error) / temperature);
            if (prob_dist(rng) < prob) {
                accept = true;
            }
        }

        if (accept) {
            current_error = new_error;
            if (current_error < best_error) {
                best_error = current_error;
                best_a = a;
                best_b = b;
            }
        } else {
            // revert
            if (change_a == 0) {
                a[i] = old_value;
            } else {
                b[i] = old_value;
            }
        }

        temperature *= COOL;
    }

    // output best found
    for (int i = 0; i < N; ++i) {
        cout << best_a[i] << " " << best_b[i] << "\n";
    }

    return 0;
}