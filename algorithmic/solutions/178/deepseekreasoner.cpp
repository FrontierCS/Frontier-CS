#include <bits/stdc++.h>
using namespace std;

int n, m;
vector<array<int, 3>> clauses;

int compute_score(const vector<int>& assign) {
    int sat = 0;
    for (const auto& cl : clauses) {
        bool ok = false;
        for (int lit : cl) {
            int var = abs(lit);
            if (lit > 0 && assign[var] == 1) { ok = true; break; }
            if (lit < 0 && assign[var] == 0) { ok = true; break; }
        }
        if (ok) sat++;
    }
    return sat;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(0);
    srand(time(0));

    cin >> n >> m;
    clauses.resize(m);
    for (int i = 0; i < m; ++i) {
        cin >> clauses[i][0] >> clauses[i][1] >> clauses[i][2];
    }

    if (m == 0) {
        for (int i = 0; i < n; ++i) cout << "0 ";
        cout << endl;
        return 0;
    }

    vector<int> best_assign(n + 1);
    int best_score = -1;
    const int ITER = 100;

    for (int iter = 0; iter < ITER; ++iter) {
        vector<int> assign(n + 1);
        for (int i = 1; i <= n; ++i) assign[i] = rand() % 2;
        int score = compute_score(assign);
        bool improved = true;
        while (improved) {
            improved = false;
            for (int i = 1; i <= n; ++i) {
                assign[i] = 1 - assign[i];
                int new_score = compute_score(assign);
                if (new_score > score) {
                    score = new_score;
                    improved = true;
                } else {
                    assign[i] = 1 - assign[i];
                }
            }
        }
        if (score > best_score) {
            best_score = score;
            best_assign = assign;
        }
        if (best_score == m) break;
    }

    for (int i = 1; i <= n; ++i) {
        cout << best_assign[i] << (i == n ? "\n" : " ");
    }
    return 0;
}