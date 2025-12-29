#include <cstdio>
#include <vector>
#include <array>
#include <algorithm>
#include <random>

using namespace std;

struct Solver {
    int n, m;
    vector<array<int, 3>> clauses;
    vector<int> sat;
    vector<int> assign;
    vector<int> crit_false, crit_true, gain;
    vector<vector<pair<int, int>>> occ; // for each variable: list of (clause_id, position)

    void read() {
        scanf("%d %d", &n, &m);
        clauses.resize(m);
        for (int i = 0; i < m; ++i) {
            int a, b, c;
            scanf("%d %d %d", &a, &b, &c);
            clauses[i] = {a, b, c};
        }
    }

    void init_random(mt19937& rng) {
        assign.assign(n + 1, 0);
        for (int v = 1; v <= n; ++v) {
            assign[v] = rng() % 2;
        }

        occ.assign(n + 1, {});
        for (int i = 0; i < m; ++i) {
            for (int j = 0; j < 3; ++j) {
                int lit = clauses[i][j];
                int var = abs(lit);
                occ[var].push_back({i, j});
            }
        }

        sat.assign(m, 0);
        for (int i = 0; i < m; ++i) {
            int cnt = 0;
            for (int j = 0; j < 3; ++j) {
                int lit = clauses[i][j];
                int var = abs(lit);
                bool sign = (lit > 0);
                if ((sign && assign[var]) || (!sign && !assign[var]))
                    cnt++;
            }
            sat[i] = cnt;
        }

        crit_false.assign(n + 1, 0);
        crit_true.assign(n + 1, 0);
        for (int i = 0; i < m; ++i) {
            if (sat[i] == 0) {
                for (int j = 0; j < 3; ++j) {
                    int var = abs(clauses[i][j]);
                    crit_false[var]++;
                }
            } else if (sat[i] == 1) {
                for (int j = 0; j < 3; ++j) {
                    int lit = clauses[i][j];
                    int var = abs(lit);
                    bool sign = (lit > 0);
                    if ((sign && assign[var]) || (!sign && !assign[var])) {
                        crit_true[var]++;
                        break;
                    }
                }
            }
        }

        gain.assign(n + 1, 0);
        for (int v = 1; v <= n; ++v) {
            gain[v] = crit_false[v] - crit_true[v];
        }
    }

    int compute_score() const {
        int s = 0;
        for (int i = 0; i < m; ++i)
            if (sat[i] > 0) s++;
        return s;
    }

    void solve(int iterations) {
        read();
        if (m == 0) {
            for (int i = 1; i <= n; ++i)
                printf("0 ");
            printf("\n");
            return;
        }

        int best_score = -1;
        vector<int> best_assign;

        for (int iter = 0; iter < iterations; ++iter) {
            mt19937 rng(iter + 12345);
            init_random(rng);

            bool flipped = true;
            vector<int> order(n);
            iota(order.begin(), order.end(), 1);

            while (flipped) {
                flipped = false;
                shuffle(order.begin(), order.end(), rng);

                for (int v : order) {
                    if (gain[v] > 0) {
                        flipped = true;
                        int old_val = assign[v];
                        int new_val = 1 - old_val;
                        assign[v] = new_val;

                        for (auto [cid, pos] : occ[v]) {
                            array<int, 3>& lits = clauses[cid];
                            int sc = sat[cid];

                            int vars[3];
                            bool old_true[3], new_true[3];
                            for (int k = 0; k < 3; ++k) {
                                vars[k] = abs(lits[k]);
                                bool sign = (lits[k] > 0);
                                if (vars[k] == v) {
                                    old_true[k] = (sign ? old_val : 1 - old_val);
                                    new_true[k] = (sign ? new_val : 1 - new_val);
                                } else {
                                    int val = assign[vars[k]];
                                    old_true[k] = new_true[k] = (sign ? val : 1 - val);
                                }
                            }

                            int old_true_idx = -1;
                            if (sc == 1) {
                                for (int k = 0; k < 3; ++k)
                                    if (old_true[k]) {
                                        old_true_idx = k;
                                        break;
                                    }
                            }

                            int new_sc = 0;
                            for (int k = 0; k < 3; ++k)
                                if (new_true[k]) new_sc++;
                            sat[cid] = new_sc;

                            // remove old critical contributions
                            if (sc == 0) {
                                for (int k = 0; k < 3; ++k)
                                    crit_false[vars[k]]--;
                            } else if (sc == 1) {
                                crit_true[vars[old_true_idx]]--;
                            }

                            // add new critical contributions
                            if (new_sc == 0) {
                                for (int k = 0; k < 3; ++k)
                                    crit_false[vars[k]]++;
                            } else if (new_sc == 1) {
                                int new_true_idx = -1;
                                for (int k = 0; k < 3; ++k)
                                    if (new_true[k]) {
                                        new_true_idx = k;
                                        break;
                                    }
                                crit_true[vars[new_true_idx]]++;
                            }
                        }

                        vector<bool> marked(n + 1, false);
                        marked[v] = true;
                        for (auto [cid, pos] : occ[v]) {
                            array<int, 3>& lits = clauses[cid];
                            for (int k = 0; k < 3; ++k)
                                marked[abs(lits[k])] = true;
                        }
                        for (int u = 1; u <= n; ++u) {
                            if (marked[u])
                                gain[u] = crit_false[u] - crit_true[u];
                        }
                    }
                }
            }

            int score = compute_score();
            if (score > best_score) {
                best_score = score;
                best_assign = assign;
            }
        }

        for (int i = 1; i <= n; ++i)
            printf("%d ", best_assign[i]);
        printf("\n");
    }
};

int main() {
    Solver solver;
    solver.solve(5);
    return 0;
}