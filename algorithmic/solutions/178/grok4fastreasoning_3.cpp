#include <bits/stdc++.h>
using namespace std;

int compute_score(const vector<int>& ass, const vector<array<int,3>>& cls) {
    int ncl = cls.size();
    int s = 0;
    for (int i = 0; i < ncl; i++) {
        const auto& cl = cls[i];
        bool sat = false;
        for (int lit : cl) {
            int v = abs(lit);
            bool ltrue = (lit > 0 ? ass[v] == 1 : ass[v] == 0);
            if (ltrue) {
                sat = true;
                break;
            }
        }
        if (sat) s++;
    }
    return s;
}

pair<vector<int>, int> do_hill(vector<array<int,3>> clauses, const vector<vector<int>>& var_clauses, vector<int> start_ass) {
    vector<int> ass = start_ass;
    int cs = compute_score(ass, clauses);
    int nn = ass.size() - 1;
    bool changed = true;
    while (changed) {
        changed = false;
        vector<int> del(nn + 1, 0);
        for (int v = 1; v <= nn; v++) {
            int bef = 0;
            for (int ci : var_clauses[v]) {
                const auto& cl = clauses[ci];
                bool sat = false;
                for (int lit : cl) {
                    int vv = abs(lit);
                    bool ltrue = (lit > 0 ? ass[vv] == 1 : ass[vv] == 0);
                    if (ltrue) {
                        sat = true;
                        break;
                    }
                }
                if (sat) ++bef;
            }
            int old = ass[v];
            ass[v] = 1 - old;
            int aft = 0;
            for (int ci : var_clauses[v]) {
                const auto& cl = clauses[ci];
                bool sat = false;
                for (int lit : cl) {
                    int vv = abs(lit);
                    bool ltrue = (lit > 0 ? ass[vv] == 1 : ass[vv] == 0);
                    if (ltrue) {
                        sat = true;
                        break;
                    }
                }
                if (sat) ++aft;
            }
            ass[v] = old;
            del[v] = aft - bef;
        }
        int md = 0;
        int bv = -1;
        for (int v = 1; v <= nn; v++) {
            if (del[v] > md) {
                md = del[v];
                bv = v;
            }
        }
        if (md > 0) {
            ass[bv] = 1 - ass[bv];
            cs += md;
            changed = true;
        }
    }
    return {ass, cs};
}

int main() {
    srand(time(NULL));
    int n, m;
    cin >> n >> m;
    vector<array<int, 3>> clauses(m);
    for (int i = 0; i < m; i++) {
        int a, b, c;
        cin >> a >> b >> c;
        clauses[i] = {a, b, c};
    }
    vector<vector<int>> var_clauses(n + 1);
    for (int i = 0; i < m; i++) {
        for (int lit : clauses[i]) {
            int v = abs(lit);
            if (v >= 1 && v <= n) {
                var_clauses[v].push_back(i);
            }
        }
    }
    int best_s = -1;
    vector<int> best(n + 1);
    // all zero
    {
        vector<int> start(n + 1, 0);
        auto [ass, s] = do_hill(clauses, var_clauses, start);
        if (s > best_s) {
            best_s = s;
            best = ass;
        }
    }
    // all one
    {
        vector<int> start(n + 1, 1);
        auto [ass, s] = do_hill(clauses, var_clauses, start);
        if (s > best_s) {
            best_s = s;
            best = ass;
        }
    }
    // random
    for (int r = 0; r < 200; r++) {
        vector<int> start(n + 1);
        for (int i = 1; i <= n; i++) {
            start[i] = rand() % 2;
        }
        auto [ass, s] = do_hill(clauses, var_clauses, start);
        if (s > best_s) {
            best_s = s;
            best = ass;
        }
    }
    for (int i = 1; i <= n; i++) {
        if (i > 1) cout << " ";
        cout << best[i];
    }
    cout << endl;
    return 0;
}