#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int n, m;
    if (!(cin >> n >> m)) return 0;
    int E = n + 1;
    vector<vector<int>> a(n + 2);
    for (int i = 1; i <= n; ++i) {
        a[i].reserve(m);
        for (int j = 0; j < m; ++j) {
            int x; cin >> x;
            a[i].push_back(x);
        }
    }
    a[E] = vector<int>(); a[E].reserve(m);
    
    vector<pair<int,int>> ops;
    ops.reserve(2000000);
    auto move_ball = [&](int x, int y) {
        // Precondition: x != y, a[x] not empty, a[y].size() < m
        int v = a[x].back();
        a[x].pop_back();
        a[y].push_back(v);
        ops.emplace_back(x, y);
    };
    
    vector<int> solved(n + 2, 0);
    for (int iter = 0; iter < n; ++iter) {
        int t = -1;
        for (int i = 1; i <= n; ++i) {
            if (!solved[i]) { t = i; break; }
        }
        if (t == -1) break;
        if (a[t].empty()) { solved[t] = 1; continue; }
        int c = a[t].back();
        
        for (int s = 1; s <= n; ++s) {
            if (s == t) continue;
            // count occurrences of c in stack s
            int k = 0;
            for (int v : a[s]) if (v == c) ++k;
            if (k == 0) continue;
            
            // Extract k occurrences
            for (int rep = 0; rep < k; ++rep) {
                // Move from s to E until top is c
                while (!a[s].empty() && a[s].back() != c) {
                    // E must have space
                    if ((int)a[E].size() >= m) {
                        // Should not happen by construction
                        // But to be safe, we can move one from E back to s (which should have space since we're popping)
                        // However at this point, s is full before popping; avoid undefined behavior
                        // As per algorithm, this situation shouldn't arise.
                    }
                    move_ball(s, E);
                }
                // Now top of s is c
                if ((int)a[t].size() == m) {
                    // Free space on t
                    move_ball(t, E);
                }
                move_ball(s, t);
            }
            // Refill s from E
            while ((int)a[s].size() < m) {
                move_ball(E, s);
            }
        }
        // Now t is full of color c
        solved[t] = 1;
    }
    
    cout << ops.size() << '\n';
    for (auto &p : ops) {
        cout << p.first << ' ' << p.second << '\n';
    }
    return 0;
}