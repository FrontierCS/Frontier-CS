#include <iostream>
#include <vector>
#include <algorithm>
#include <random>
#include <tuple>
#include <ctime>
#include <cstdlib>

using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n, m;
    cin >> n >> m;

    // If no clauses, output any assignment (all false).
    if (m == 0) {
        for (int i = 0; i < n; ++i) {
            cout << "0 ";
        }
        cout << endl;
        return 0;
    }

    // Store each clause as three literals: (variable index, sign)
    // sign = 1 for positive, -1 for negative.
    vector<array<pair<int, int>, 3>> clauses(m);

    // For each variable, store distinct clauses where it appears,
    // along with counts of positive and negative occurrences.
    vector<vector<tuple<int, int, int>>> var_clauses(n);

    // Temporary structure to collect occurrences while reading.
    vector<vector<pair<int, int>>> temp_clauses_for_var(n);

    for (int i = 0; i < m; ++i) {
        int a, b, c;
        cin >> a >> b >> c;
        int lits[3] = {a, b, c};
        for (int j = 0; j < 3; ++j) {
            int lit = lits[j];
            int var = abs(lit) - 1;          // 0‑based index
            int sign = (lit > 0) ? 1 : -1;
            clauses[i][j] = {var, sign};
            temp_clauses_for_var[var].push_back({i, sign});
        }
    }

    // Convert the temporary lists into distinct clause information.
    for (int v = 0; v < n; ++v) {
        // Sort by clause index to group occurrences of the same clause.
        sort(temp_clauses_for_var[v].begin(), temp_clauses_for_var[v].end());
        int last_c = -1;
        int pos = 0, neg = 0;
        for (auto& occ : temp_clauses_for_var[v]) {
            int c = occ.first;
            int s = occ.second;
            if (c != last_c && last_c != -1) {
                var_clauses[v].emplace_back(last_c, pos, neg);
                pos = neg = 0;
            }
            if (s == 1) ++pos;
            else        ++neg;
            last_c = c;
        }
        if (last_c != -1) {
            var_clauses[v].emplace_back(last_c, pos, neg);
        }
    }

    // Random number generator.
    random_device rd;
    mt19937 rng(rd());
    uniform_int_distribution<int> rand_bit(0, 1);

    // Best solution found.
    vector<int> best_assignment(n, 0);
    int best_satisfied = 0;
    const int NUM_TRIALS = 100;   // can be adjusted

    for (int trial = 0; trial < NUM_TRIALS; ++trial) {
        // Random initial assignment.
        vector<int> assign(n);
        for (int i = 0; i < n; ++i) {
            assign[i] = rand_bit(rng);
        }

        // Compute initial true count for each clause.
        vector<int> true_count(m, 0);
        for (int i = 0; i < m; ++i) {
            for (int j = 0; j < 3; ++j) {
                int var = clauses[i][j].first;
                int sign = clauses[i][j].second;
                if ((sign == 1 && assign[var] == 1) ||
                    (sign == -1 && assign[var] == 0)) {
                    ++true_count[i];
                }
            }
        }

        // Count satisfied clauses.
        int satisfied = 0;
        for (int i = 0; i < m; ++i) {
            if (true_count[i] > 0) ++satisfied;
        }

        // Local improvement loop.
        bool improved;
        do {
            improved = false;
            // Random order of variables.
            vector<int> order(n);
            iota(order.begin(), order.end(), 0);
            shuffle(order.begin(), order.end(), rng);

            for (int v : order) {
                // Compute the change in satisfied clauses if we flip variable v.
                int delta = 0;
                // We'll also store the change per clause to apply later.
                vector<pair<int, int>> changes; // (clause index, delta_t)

                for (auto& tup : var_clauses[v]) {
                    int c = get<0>(tup);
                    int pos = get<1>(tup);
                    int neg = get<2>(tup);
                    int k = pos + neg;
                    int count_cur = (assign[v] == 1) ? pos : neg;
                    int t = true_count[c];
                    int delta_t = k - 2 * count_cur;
                    int new_t = t + delta_t;
                    bool old_sat = (t > 0);
                    bool new_sat = (new_t > 0);
                    delta += (new_sat - old_sat);
                    changes.emplace_back(c, delta_t);
                }

                if (delta > 0) {
                    // Flip variable v.
                    assign[v] = 1 - assign[v];
                    // Update true_count for all affected clauses.
                    for (auto& ch : changes) {
                        int c = ch.first;
                        int delta_t = ch.second;
                        true_count[c] += delta_t;
                    }
                    satisfied += delta;
                    improved = true;
                }
            }
        } while (improved);

        // Update best solution.
        if (satisfied > best_satisfied) {
            best_satisfied = satisfied;
            best_assignment = assign;
        }
    }

    // Output the best assignment.
    for (int i = 0; i < n; ++i) {
        cout << best_assignment[i] << " ";
    }
    cout << endl;

    return 0;
}