#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(NULL);
    srand(time(NULL));
    int n, m;
    cin >> n >> m;
    vector<pair<int, int>> clauses(m);
    for (int i = 0; i < m; i++) {
        int a, b;
        cin >> a >> b;
        clauses[i] = {a, b};
    }
    auto compute_satisfied = [&](const vector<int>& assign) -> int {
        int cnt = 0;
        for (auto [a, b] : clauses) {
            int v1 = abs(a);
            int val_l1 = (a > 0 ? assign[v1] : 1 - assign[v1]);
            int v2 = abs(b);
            int val_l2 = (b > 0 ? assign[v2] : 1 - assign[v2]);
            if (val_l1 || val_l2) cnt++;
        }
        return cnt;
    };
    auto hill_climb = [&](vector<int> assign) -> pair<int, vector<int>> {
        int current_sat = compute_satisfied(assign);
        int max_iter = n * 10;
        int iter = 0;
        while (iter < max_iter) {
            vector<int> gain(n + 1, 0);
            for (auto [aa, bb] : clauses) {
                int a = aa, b = bb;
                int v1 = abs(a);
                bool pos1 = a > 0;
                int val_l1 = pos1 ? assign[v1] : 1 - assign[v1];
                int v2 = abs(b);
                bool pos2 = b > 0;
                int val_l2 = pos2 ? assign[v2] : 1 - assign[v2];
                if (v1 != v2) {
                    if (val_l1 == 0 && val_l2 == 0) {
                        gain[v1]++;
                        gain[v2]++;
                    } else if (val_l1 == 1 && val_l2 == 0) {
                        gain[v1]--;
                    } else if (val_l1 == 0 && val_l2 == 1) {
                        gain[v2]--;
                    }
                } else {
                    if (val_l1 == 0 && val_l2 == 0) {
                        gain[v1]++;
                    } else if (val_l1 == 1 && val_l2 == 1) {
                        gain[v1]--;
                    }
                }
            }
            int maxg = -1;
            int bestvar = -1;
            for (int i = 1; i <= n; i++) {
                if (gain[i] > maxg) {
                    maxg = gain[i];
                    bestvar = i;
                }
            }
            if (maxg <= 0) break;
            assign[bestvar] = 1 - assign[bestvar];
            current_sat += maxg;
            iter++;
        }
        return {current_sat, assign};
    };
    int best_score = (m == 0 ? 0 : -1);
    vector<int> best_assign(n + 1, 0);
    const int num_restarts = 5;
    for (int r = 0; r < num_restarts; r++) {
        vector<int> assign(n + 1, 0);
        for (int i = 1; i <= n; i++) {
            assign[i] = rand() % 2;
        }
        auto [score, ass] = hill_climb(assign);
        if (score > best_score) {
            best_score = score;
            best_assign = ass;
        }
    }
    {
        vector<int> assign(n + 1, 0);
        auto [score, ass] = hill_climb(assign);
        if (score > best_score) {
            best_score = score;
            best_assign = ass;
        }
    }
    {
        vector<int> assign(n + 1, 1);
        auto [score, ass] = hill_climb(assign);
        if (score > best_score) {
            best_score = score;
            best_assign = ass;
        }
    }
    for (int i = 1; i <= n; i++) {
        cout << best_assign[i];
        if (i < n) cout << " ";
        else cout << "\n";
    }
    return 0;
}