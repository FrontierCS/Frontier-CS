#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n, m;
    cin >> n >> m;

    if (m == 0) {
        for (int i = 0; i < n; ++i)
            cout << "0 ";
        cout << endl;
        return 0;
    }

    vector<array<short, 3>> clauses(m);
    vector<int> pos_count(n + 1, 0), neg_count(n + 1, 0);
    vector<vector<pair<int, char>>> occ(n + 1); // (clause_id, sign)

    for (int j = 0; j < m; ++j) {
        int a, b, c;
        cin >> a >> b >> c;
        clauses[j] = {(short)a, (short)b, (short)c};
        for (int lit : {a, b, c}) {
            int var = abs(lit);
            char sign = (lit > 0 ? 1 : -1);
            occ[var].push_back({j, sign});
            if (sign == 1)
                pos_count[var]++;
            else
                neg_count[var]++;
        }
    }

    mt19937 rng(chrono::steady_clock::now().time_since_epoch().count());

    auto run_greedy = [&](vector<char>& assignment, mt19937& rng) -> int {
        int m = clauses.size();
        vector<char> true_count(m, 0);
        vector<char> satisfied(m, 0);

        // initial evaluation
        for (int j = 0; j < m; ++j) {
            char tc = 0;
            for (short lit : clauses[j]) {
                short var = abs(lit);
                char sign = (lit > 0 ? 1 : -1);
                if ((sign == 1 && assignment[var] == 1) ||
                    (sign == -1 && assignment[var] == 0))
                    tc++;
            }
            true_count[j] = tc;
            satisfied[j] = (tc > 0);
        }

        bool improved = true;
        int rounds = 0;
        const int MAX_ROUNDS = 20;
        while (improved && rounds < MAX_ROUNDS) {
            improved = false;
            vector<int> order(n);
            iota(order.begin(), order.end(), 1);
            shuffle(order.begin(), order.end(), rng);

            for (int i : order) {
                char old_val = assignment[i];
                int delta = 0;

                // compute delta for flipping variable i
                for (auto& p : occ[i]) {
                    int c = p.first;
                    char sign = p.second;
                    bool old_true = (sign == 1 && old_val == 1) ||
                                    (sign == -1 && old_val == 0);
                    char old_tc = true_count[c];
                    char delta_tc = old_true ? -1 : 1;
                    char new_tc = old_tc + delta_tc;
                    bool old_sat = (old_tc > 0);
                    bool new_sat = (new_tc > 0);
                    if (new_sat && !old_sat)
                        delta++;
                    else if (old_sat && !new_sat)
                        delta--;
                }

                if (delta > 0) {
                    improved = true;
                    assignment[i] = 1 - old_val;
                    // update true_count and satisfied for affected clauses
                    for (auto& p : occ[i]) {
                        int c = p.first;
                        char sign = p.second;
                        bool old_true = (sign == 1 && old_val == 1) ||
                                        (sign == -1 && old_val == 0);
                        char delta_tc = old_true ? -1 : 1;
                        true_count[c] += delta_tc;
                        satisfied[c] = (true_count[c] > 0);
                    }
                }
            }
            rounds++;
        }

        int sat = 0;
        for (int j = 0; j < m; ++j)
            sat += satisfied[j];
        return sat;
    };

    int best_sat = -1;
    vector<char> best_assignment(n + 1, 0);

    // deterministic start (majority vote)
    {
        vector<char> assignment(n + 1);
        for (int i = 1; i <= n; ++i)
            assignment[i] = (pos_count[i] >= neg_count[i] ? 1 : 0);
        int sat = run_greedy(assignment, rng);
        if (sat > best_sat) {
            best_sat = sat;
            best_assignment = assignment;
        }
    }

    // random restarts
    const int T = 4;
    uniform_int_distribution<int> rand_bit(0, 1);
    for (int t = 0; t < T; ++t) {
        vector<char> assignment(n + 1);
        for (int i = 1; i <= n; ++i)
            assignment[i] = rand_bit(rng);
        int sat = run_greedy(assignment, rng);
        if (sat > best_sat) {
            best_sat = sat;
            best_assignment = assignment;
        }
    }

    for (int i = 1; i <= n; ++i)
        cout << (int)best_assignment[i] << " ";
    cout << endl;

    return 0;
}