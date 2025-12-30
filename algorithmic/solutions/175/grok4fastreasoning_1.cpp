#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(NULL);
    int n, m;
    cin >> n >> m;
    if (m == 0) {
        for (int i = 1; i <= n; ++i) {
            cout << (i == 1 ? "" : " ") << 0;
        }
        cout << '\n';
        return 0;
    }
    vector<vector<int>> clauses(m, vector<int>(3));
    for (int i = 0; i < m; ++i) {
        for (int j = 0; j < 3; ++j) {
            cin >> clauses[i][j];
        }
    }
    mt19937 rng(random_device{}());
    vector<int> best_assign(n + 1);
    double best_score = -1.0;
    vector<int> assignment(n + 1);
    for (int restart = 0; restart < 10; ++restart) {
        for (int i = 1; i <= n; ++i) {
            assignment[i] = rng() % 2;
        }
        // Local search
        int steps = 0;
        const int MAX_STEPS = 5000;
        const int MAX_ATT = 1000;
        while (steps < MAX_STEPS) {
            int att = 0;
            int cidx = -1;
            while (att < MAX_ATT) {
                int idx = rng() % m;
                bool sat = false;
                const auto& cls = clauses[idx];
                for (int j = 0; j < 3; ++j) {
                    int l = cls[j];
                    int v = abs(l);
                    bool lit = (l > 0) ? (assignment[v] == 1) : (assignment[v] == 0);
                    if (lit) {
                        sat = true;
                        break;
                    }
                }
                if (!sat) {
                    cidx = idx;
                    break;
                }
                ++att;
            }
            if (cidx == -1) break;
            int j = rng() % 3;
            int l = clauses[cidx][j];
            int v = abs(l);
            assignment[v] = 1 - assignment[v];
            ++steps;
        }
        // Compute score
        int sat_count = 0;
        for (int i = 0; i < m; ++i) {
            bool sat = false;
            const auto& cls = clauses[i];
            for (int j = 0; j < 3; ++j) {
                int l = cls[j];
                int v = abs(l);
                bool lit = (l > 0) ? (assignment[v] == 1) : (assignment[v] == 0);
                if (lit) {
                    sat = true;
                    break;
                }
            }
            if (sat) ++sat_count;
        }
        double score = static_cast<double>(sat_count) / m;
        if (score > best_score) {
            best_score = score;
            best_assign = assignment;
        }
    }
    for (int i = 1; i <= n; ++i) {
        cout << (i == 1 ? "" : " ") << best_assign[i];
    }
    cout << '\n';
    return 0;
}