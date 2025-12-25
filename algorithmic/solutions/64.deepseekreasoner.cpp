#include <iostream>
#include <vector>
#include <algorithm>
#include <cmath>
#include <random>
#include <string>
#include <cstdlib>
#include <ctime>
#include <climits>

using namespace std;

typedef long long ll;

ll llabs(ll x) { return x < 0 ? -x : x; }

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n;
    ll T;
    cin >> n >> T;
    vector<ll> a(n);
    for (int i = 0; i < n; ++i) {
        cin >> a[i];
    }

    // Greedy initial solution
    vector<bool> subset(n, false);
    ll cur_sum = 0;
    for (int i = 0; i < n; ++i) {
        if (llabs(cur_sum + a[i] - T) < llabs(cur_sum - T)) {
            cur_sum += a[i];
            subset[i] = true;
        }
    }
    ll best_err = llabs(cur_sum - T);
    vector<bool> best = subset;
    ll best_sum = cur_sum;

    // Simulated Annealing
    mt19937 rng(12345); // deterministic seed
    uniform_int_distribution<int> index_dist(0, n-1);
    uniform_real_distribution<double> prob_dist(0.0, 1.0);

    double temp = max(1.0, (double)best_err) * 10.0;
    const double cooling_rate = 0.999995;
    const int iterations = 300000;

    for (int iter = 0; iter < iterations; ++iter) {
        int i = index_dist(rng);
        ll new_sum = cur_sum;
        if (subset[i]) {
            new_sum -= a[i];
        } else {
            new_sum += a[i];
        }
        ll new_err = llabs(new_sum - T);
        ll delta = new_err - best_err; // compare to best_err? Actually should compare to current_err? Use current_err for acceptance.
        // For SA, we compare to current state's error.
        ll cur_err = llabs(cur_sum - T);
        delta = new_err - cur_err;

        if (delta < 0 || prob_dist(rng) < exp(-delta / temp)) {
            // accept move
            cur_sum = new_sum;
            subset[i] = !subset[i];
            cur_err = new_err;
            if (new_err < best_err) {
                best_err = new_err;
                best_sum = new_sum;
                best = subset;
            }
        }
        temp *= cooling_rate;
    }

    // Hill climbing on best found (single flips)
    bool improved = true;
    while (improved) {
        improved = false;
        for (int i = 0; i < n; ++i) {
            ll test_sum = best_sum;
            if (best[i]) {
                test_sum -= a[i];
            } else {
                test_sum += a[i];
            }
            ll test_err = llabs(test_sum - T);
            if (test_err < best_err) {
                best_err = test_err;
                best_sum = test_sum;
                best[i] = !best[i];
                improved = true;
            }
        }
    }

    // Output binary string
    string ans(n, '0');
    for (int i = 0; i < n; ++i) {
        if (best[i]) ans[i] = '1';
    }
    cout << ans << endl;

    return 0;
}