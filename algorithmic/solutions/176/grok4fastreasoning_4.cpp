#include <bits/stdc++.h>
using namespace std;

int compute_satisfied(const vector<int>& assign, const vector<vector<int>>& clauses, int m) {
    int s = 0;
    for (int i = 0; i < m; i++) {
        const auto& cls = clauses[i];
        bool sat = false;
        for (int lit : cls) {
            int v = abs(lit);
            bool ltrue = (lit > 0 ? assign[v] : !assign[v]);
            if (ltrue) {
                sat = true;
                break;
            }
        }
        if (sat) s++;
    }
    return s;
}

int compute_delta(int x, const vector<int>& assign, const vector<vector<int>>& clauses, const vector<vector<int>>& var_clauses) {
    int delta = 0;
    bool curr_assign_x = assign[x];
    bool new_assign_x = !curr_assign_x;
    for (int cl_idx : var_clauses[x]) {
        const vector<int>& cls = clauses[cl_idx];
        // curr_sat
        bool curr_sat = false;
        for (int lit : cls) {
            int v = abs(lit);
            bool val = assign[v];
            bool ltrue = (lit > 0 ? val : !val);
            if (ltrue) {
                curr_sat = true;
                break;
            }
        }
        // new_sat
        bool new_sat = false;
        for (int lit : cls) {
            int v = abs(lit);
            bool ltrue;
            if (v == x) {
                ltrue = (lit > 0 ? new_assign_x : !new_assign_x);
            } else {
                bool val = assign[v];
                ltrue = (lit > 0 ? val : !val);
            }
            if (ltrue) {
                new_sat = true;
                break;
            }
        }
        if (curr_sat && !new_sat) delta--;
        else if (!curr_sat && new_sat) delta++;
    }
    return delta;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(0);
    int n, m;
    cin >> n >> m;
    vector<vector<int>> clauses(m, vector<int>(3));
    vector<vector<int>> var_clauses(n + 1);
    for (int i = 0; i < m; i++) {
        int a, b, c;
        cin >> a >> b >> c;
        clauses[i] = {a, b, c};
        int va = abs(a), vb = abs(b), vc = abs(c);
        var_clauses[va].push_back(i);
        var_clauses[vb].push_back(i);
        var_clauses[vc].push_back(i);
    }
    if (m == 0) {
        for (int i = 1; i <= n; i++) {
            cout << 0 << (i < n ? " " : "\n");
        }
        return 0;
    }
    srand(time(NULL));
    vector<int> best_assign(n + 1, 0);
    int best_s = -1;
    const int RESTARTS = 20;
    for (int r = 0; r < RESTARTS; r++) {
        vector<int> assign(n + 1, 0);
        for (int i = 1; i <= n; i++) {
            assign[i] = rand() % 2;
        }
        bool changed = true;
        while (changed) {
            changed = false;
            int best_delta = 0;
            int best_x = -1;
            for (int x = 1; x <= n; x++) {
                int delta = compute_delta(x, assign, clauses, var_clauses);
                if (delta > best_delta) {
                    best_delta = delta;
                    best_x = x;
                }
            }
            if (best_delta > 0) {
                assign[best_x] = 1 - assign[best_x];
                changed = true;
            }
        }
        int s = compute_satisfied(assign, clauses, m);
        if (s > best_s) {
            best_s = s;
            best_assign = assign;
        }
    }
    for (int i = 1; i <= n; i++) {
        cout << best_assign[i];
        if (i < n) cout << " ";
        else cout << "\n";
    }
    return 0;
}