#include <bits/stdc++.h>
using namespace std;

static mt19937 rng((uint32_t)chrono::steady_clock::now().time_since_epoch().count());

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n;
    if (!(cin >> n)) return 0;

    auto ask = [&](int i, int j)->int {
        cout << "? " << i << " " << j << "\n";
        cout.flush();
        int x;
        if (!(cin >> x)) exit(0);
        if (x == -1) exit(0);
        return x;
    };

    auto finish = [&](const vector<int>& p) {
        cout << "! ";
        for (int i = 1; i <= (int)p.size()-1; ++i) {
            cout << p[i] << (i + 1 <= (int)p.size()-1 ? ' ' : '\n');
        }
        cout.flush();
        exit(0);
    };

    // Query budget (soft tracking to avoid exceeding 4269)
    int query_count = 0;
    const int LIMIT = 4269;
    auto safe_ask = [&](int i, int j)->int {
        if (query_count + 1 > LIMIT) {
            // If we ever risk exceeding budget, terminate.
            exit(0);
        }
        int res = ask(i, j);
        query_count++;
        return res;
    };

    // Start with a random index
    int start = uniform_int_distribution<int>(1, n)(rng);

    // First full sweep from start to find a good candidate (likely near zero)
    int candidate = start;
    int best_val = INT_MAX;

    vector<int> vals_from_start(n + 1, -1);
    for (int i = 1; i <= n; ++i) {
        if (i == start) continue;
        int val = safe_ask(start, i);
        vals_from_start[i] = val;
        if (val < best_val) {
            best_val = val;
            candidate = i;
        }
    }

    // Now try to verify/refine candidate using sampling
    int zero_idx = candidate;

    // For current candidate 'c', we will maintain sampled ORs: val_c[i] = OR(c, i).
    auto find_zero_with_sampling = [&](int c)->int {
        vector<int> val_c(n + 1, -1);
        vector<int> sampled_indices;
        sampled_indices.reserve(128);

        auto add_sample = [&](int idx) {
            if (idx == c) return;
            if (val_c[idx] != -1) return;
            int v = safe_ask(c, idx);
            val_c[idx] = v;
            sampled_indices.push_back(idx);
        };

        // Heuristic: prefill a few samples
        int initial_samples = min(n - 1, 32);
        for (int t = 0; t < initial_samples; ++t) {
            int idx;
            do {
                idx = uniform_int_distribution<int>(1, n)(rng);
            } while (idx == c || val_c[idx] != -1);
            add_sample(idx);
        }

        int ok_count = 0; // number of successful pair checks suggesting c is zero
        const int OK_TARGET = 25; // if many pairs match, accept c as zero

        // Try up to some iterations, but also preserve budget for reconstruction
        for (int iter = 0; iter < 200; ++iter) {
            // Ensure at least 2 samples
            if ((int)sampled_indices.size() < 2) {
                int idx;
                do {
                    idx = uniform_int_distribution<int>(1, n)(rng);
                } while (idx == c || val_c[idx] != -1);
                add_sample(idx);
                continue;
            }

            // Pick two sampled indices and test if OR(a,b) == (OR(c,a) | OR(c,b))
            int a = sampled_indices[uniform_int_distribution<int>(0, (int)sampled_indices.size()-1)(rng)];
            int b = sampled_indices[uniform_int_distribution<int>(0, (int)sampled_indices.size()-1)(rng)];
            if (a == b) continue;

            int va = val_c[a];
            int vb = val_c[b];
            int vab = safe_ask(a, b);

            if ((va | vb) != vab) {
                // c is not zero. Improve candidate by finding index with minimal OR(c, *)
                int newc = c;
                int newbest = INT_MAX;

                // Use current samples
                for (int idx : sampled_indices) {
                    if (val_c[idx] < newbest) {
                        newbest = val_c[idx];
                        newc = idx;
                    }
                }

                // Probe a few more to refine
                int extra = min(24, n - 1 - (int)sampled_indices.size());
                for (int t = 0; t < extra; ++t) {
                    int idx;
                    do {
                        idx = uniform_int_distribution<int>(1, n)(rng);
                    } while (idx == c || val_c[idx] != -1);
                    add_sample(idx);
                    if (val_c[idx] < newbest) {
                        newbest = val_c[idx];
                        newc = idx;
                    }
                }

                // Move to new candidate
                c = newc;
                // Reset samples for new candidate
                fill(val_c.begin(), val_c.end(), -1);
                sampled_indices.clear();

                // Pre-sample a few for new candidate
                int pre = min(n - 1, 24);
                for (int t = 0; t < pre; ++t) {
                    int idx;
                    do {
                        idx = uniform_int_distribution<int>(1, n)(rng);
                    } while (idx == c || val_c[idx] != -1);
                    add_sample(idx);
                }

                ok_count = 0;
                // Check remaining budget to ensure we can reconstruct later
                int remaining_budget = LIMIT - query_count;
                int known = (int)sampled_indices.size();
                int needed_reconstruct = (n - 1) - known;
                if (remaining_budget <= needed_reconstruct) break;
                continue;
            } else {
                ok_count++;
                // If many successes, accept c as zero
                if (ok_count >= OK_TARGET) break;

                // Also keep sampling a bit to diversify pairs
                if ((int)sampled_indices.size() < 64) {
                    int idx;
                    do {
                        idx = uniform_int_distribution<int>(1, n)(rng);
                    } while (idx == c || val_c[idx] != -1);
                    add_sample(idx);
                }
            }

            // Ensure we have enough budget to reconstruct at some point
            int remaining_budget = LIMIT - query_count;
            int known = (int)sampled_indices.size();
            int needed_reconstruct = (n - 1) - known;
            if (remaining_budget <= needed_reconstruct) break;
        }

        // Reconstruct using current candidate c
        vector<int> p(n + 1, -1);
        p[c] = 0;
        for (int i = 1; i <= n; ++i) {
            if (i == c) continue;
            int v = val_c[i];
            if (v == -1) v = safe_ask(c, i);
            p[i] = v;
        }
        finish(p);
        return c; // unreachable
    };

    // Try to confirm/refine and then reconstruct
    find_zero_with_sampling(candidate);

    return 0;
}