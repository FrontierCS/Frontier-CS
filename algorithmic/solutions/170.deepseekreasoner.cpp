#include <iostream>
#include <vector>
#include <algorithm>
#include <random>
#include <cmath>
#include <cstring>
#include <climits>

using namespace std;

const int N = 100;
const int L = 500000;
const int TRIALS = 30;          // number of trials for greedy assignment
const int PENALTY_SELF = 10;    // penalty for assigning b[i]=i

int T[N];
int best_a[N], best_b[N];
long long best_err = LLONG_MAX;

// simulate and return error
long long simulate(const int a[N], const int b[N]) {
    int count[N] = {0};
    int cur = 0;
    for (int week = 0; week < L; ++week) {
        ++count[cur];
        if (week == L-1) break;
        int t = count[cur];
        int nxt = (t % 2 == 1) ? a[cur] : b[cur];
        cur = nxt;
    }
    long long err = 0;
    for (int i = 0; i < N; ++i) {
        err += abs(count[i] - T[i]);
    }
    return err;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    // read input
    int n, l;
    cin >> n >> l; // n is always 100, l is always 500000
    for (int i = 0; i < n; ++i) cin >> T[i];

    // random device
    random_device rd;
    mt19937 gen(rd());

    // main loop: multiple trials with random order
    for (int trial = 0; trial < TRIALS; ++trial) {
        int a[N], b[N];
        int load[N] = {0};

        // generate random order of employees
        vector<int> order(N);
        for (int i = 0; i < N; ++i) order[i] = i;
        shuffle(order.begin(), order.end(), gen);

        // greedy assignment of b[i]
        for (int idx = 0; idx < N; ++idx) {
            int i = order[idx];
            int best_j = -1;
            int best_cost = INT_MAX;
            for (int j = 0; j < N; ++j) {
                int cost = abs(load[j] + T[i] - T[j]);
                if (j == i) cost += PENALTY_SELF;
                if (cost < best_cost) {
                    best_cost = cost;
                    best_j = j;
                }
            }
            b[i] = best_j;
            load[best_j] += T[i];
        }

        // set a[i] = i, but for zero-target employees set both to b[i]
        for (int i = 0; i < N; ++i) {
            a[i] = i;
        }
        for (int i = 0; i < N; ++i) {
            if (T[i] == 0) {
                a[i] = b[i];
            }
        }

        // simulate and update best
        long long err = simulate(a, b);
        if (err < best_err) {
            best_err = err;
            memcpy(best_a, a, sizeof(best_a));
            memcpy(best_b, b, sizeof(best_b));
        }
    }

    // output the best found
    for (int i = 0; i < N; ++i) {
        cout << best_a[i] << " " << best_b[i] << "\n";
    }

    return 0;
}