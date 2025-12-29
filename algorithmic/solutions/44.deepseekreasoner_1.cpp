#include <bits/stdc++.h>
using namespace std;
typedef long long ll;

const int CANDIDATES = 200; // number of candidates to consider

vector<ll> x, y;
vector<bool> is_prime;

ll dist2(int a, int b) {
    ll dx = x[a] - x[b];
    ll dy = y[a] - y[b];
    return dx*dx + dy*dy;
}

// Find the nearest city to 'current' among the cities in set 's'
// by examining up to CANDIDATES/2 cities on each side in x-order.
int find_nearest_in_set(int current, const set<int>& s) {
    if (s.empty()) return -1;
    auto it = s.lower_bound(current);
    vector<int> candidates;
    // right side
    auto it_r = it;
    for (int i = 0; i < CANDIDATES/2 && it_r != s.end(); ++i, ++it_r) {
        candidates.push_back(*it_r);
    }
    // left side
    auto it_l = it;
    if (it_l != s.begin()) {
        --it_l;
        for (int i = 0; i < CANDIDATES/2; ++i) {
            candidates.push_back(*it_l);
            if (it_l == s.begin()) break;
            --it_l;
        }
    }
    if (candidates.empty()) return -1;
    int best = candidates[0];
    ll best_d2 = dist2(current, best);
    for (int cand : candidates) {
        ll d2 = dist2(current, cand);
        if (d2 < best_d2) {
            best_d2 = d2;
            best = cand;
        }
    }
    return best;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(0);
    int N;
    cin >> N;
    x.resize(N);
    y.resize(N);
    for (int i = 0; i < N; ++i) {
        cin >> x[i] >> y[i];
    }
    // Sieve for primes up to N-1
    is_prime.assign(N, true);
    if (N > 0) is_prime[0] = false;
    if (N > 1) is_prime[1] = false;
    for (int i = 2; i * i < N; ++i) {
        if (is_prime[i]) {
            for (int j = i * i; j < N; j += i) {
                is_prime[j] = false;
            }
        }
    }
    set<int> unvisited;
    set<int> primes_set;
    for (int i = 1; i < N; ++i) {
        unvisited.insert(i);
        if (is_prime[i]) {
            primes_set.insert(i);
        }
    }
    vector<int> P(N+1);
    P[0] = 0;
    int current = 0;
    for (int step = 1; step <= N-1; ++step) {
        bool need_prime = (step % 10 == 9);
        int next_city = -1;
        if (need_prime && !primes_set.empty()) {
            next_city = find_nearest_in_set(current, primes_set);
            if (next_city == -1) {
                next_city = *primes_set.begin();
            }
        } else {
            if (!unvisited.empty()) {
                next_city = find_nearest_in_set(current, unvisited);
                if (next_city == -1) {
                    next_city = *unvisited.begin();
                }
            }
        }
        // Fallback in case nothing was found (should not happen)
        if (next_city == -1) {
            next_city = *unvisited.begin();
        }
        P[step] = next_city;
        unvisited.erase(next_city);
        if (is_prime[next_city]) {
            primes_set.erase(next_city);
        }
        current = next_city;
    }
    P[N] = 0;
    cout << N+1 << "\n";
    for (int i = 0; i <= N; ++i) {
        cout << P[i] << "\n";
    }
    return 0;
}