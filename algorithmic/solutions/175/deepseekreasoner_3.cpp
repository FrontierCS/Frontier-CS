#include <iostream>
#include <vector>
#include <algorithm>
#include <numeric>
#include <random>
#include <ctime>
#include <cstdlib>

using namespace std;

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(nullptr);
    cout.tie(nullptr);

    int n, m;
    cin >> n >> m;

    if (m == 0) {
        for (int i = 0; i < n; ++i) {
            cout << "0 ";
        }
        cout << endl;
        return 0;
    }

    vector<vector<int>> pos_clauses(n);
    vector<vector<int>> neg_clauses(n);
    vector<int> pos_count(n, 0), neg_count(n, 0);
    vector<array<int, 3>> clause_vars(m);
    vector<array<bool, 3>> clause_signs(m); // true = positive

    for (int i = 0; i < m; ++i) {
        int a, b, c;
        cin >> a >> b >> c;
        array<int, 3> lits = {a, b, c};
        for (int j = 0; j < 3; ++j) {
            int x = lits[j];
            int var = abs(x) - 1;
            bool sign = (x > 0);
            clause_vars[i][j] = var;
            clause_signs[i][j] = sign;
            if (sign) {
                pos_clauses[var].push_back(i);
                pos_count[var]++;
            } else {
                neg_clauses[var].push_back(i);
                neg_count[var]++;
            }
        }
    }

    // initial assignment: majority
    vector<bool> assignment(n);
    for (int i = 0; i < n; ++i) {
        assignment[i] = (pos_count[i] > neg_count[i]);
    }

    // compute true_count for each clause
    vector<char> true_count(m, 0);
    for (int i = 0; i < m; ++i) {
        for (int j = 0; j < 3; ++j) {
            int var = clause_vars[i][j];
            bool sign = clause_signs[i][j];
            if (assignment[var] == sign) {
                true_count[i]++;
            }
        }
    }

    // random generator
    mt19937 rng(time(nullptr));

    // local search
    const int MAX_PASSES = 20;
    bool flipped;
    for (int pass = 0; pass < MAX_PASSES; ++pass) {
        flipped = false;
        vector<int> order(n);
        iota(order.begin(), order.end(), 0);
        shuffle(order.begin(), order.end(), rng);

        for (int var : order) {
            int gain = 0;

            // positive occurrences
            for (int cl : pos_clauses[var]) {
                char old_true = true_count[cl];
                char new_true = old_true + (assignment[var] ? -1 : 1);
                bool old_sat = (old_true > 0);
                bool new_sat = (new_true > 0);
                if (new_sat && !old_sat) gain++;
                else if (!new_sat && old_sat) gain--;
            }

            // negative occurrences
            for (int cl : neg_clauses[var]) {
                char old_true = true_count[cl];
                char change = (assignment[var] == 0) ? -1 : 1;
                char new_true = old_true + change;
                bool old_sat = (old_true > 0);
                bool new_sat = (new_true > 0);
                if (new_sat && !old_sat) gain++;
                else if (!new_sat && old_sat) gain--;
            }

            if (gain > 0) {
                // flip variable
                assignment[var] = !assignment[var];

                // update true_count for positive clauses
                for (int cl : pos_clauses[var]) {
                    if (assignment[var]) {
                        true_count[cl]++;
                    } else {
                        true_count[cl]--;
                    }
                }
                // update true_count for negative clauses
                for (int cl : neg_clauses[var]) {
                    if (assignment[var]) {
                        true_count[cl]--;
                    } else {
                        true_count[cl]++;
                    }
                }
                flipped = true;
            }
        }
        if (!flipped) break;
    }

    // output
    for (int i = 0; i < n; ++i) {
        cout << (assignment[i] ? "1 " : "0 ");
    }
    cout << endl;

    return 0;
}