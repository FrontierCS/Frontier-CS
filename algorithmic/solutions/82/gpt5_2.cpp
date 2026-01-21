#include <bits/stdc++.h>
using namespace std;

static const int MAXN = 2050;

int n;
long long query_count = 0;

int ask(int i, int j) {
    if (i == j) return -1;
    cout << "? " << i << " " << j << "\n";
    cout.flush();
    int x;
    if (!(cin >> x)) exit(0);
    if (x == -1) exit(0);
    query_count++;
    return x;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    if (!(cin >> n)) return 0;

    // Use 1-indexed arrays
    vector<vector<int>> cache(n + 1, vector<int>(n + 1, -2));
    auto ask_cached = [&](int i, int j)->int {
        if (i == j) return -1;
        int a = i, b = j;
        if (a > b) swap(a, b);
        if (cache[a][b] != -2) return cache[a][b];
        int res = ask(a, b);
        cache[a][b] = res;
        return res;
    };

    // Determine number of bits L (ceil log2 n)
    int L = 0;
    while ((1 << L) < n) L++;

    // Step 1: choose pivot s with small estimated popcount using sampling
    std::mt19937 rng((uint32_t)chrono::high_resolution_clock::now().time_since_epoch().count());
    int best_s = 1;
    int best_est_pop = INT_MAX;
    int tries = min(n, 12);     // number of attempts to find good s
    int samples = 10;           // queries per attempt for estimation

    vector<int> all_idx(n);
    iota(all_idx.begin(), all_idx.end(), 1);

    for (int it = 0; it < tries; ++it) {
        int s = uniform_int_distribution<int>(1, n)(rng);
        // Sample 'samples' distinct indices (not equal to s)
        int cnt = 0;
        int est_mask = (1 << L) - 1;
        unordered_set<int> used;
        used.insert(s);
        while (cnt < samples) {
            int j = uniform_int_distribution<int>(1, n)(rng);
            if (used.insert(j).second) {
                int r = ask_cached(s, j);
                est_mask &= r;
                cnt++;
            }
        }
        int est_pop = __builtin_popcount((unsigned)est_mask);
        if (est_pop < best_est_pop) {
            best_est_pop = est_pop;
            best_s = s;
        }
        if (best_est_pop <= 5) break;
    }

    int s = best_s;

    // Step 2: query OR(s, i) for all i != s and compute p_s exactly
    vector<int> r(n + 1, -1);
    for (int i = 1; i <= n; ++i) {
        if (i == s) continue;
        int val = ask_cached(s, i);
        r[i] = val;
    }
    int ps = (1 << L) - 1;
    for (int i = 1; i <= n; ++i) {
        if (i == s) continue;
        ps &= r[i];
    }

    vector<int> ans(n + 1, -1);

    // If s is zero, we are done
    if (ps == 0) {
        ans[s] = 0;
        for (int i = 1; i <= n; ++i) {
            if (i == s) continue;
            ans[i] = r[i];
        }
        cout << "! ";
        for (int i = 1; i <= n; ++i) {
            cout << ans[i] << (i == n ? '\n' : ' ');
        }
        cout.flush();
        return 0;
    }

    // Build candidate set C: those i with r[i] == ps (i.e., p_i subset of ps), zero is in C
    vector<int> C;
    for (int i = 1; i <= n; ++i) {
        if (i == s) continue;
        if (r[i] == ps) C.push_back(i);
    }

    // Choose t to reduce candidates: maximize bits outside ps
    auto out_bits_count = [&](int i)->int {
        int out = r[i] & (~ps);
        return __builtin_popcount((unsigned)out);
    };

    vector<char> usedT(n + 1, 0);
    int M = ps;

    // While more than one candidate, shrink using different t's
    int safety_iter = 3 * L + 10; // safety cap
    while ((int)C.size() > 1 && safety_iter-- > 0) {
        int best_t = -1;
        int best_out = -1;
        for (int i = 1; i <= n; ++i) {
            if (i == s) continue;
            if (usedT[i]) continue;
            int ob = out_bits_count(i);
            if (ob > best_out) {
                best_out = ob;
                best_t = i;
            }
        }
        if (best_t == -1) {
            // fallback: pick any non-used t
            for (int i = 1; i <= n; ++i) {
                if (i == s) continue;
                if (!usedT[i]) { best_t = i; break; }
            }
            if (best_t == -1) break;
        }
        usedT[best_t] = 1;

        int minVal = INT_MAX;
        vector<int> vals(C.size());
        for (size_t idx = 0; idx < C.size(); ++idx) {
            int c = C[idx];
            int v = ask_cached(c, best_t);
            vals[idx] = v;
            if (v < minVal) minVal = v;
        }

        // minVal equals p_t (since OR(z, t) = p_t for zero z in C)
        int pt = minVal;
        M &= pt;

        // Filter candidates to those achieving minVal
        vector<int> newC;
        for (size_t idx = 0; idx < C.size(); ++idx) {
            if (vals[idx] == minVal) newC.push_back(C[idx]);
        }
        C.swap(newC);

        if (M == 0) break;
    }

    // After shrinking, if multiple left, perform a final deterministic pass using additional t's
    // Pick some additional t's to ensure intersection becomes 0 (if needed)
    if ((int)C.size() > 1) {
        // Try a few more different t's
        for (int extra = 0; extra < 3 * L && (int)C.size() > 1; ++extra) {
            int best_t = -1;
            int best_out = -1;
            for (int i = 1; i <= n; ++i) {
                if (i == s) continue;
                if (usedT[i]) continue;
                int ob = out_bits_count(i);
                if (ob > best_out) {
                    best_out = ob;
                    best_t = i;
                }
            }
            if (best_t == -1) break;
            usedT[best_t] = 1;

            int minVal = INT_MAX;
            vector<int> vals(C.size());
            for (size_t idx = 0; idx < C.size(); ++idx) {
                int c = C[idx];
                int v = ask_cached(c, best_t);
                vals[idx] = v;
                minVal = min(minVal, v);
            }
            vector<int> newC;
            for (size_t idx = 0; idx < C.size(); ++idx) {
                if (vals[idx] == minVal) newC.push_back(C[idx]);
            }
            C.swap(newC);
        }
    }

    int zero_idx;
    if ((int)C.size() >= 1) {
        zero_idx = C[0];
    } else {
        // Fallback if something went wrong: find zero by pairwise check with random t's
        zero_idx = s; // just to initialize
        for (int i = 1; i <= n; ++i) {
            if (i == s) continue;
            if (r[i] == ps) { zero_idx = i; break; }
        }
    }

    // Step 3: recover entire permutation via OR with zero index
    ans[zero_idx] = 0;
    for (int i = 1; i <= n; ++i) {
        if (i == zero_idx) continue;
        int v = ask_cached(i, zero_idx);
        ans[i] = v;
    }

    cout << "! ";
    for (int i = 1; i <= n; ++i) {
        cout << ans[i] << (i == n ? '\n' : ' ');
    }
    cout.flush();

    return 0;
}