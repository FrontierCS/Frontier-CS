#include <bits/stdc++.h>
using namespace std;

int get_satisfied(const vector<vector<int>>& cls, const vector<int>& ass, int m, int n) {
    int cnt = 0;
    for (int i = 0; i < m; i++) {
        bool sat = false;
        for (int j = 0; j < 3; j++) {
            int l = cls[i][j];
            int v = abs(l);
            bool lit = (l > 0 ? (ass[v] == 1) : (ass[v] == 0));
            if (lit) {
                sat = true;
                break;
            }
        }
        if (sat) cnt++;
    }
    return cnt;
}

int main() {
    int n, m;
    cin >> n >> m;
    vector<vector<int>> cls(m, vector<int>(3));
    vector<vector<pair<int, int>>> var_clauses(n + 1);
    for (int i = 0; i < m; i++) {
        for (int j = 0; j < 3; j++) {
            cin >> cls[i][j];
        }
        for (int j = 0; j < 3; j++) {
            int l = cls[i][j];
            int v = abs(l);
            var_clauses[v].emplace_back(i, j);
        }
    }
    vector<int> best_ass(n + 1);
    int best_s = -1;
    mt19937 rng(42);
    for (int restart = 0; restart < 20; restart++) {
        vector<int> ass(n + 1, 0);
        for (int i = 1; i <= n; i++) {
            ass[i] = (rng() & 1);
        }
        int curr_s = get_satisfied(cls, ass, m, n);
        bool improved = true;
        while (improved) {
            improved = false;
            int best_delta = 0;
            int best_x = -1;
            for (int x = 1; x <= n; x++) {
                int delta = 0;
                for (auto [cl, pos] : var_clauses[x]) {
                    int l = cls[cl][pos];
                    bool curr_ass = (ass[x] == 1);
                    bool curr_lit = (l > 0 ? curr_ass : !curr_ass);
                    bool next_lit = (l > 0 ? !curr_ass : curr_ass);
                    int p1 = (pos + 1) % 3;
                    int p2 = (pos + 2) % 3;
                    int l1 = cls[cl][p1];
                    int v1 = abs(l1);
                    bool o1 = (l1 > 0 ? (ass[v1] == 1) : (ass[v1] == 0));
                    int l2 = cls[cl][p2];
                    int v2 = abs(l2);
                    bool o2 = (l2 > 0 ? (ass[v2] == 1) : (ass[v2] == 0));
                    bool other_sat = o1 || o2;
                    bool curr_sat = curr_lit || other_sat;
                    bool next_sat = next_lit || other_sat;
                    if (curr_sat && !next_sat) delta--;
                    if (!curr_sat && next_sat) delta++;
                }
                if (delta > best_delta) {
                    best_delta = delta;
                    best_x = x;
                }
            }
            if (best_delta > 0) {
                ass[best_x] = 1 - ass[best_x];
                curr_s += best_delta;
                improved = true;
            }
        }
        if (curr_s > best_s) {
            best_s = curr_s;
            best_ass = ass;
        }
    }
    for (int i = 1; i <= n; i++) {
        cout << best_ass[i];
        if (i < n) cout << " ";
        else cout << endl;
    }
    return 0;
}