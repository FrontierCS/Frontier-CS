#include <bits/stdc++.h>
using namespace std;

const int TH = 100; // consider primes up to 100 for greedy improvements

vector<int> spf;
vector<int> primes;

void sieve(int n) {
    spf.assign(n + 1, 0);
    for (int i = 2; i <= n; i++) {
        if (spf[i] == 0) {
            spf[i] = i;
            primes.push_back(i);
        }
        for (int p : primes) {
            if (p > spf[i] || i * p > n) break;
            spf[i * p] = p;
        }
    }
}

// toggle[p] = list of indices i where v_p(i) is odd (p <= TH)
unordered_map<int, vector<int>> toggle;

void compute_toggle(int n) {
    for (int p : primes) {
        if (p > TH) break;
        vector<int> list;
        long long pe = p;
        int e = 1;
        while (pe <= n) {
            if (e % 2 == 1) {
                for (long long t = 1; t * pe <= n; t++) {
                    if (t % p != 0) {
                        list.push_back(pe * t);
                    }
                }
            }
            pe *= p;
            e++;
        }
        sort(list.begin(), list.end());
        toggle[p] = list;
    }
}

// Compute simple candidate (1..7)
pair<vector<int>, int64_t> compute_simple(int candidate_id, int n) {
    vector<int> f(n + 1);
    f[1] = 1;
    // assign values to primes
    for (int p : primes) {
        if (p > n) break;
        if (candidate_id == 1) { // Liouville
            f[p] = -1;
        } else if (candidate_id == 2) { // mod4, f(2)=1
            if (p == 2) f[p] = 1;
            else if (p % 4 == 1) f[p] = 1;
            else f[p] = -1;
        } else if (candidate_id == 3) { // mod4, f(2)=-1
            if (p == 2) f[p] = -1;
            else if (p % 4 == 1) f[p] = 1;
            else f[p] = -1;
        } else if (candidate_id == 4) { // mod3, f(3)=1
            if (p == 3) f[p] = 1;
            else if (p % 3 == 1) f[p] = 1;
            else f[p] = -1;
        } else if (candidate_id == 5) { // mod3, f(3)=-1
            if (p == 3) f[p] = -1;
            else if (p % 3 == 1) f[p] = 1;
            else f[p] = -1;
        } else if (candidate_id == 6) { // mod8, f(2)=1
            if (p == 2) f[p] = 1;
            else if (p % 8 == 1 || p % 8 == 7) f[p] = 1;
            else f[p] = -1;
        } else if (candidate_id == 7) { // mod8, f(2)=-1
            if (p == 2) f[p] = -1;
            else if (p % 8 == 1 || p % 8 == 7) f[p] = 1;
            else f[p] = -1;
        }
    }
    // fill composites using complete multiplicativity
    for (int i = 2; i <= n; i++) {
        if (f[i] == 0) { // composite not set
            f[i] = f[spf[i]] * f[i / spf[i]];
        }
    }
    // compute prefix sums and max absolute partial sum
    vector<int64_t> S(n + 1);
    S[0] = 0;
    int64_t max_abs = 0;
    for (int i = 1; i <= n; i++) {
        S[i] = S[i - 1] + f[i];
        if (llabs(S[i]) > max_abs) max_abs = llabs(S[i]);
    }
    return {f, max_abs};
}

// Greedy improvement starting from a base candidate
pair<vector<int>, int64_t> compute_greedy(int base_candidate_id, int n) {
    auto [f, base_max] = compute_simple(base_candidate_id, n);
    vector<int64_t> S(n + 1);
    S[0] = 0;
    int64_t current_max = 0;
    for (int i = 1; i <= n; i++) {
        S[i] = S[i - 1] + f[i];
        if (llabs(S[i]) > current_max) current_max = llabs(S[i]);
    }

    // iterate over small primes in increasing order
    for (int p : primes) {
        if (p > TH) break;
        const vector<int>& list = toggle[p];
        // simulate flipping p
        int64_t delta = 0;
        size_t ptr = 0;
        int64_t new_max = 0;
        for (int k = 1; k <= n; k++) {
            while (ptr < list.size() && list[ptr] == k) {
                delta += -2 * f[k];
                ptr++;
            }
            int64_t val = S[k] + delta;
            if (llabs(val) > new_max) new_max = llabs(val);
        }
        // if flipping reduces the maximum, apply the flip
        if (new_max < current_max) {
            // store old f values for indices in list
            vector<int> old_vals(list.size());
            for (size_t idx = 0; idx < list.size(); idx++) {
                int i = list[idx];
                old_vals[idx] = f[i];
                f[i] *= -1;
            }
            // apply range updates to S using a difference array
            vector<int64_t> diff(n + 2, 0);
            for (size_t idx = 0; idx < list.size(); idx++) {
                int i = list[idx];
                int64_t change = -2 * old_vals[idx];
                diff[i] += change;
                diff[n + 1] -= change;
            }
            int64_t running = 0;
            current_max = 0;
            for (int k = 1; k <= n; k++) {
                running += diff[k];
                S[k] += running;
                if (llabs(S[k]) > current_max) current_max = llabs(S[k]);
            }
        }
    }
    return {f, current_max};
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(0);

    int n;
    cin >> n;
    sieve(n);
    compute_toggle(n);

    vector<pair<vector<int>, int64_t>> candidates;
    // simple candidates 1..7
    for (int id = 1; id <= 7; id++) {
        candidates.push_back(compute_simple(id, n));
    }
    // greedy candidates: 8 = greedy Liouville, 9 = greedy mod4 (f2=1)
    candidates.push_back(compute_greedy(1, n));
    candidates.push_back(compute_greedy(2, n));

    // choose the candidate with smallest maximum absolute partial sum
    int best_idx = 0;
    int64_t best_max = candidates[0].second;
    for (size_t i = 1; i < candidates.size(); i++) {
        if (candidates[i].second < best_max) {
            best_max = candidates[i].second;
            best_idx = i;
        }
    }

    // output f(1) .. f(n)
    const vector<int>& best_f = candidates[best_idx].first;
    for (int i = 1; i <= n; i++) {
        cout << best_f[i] << (i == n ? "\n" : " ");
    }

    return 0;
}