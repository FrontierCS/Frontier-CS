#include <bits/stdc++.h>
using namespace std;

typedef long long ll;

// Interleave bits of two 31-bit numbers to get a 62-bit Morton code
static ll interleave(uint32_t x, uint32_t y) {
    ll res = 0;
    for (int i = 0; i < 31; ++i) {
        res |= (ll)((x >> i) & 1) << (2 * i);
        res |= (ll)((y >> i) & 1) << (2 * i + 1);
    }
    return res;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int N;
    cin >> N;
    vector<ll> x(N), y(N);
    for (int i = 0; i < N; ++i) {
        cin >> x[i] >> y[i];
    }

    // Sieve for primes among city IDs
    vector<bool> is_prime(N, false);
    if (N > 2) {
        vector<bool> sieve(N, true);
        sieve[0] = sieve[1] = false;
        for (int p = 2; p < N; ++p) {
            if (sieve[p]) {
                is_prime[p] = true;
                if ((ll)p * p < N) {
                    for (int j = p * p; j < N; j += p) {
                        sieve[j] = false;
                    }
                }
            }
        }
    }

    const ll OFFSET = 1000000000LL;  // shift coordinates to non‑negative
    vector<pair<ll, int>> morton(N);
    for (int i = 0; i < N; ++i) {
        uint32_t nx = (uint32_t)(x[i] + OFFSET);
        uint32_t ny = (uint32_t)(y[i] + OFFSET);
        morton[i] = {interleave(nx, ny), i};
    }
    sort(morton.begin(), morton.end());

    // Find position of city 0 in the Morton order
    int idx0 = -1;
    for (int i = 0; i < N; ++i) {
        if (morton[i].second == 0) {
            idx0 = i;
            break;
        }
    }

    // Build initial tour: start at 0, then cities after 0 in Morton order,
    // then cities before 0, finally return to 0.
    vector<int> P(N + 1);
    P[0] = 0;
    int pos = 1;
    for (int i = idx0 + 1; i < N; ++i) {
        P[pos++] = morton[i].second;
    }
    for (int i = 0; i < idx0; ++i) {
        P[pos++] = morton[i].second;
    }
    P[N] = 0;

    // Precompute Euclidean distances between consecutive cities in the tour
    auto dist_func = [&](int a, int b) -> double {
        double dx = x[a] - x[b];
        double dy = y[a] - y[b];
        return sqrt(dx * dx + dy * dy);
    };
    vector<double> dist(N);  // dist[i] = distance(P[i] -> P[i+1])
    for (int i = 0; i < N; ++i) {
        dist[i] = dist_func(P[i], P[i+1]);
    }

    // Function to compute change in penalized length if we swap P[i] and P[j]
    auto delta_swap = [&](int i, int j) -> double {
        if (i == j) return 0.0;
        if (i > j) swap(i, j);
        vector<int> steps;
        if (i >= 1) steps.push_back(i);
        if (i + 1 <= N) steps.push_back(i + 1);
        if (j >= 1) steps.push_back(j);
        if (j + 1 <= N) steps.push_back(j + 1);
        sort(steps.begin(), steps.end());
        steps.erase(unique(steps.begin(), steps.end()), steps.end());

        double delta = 0.0;
        for (int t : steps) {
            int idx = t - 1;  // index in dist array
            int start_old = P[t-1];
            int end_old   = P[t];
            double mult_old = (t % 10 == 0 && !is_prime[start_old]) ? 1.1 : 1.0;
            double dist_old = dist[idx];

            int start_new = (t-1 == i) ? P[j] : (t-1 == j) ? P[i] : P[t-1];
            int end_new   = (t == i)   ? P[j] : (t == j)   ? P[i] : P[t];
            double mult_new = (t % 10 == 0 && !is_prime[start_new]) ? 1.1 : 1.0;
            double dist_new = dist_func(start_new, end_new);

            delta += mult_new * dist_new - mult_old * dist_old;
        }
        return delta;
    };

    // Try to improve penalty steps by swapping with nearby primes
    const int WINDOW = 30;
    for (int s = 9; s < N; s += 10) {   // positions that must be prime to avoid penalty
        if (is_prime[P[s]]) continue;
        int best_j = -1;
        double best_delta = 0.0;
        int left = max(1, s - WINDOW);
        int right = min(N - 1, s + WINDOW);
        for (int j = left; j <= right; ++j) {
            if (j == s || !is_prime[P[j]]) continue;
            double delta = delta_swap(s, j);
            if (delta < best_delta) {
                best_delta = delta;
                best_j = j;
            }
        }
        if (best_j != -1 && best_delta < -1e-9) {
            // Perform the swap
            swap(P[s], P[best_j]);
            // Update distances for affected edges
            vector<int> steps;
            if (s >= 1) steps.push_back(s);
            if (s + 1 <= N) steps.push_back(s + 1);
            if (best_j >= 1) steps.push_back(best_j);
            if (best_j + 1 <= N) steps.push_back(best_j + 1);
            sort(steps.begin(), steps.end());
            steps.erase(unique(steps.begin(), steps.end()), steps.end());
            for (int t : steps) {
                dist[t-1] = dist_func(P[t-1], P[t]);
            }
        }
    }

    // Output the tour
    cout << N + 1 << '\n';
    for (int i = 0; i <= N; ++i) {
        cout << P[i] << '\n';
    }

    return 0;
}