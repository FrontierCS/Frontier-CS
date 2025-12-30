#include <bits/stdc++.h>
using namespace std;

using ll = long long;

struct Solution {
    vector<vector<int>> seq; // per machine job order
    ll makespan = (ll)4e18;
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int J, M;
    if (!(cin >> J >> M)) {
        return 0;
    }

    vector<vector<int>> route(J, vector<int>(M));
    vector<vector<ll>> proc(J, vector<ll>(M));

    for (int j = 0; j < J; ++j) {
        for (int k = 0; k < M; ++k) {
            int m; ll p;
            cin >> m >> p;
            route[j][k] = m;
            proc[j][k] = p;
        }
    }

    // Precompute job total processing and machine total processing
    vector<ll> jobSum(J, 0);
    vector<ll> machineSum(M, 0);
    for (int j = 0; j < J; ++j) {
        for (int k = 0; k < M; ++k) {
            jobSum[j] += proc[j][k];
            machineSum[route[j][k]] += proc[j][k];
        }
    }

    // Position of machine within job's route (for potential future use)
    vector<vector<int>> pos(J, vector<int>(M, -1));
    for (int j = 0; j < J; ++j) {
        for (int k = 0; k < M; ++k) {
            pos[j][route[j][k]] = k;
        }
    }

    // RNG
    uint64_t seed = chrono::steady_clock::now().time_since_epoch().count()
                    ^ (uint64_t)(J * 10007 + M * 1009);
    std::mt19937_64 rng(seed);
    auto randu = [&]() -> double {
        return std::uniform_real_distribution<double>(0.0, 1.0)(rng);
    };
    auto randint = [&](int l, int r) -> int {
        return std::uniform_int_distribution<int>(l, r)(rng);
    };

    // GT scheduler with various rules and epsilon-greedy randomness
    auto run_GT = [&](int rule, double epsRand) -> Solution {
        const ll INF = (ll)4e18;
        vector<int> idx(J, 0);
        vector<ll> rj(J, 0), avail(M, 0);
        vector<ll> remInc = jobSum; // remaining work including current operation
        vector<vector<int>> seq(M);
        for (int m = 0; m < M; ++m) seq[m].reserve(J);

        ll maxC = 0;
        int totalOps = J * M;
        vector<ll> s_cache(J), c_cache(J); // to avoid recomputation for candidate m*
        while (totalOps > 0) {
            // Step 1: compute earliest completion times for each job's next op
            ll best_c = INF, best_s = INF;
            int j0 = -1, mstar = -1;
            for (int j = 0; j < J; ++j) if (idx[j] < M) {
                int m = route[j][idx[j]];
                ll p = proc[j][idx[j]];
                ll s = rj[j] > avail[m] ? rj[j] : avail[m];
                ll c = s + p;
                s_cache[j] = s;
                c_cache[j] = c;
                if (c < best_c || (c == best_c && (s < best_s || (s == best_s && randint(0,1)==0)))) {
                    best_c = c; best_s = s; j0 = j; mstar = m;
                }
            }

            // Step 2: build conflict set on mstar
            vector<int> K;
            K.reserve(J);
            for (int j = 0; j < J; ++j) if (idx[j] < M && route[j][idx[j]] == mstar) {
                ll s = s_cache[j];
                if (s < best_c) {
                    K.push_back(j);
                }
            }
            if (K.empty()) {
                // Should not happen, but fallback: schedule j0
                K.push_back(j0);
            }

            int choose = -1;
            if (randu() < epsRand) {
                choose = K[randint(0, (int)K.size()-1)];
            } else {
                // Select according to rule
                double best_val = 0.0;
                bool first = true;
                for (int j : K) {
                    ll s = s_cache[j];
                    ll p = proc[j][idx[j]];
                    ll rem = remInc[j];
                    double val;
                    switch (rule) {
                        case 0: // MIN s
                            val = (double)s;
                            break;
                        case 1: // SPT
                            val = (double)p;
                            break;
                        case 2: // LPT
                            val = -(double)p;
                            break;
                        case 3: // MWKR max remaining work
                            val = -(double)rem;
                            break;
                        case 4: // LWR min remaining work
                            val = (double)rem;
                            break;
                        case 5: // Earliest completion time
                            val = (double)(s + p);
                            break;
                        case 6: // Weighted s and p
                            val = 0.7 * (double)s + 0.3 * (double)p;
                            break;
                        case 7: // Weighted s and remaining work
                            val = 0.5 * (double)s + 0.5 * (double)rem;
                            break;
                        case 8: // Bias to bottleneck relief (prefer large p on heavy machine)
                        {
                            double machineLoad = (double)machineSum[mstar];
                            val = - (double)p - 0.1 * machineLoad + 0.1 * (double)s;
                            break;
                        }
                        case 9: // Randomized tie-breaking around s and p
                            val = (double)s + (double)p * (0.2 + 0.3 * randu());
                            break;
                        default:
                            val = (double)(s + p);
                            break;
                    }
                    if (first || val < best_val || (val == best_val && randint(0,1)==0)) {
                        best_val = val;
                        choose = j;
                        first = false;
                    }
                }
            }

            // Step 3: schedule chosen job on mstar
            int j = choose;
            int m = route[j][idx[j]];
            ll p = proc[j][idx[j]];
            ll s = rj[j] > avail[m] ? rj[j] : avail[m];
            ll c = s + p;

            seq[m].push_back(j);
            rj[j] = c;
            avail[m] = c;
            remInc[j] -= p;
            idx[j]++;

            if (c > maxC) maxC = c;
            totalOps--;
        }

        Solution sol;
        sol.seq = move(seq);
        sol.makespan = maxC;
        return sol;
    };

    // Time budget
    auto time_start = chrono::steady_clock::now();
    auto elapsed_ms = [&]() -> double {
        auto now = chrono::steady_clock::now();
        return chrono::duration<double, std::milli>(now - time_start).count();
    };

    double timeLimitMs = 1800.0; // conservative
    // If input is small, we can allow more time
    if (J * M <= 400) timeLimitMs = 1900.0;

    // Try a set of base rules first deterministically (epsRand = 0)
    vector<int> base_rules = {5, 0, 1, 2, 3, 4, 6, 7, 8, 9};
    Solution best;
    best.makespan = (ll)4e18;

    for (int r : base_rules) {
        Solution cur = run_GT(r, 0.0);
        if (cur.makespan < best.makespan) {
            best = move(cur);
        }
        if (elapsed_ms() > timeLimitMs) break;
    }

    // Randomized multi-start with epsilon-greedy
    while (elapsed_ms() < timeLimitMs) {
        int r = base_rules[randint(0, (int)base_rules.size()-1)];
        double eps = 0.02 + 0.18 * randu(); // between 0.02 and 0.20
        Solution cur = run_GT(r, eps);
        if (cur.makespan < best.makespan) {
            best = move(cur);
        }
    }

    // Output exactly M lines, each with J job indices in order
    for (int m = 0; m < M; ++m) {
        for (int i = 0; i < (int)best.seq[m].size(); ++i) {
            if (i) cout << ' ';
            cout << best.seq[m][i];
        }
        // In rare case due to unforeseen issues, pad missing jobs arbitrarily (shouldn't happen)
        if ((int)best.seq[m].size() < J) {
            vector<int> used(J, 0);
            for (int x : best.seq[m]) if (0 <= x && x < J) used[x] = 1;
            for (int j = 0; j < J; ++j) if (!used[j]) {
                if (!best.seq[m].empty() || i) cout << ' ';
                cout << j;
            }
        }
        cout << '\n';
    }

    return 0;
}