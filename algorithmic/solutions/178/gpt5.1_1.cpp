#include <bits/stdc++.h>
using namespace std;

struct Clause {
    uint8_t v[3];
    bool neg[3];
};

static uint64_t rng_state = 88172645463325252ull;

static inline uint64_t xorshift64() {
    uint64_t x = rng_state;
    x ^= x << 7;
    x ^= x >> 9;
    return rng_state = x;
}

static inline int rand_int(int bound) {
    return (int)(xorshift64() % (uint64_t)bound);
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n, m;
    if (!(cin >> n >> m)) return 0;

    if (m == 0) {
        for (int i = 1; i <= n; ++i) {
            cout << 0;
            if (i < n) cout << ' ';
        }
        cout << '\n';
        return 0;
    }

    vector<Clause> clauses(m);
    vector<vector<int>> occurs(n + 1);

    for (int i = 0; i < m; ++i) {
        int a, b, c;
        cin >> a >> b >> c;
        int arr[3] = {a, b, c};
        for (int k = 0; k < 3; ++k) {
            int lit = arr[k];
            bool neg = false;
            int var;
            if (lit > 0) {
                var = lit;
                neg = false;
            } else {
                var = -lit;
                neg = true;
            }
            clauses[i].v[k] = (uint8_t)var;
            clauses[i].neg[k] = neg;
            occurs[var].push_back(i);
        }
    }

    uint64_t seed = chrono::high_resolution_clock::now().time_since_epoch().count();
    rng_state ^= seed | 1ull;

    vector<uint8_t> assign(n + 1), best_assign(n + 1);
    vector<char> clause_sat(m);

    auto eval_clause = [&](int idx) -> bool {
        const Clause &cl = clauses[idx];
        uint8_t v0 = cl.v[0];
        bool val0 = assign[v0];
        if (cl.neg[0]) val0 = !val0;
        if (val0) return true;

        uint8_t v1 = cl.v[1];
        bool val1 = assign[v1];
        if (cl.neg[1]) val1 = !val1;
        if (val1) return true;

        uint8_t v2 = cl.v[2];
        bool val2 = assign[v2];
        if (cl.neg[2]) val2 = !val2;
        if (val2) return true;

        return false;
    };

    auto eval_clause_if_flip = [&](int idx, int flipped_var) -> bool {
        const Clause &cl = clauses[idx];

        uint8_t v0 = cl.v[0];
        bool val0 = assign[v0];
        if (v0 == flipped_var) val0 = !val0;
        if (cl.neg[0]) val0 = !val0;
        if (val0) return true;

        uint8_t v1 = cl.v[1];
        bool val1 = assign[v1];
        if (v1 == flipped_var) val1 = !val1;
        if (cl.neg[1]) val1 = !val1;
        if (val1) return true;

        uint8_t v2 = cl.v[2];
        bool val2 = assign[v2];
        if (v2 == flipped_var) val2 = !val2;
        if (cl.neg[2]) val2 = !val2;
        if (val2) return true;

        return false;
    };

    int best_satisfied = -1;
    const int STEPS_PER_RESTART = 2000;
    const int NUM_RESTARTS = 15;
    bool found_all = false;

    for (int restart = 0; restart < NUM_RESTARTS && !found_all; ++restart) {
        for (int i = 1; i <= n; ++i) {
            assign[i] = (uint8_t)(rand_int(2));
        }

        int satisfied_count = 0;
        for (int i = 0; i < m; ++i) {
            bool sat = eval_clause(i);
            clause_sat[i] = sat ? 1 : 0;
            if (sat) ++satisfied_count;
        }
        if (satisfied_count > best_satisfied) {
            best_satisfied = satisfied_count;
            best_assign = assign;
            if (best_satisfied == m) {
                found_all = true;
                break;
            }
        }

        for (int step = 0; step < STEPS_PER_RESTART; ++step) {
            if (satisfied_count == m) {
                if (satisfied_count > best_satisfied) {
                    best_satisfied = satisfied_count;
                    best_assign = assign;
                }
                found_all = true;
                break;
            }

            int best_var = 1;
            int best_delta = INT_MIN;

            for (int v = 1; v <= n; ++v) {
                int delta = 0;
                const auto &ov = occurs[v];
                int sz = (int)ov.size();
                for (int p = 0; p < sz; ++p) {
                    int idx = ov[p];
                    bool was = clause_sat[idx];
                    bool now = eval_clause_if_flip(idx, v);
                    if (was) {
                        if (!now) --delta;
                    } else {
                        if (now) ++delta;
                    }
                }
                if (delta > best_delta) {
                    best_delta = delta;
                    best_var = v;
                } else if (delta == best_delta && rand_int(2) == 0) {
                    best_var = v;
                }
            }

            int chosen_var;
            if (best_delta > 0) {
                chosen_var = best_var;
            } else {
                if (rand_int(100) < 50) {
                    chosen_var = best_var;
                } else {
                    int chosen_clause = -1;
                    if (satisfied_count < m) {
                        for (int tries = 0; tries < 20; ++tries) {
                            int idx = rand_int(m);
                            if (!clause_sat[idx]) {
                                chosen_clause = idx;
                                break;
                            }
                        }
                    }
                    if (chosen_clause == -1) {
                        chosen_var = 1 + rand_int(n);
                    } else {
                        const Clause &cl = clauses[chosen_clause];
                        int lit_idx = rand_int(3);
                        chosen_var = cl.v[lit_idx];
                    }
                }
            }

            assign[chosen_var] ^= 1u;

            const auto &ov = occurs[chosen_var];
            int sz = (int)ov.size();
            for (int p = 0; p < sz; ++p) {
                int idx = ov[p];
                bool was = clause_sat[idx];
                bool now = eval_clause(idx);
                if (was != now) {
                    clause_sat[idx] = now ? 1 : 0;
                    if (now) ++satisfied_count;
                    else --satisfied_count;
                }
            }

            if (satisfied_count > best_satisfied) {
                best_satisfied = satisfied_count;
                best_assign = assign;
                if (best_satisfied == m) {
                    found_all = true;
                    break;
                }
            }
        }
    }

    for (int i = 1; i <= n; ++i) {
        cout << (int)best_assign[i];
        if (i < n) cout << ' ';
    }
    cout << '\n';
    return 0;
}