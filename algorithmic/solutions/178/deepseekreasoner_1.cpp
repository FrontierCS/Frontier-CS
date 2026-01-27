#include <bits/stdc++.h>
using namespace std;

struct Clause {
    int var[3];
    bool pos[3]; // true if variable appears positively
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n, m;
    cin >> n >> m;
    if (m == 0) {
        for (int i = 0; i < n; ++i) {
            cout << 0 << " \n"[i == n - 1];
        }
        return 0;
    }

    vector<Clause> clauses(m);
    for (int i = 0; i < m; ++i) {
        for (int j = 0; j < 3; ++j) {
            int lit;
            cin >> lit;
            clauses[i].var[j] = abs(lit) - 1;
            clauses[i].pos[j] = (lit > 0);
        }
    }

    random_device rd;
    mt19937 rng(rd());
    uniform_int_distribution<int> rand_bit(0, 1);

    vector<bool> best_assign(n);
    int best_sat = -1;
    const int NUM_RESTARTS = 1000;

    for (int restart = 0; restart < NUM_RESTARTS; ++restart) {
        vector<bool> assign(n);
        for (int i = 0; i < n; ++i) {
            assign[i] = rand_bit(rng);
        }

        int total_sat = 0;
        for (const auto& cl : clauses) {
            bool sat = false;
            for (int j = 0; j < 3; ++j) {
                if (assign[cl.var[j]] == cl.pos[j]) {
                    sat = true;
                    break;
                }
            }
            if (sat) total_sat++;
        }

        while (true) {
            vector<int> delta(n, 0);
            for (const auto& cl : clauses) {
                bool a[3];
                for (int j = 0; j < 3; ++j) {
                    a[j] = (assign[cl.var[j]] == cl.pos[j]);
                }
                bool cur = a[0] || a[1] || a[2];
                for (int j = 0; j < 3; ++j) {
                    bool new_cur;
                    if (j == 0)      new_cur = (!a[0]) || a[1] || a[2];
                    else if (j == 1) new_cur = a[0] || (!a[1]) || a[2];
                    else             new_cur = a[0] || a[1] || (!a[2]);
                    int change = (new_cur ? 1 : 0) - (cur ? 1 : 0);
                    delta[cl.var[j]] += change;
                }
            }

            int best_var = -1;
            int best_delta = 0;
            for (int i = 0; i < n; ++i) {
                if (delta[i] > best_delta) {
                    best_delta = delta[i];
                    best_var = i;
                }
            }

            if (best_var == -1) break;

            assign[best_var] = !assign[best_var];
            total_sat += best_delta;
            if (total_sat == m) break;
        }

        if (total_sat > best_sat) {
            best_sat = total_sat;
            best_assign = assign;
            if (best_sat == m) break;
        }
    }

    for (int i = 0; i < n; ++i) {
        cout << (best_assign[i] ? 1 : 0) << " \n"[i == n - 1];
    }

    return 0;
}