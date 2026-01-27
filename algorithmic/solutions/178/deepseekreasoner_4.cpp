#include <iostream>
#include <vector>
#include <cstdlib>
#include <ctime>
#include <algorithm>
#include <utility>

using namespace std;

struct Clause {
    int var[3];
    bool sign[3]; // true means positive literal (variable), false means negative (¬variable)
};

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(nullptr);

    int n, m;
    cin >> n >> m;

    if (m == 0) {
        for (int i = 0; i < n; ++i) {
            cout << 0 << (i == n-1 ? '\n' : ' ');
        }
        return 0;
    }

    vector<Clause> clauses(m);
    vector<vector<pair<int, int>>> occ(n+1); // for each variable, list of (clause_index, literal_index)

    for (int i = 0; i < m; ++i) {
        int a, b, c;
        cin >> a >> b >> c;
        int literals[3] = {a, b, c};
        for (int j = 0; j < 3; ++j) {
            int lit = literals[j];
            int var = abs(lit);
            bool sign = (lit > 0);
            clauses[i].var[j] = var;
            clauses[i].sign[j] = sign;
            occ[var].push_back({i, j});
        }
    }

    srand(time(0));

    int best_satisfied = -1;
    vector<bool> best_assign(n+1, false);

    const int ITERATIONS = 1000;

    for (int iter = 0; iter < ITERATIONS; ++iter) {
        // random assignment
        vector<bool> assign(n+1);
        for (int v = 1; v <= n; ++v) {
            assign[v] = rand() % 2;
        }

        // clause_true_count[c] = number of true literals in clause c
        vector<int> clause_true_count(m, 0);
        for (int c = 0; c < m; ++c) {
            for (int j = 0; j < 3; ++j) {
                int var = clauses[c].var[j];
                bool sign = clauses[c].sign[j];
                if ((sign && assign[var]) || (!sign && !assign[var])) {
                    clause_true_count[c]++;
                }
            }
        }

        int satisfied = 0;
        for (int c = 0; c < m; ++c) {
            if (clause_true_count[c] > 0) satisfied++;
        }

        // hill climbing
        while (true) {
            int best_v = -1;
            int best_delta = 0;

            for (int v = 1; v <= n; ++v) {
                int delta = 0;
                for (const auto& p : occ[v]) {
                    int c = p.first;
                    int k = p.second;
                    bool literal_true = (clauses[c].sign[k] == assign[clauses[c].var[k]]); // var[k] is v
                    int old_count = clause_true_count[c];
                    int change = literal_true ? -1 : +1;
                    int new_count = old_count + change;
                    if (old_count == 0 && new_count > 0) delta++;
                    else if (old_count > 0 && new_count == 0) delta--;
                }
                if (delta > best_delta) {
                    best_delta = delta;
                    best_v = v;
                }
            }

            if (best_delta <= 0) break;

            // flip variable best_v
            bool old_val = assign[best_v];
            assign[best_v] = !old_val;
            for (const auto& p : occ[best_v]) {
                int c = p.first;
                int k = p.second;
                bool literal_was_true = (clauses[c].sign[k] == old_val);
                int change = literal_was_true ? -1 : +1;
                clause_true_count[c] += change;
            }
            satisfied += best_delta;

            if (satisfied == m) break; // all clauses satisfied, can stop this iteration
        }

        if (satisfied > best_satisfied) {
            best_satisfied = satisfied;
            best_assign = assign;
            if (satisfied == m) break; // optimal found, no need to continue iterations
        }
    }

    // output assignment
    for (int i = 1; i <= n; ++i) {
        cout << (best_assign[i] ? 1 : 0) << (i == n ? '\n' : ' ');
    }

    return 0;
}