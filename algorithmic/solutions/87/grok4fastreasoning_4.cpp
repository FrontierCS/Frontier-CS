#include <bits/stdc++.h>
using namespace std;

int main() {
    int n, m;
    cin >> n >> m;
    vector<int> initial(n + 1);
    for (int i = 1; i <= n; i++) cin >> initial[i];
    vector<int> goal(n + 1);
    for (int i = 1; i <= n; i++) cin >> goal[i];
    vector<vector<int>> adj(n + 1);
    for (int i = 0; i < m; i++) {
        int u, v;
        cin >> u >> v;
        adj[u].push_back(v);
        adj[v].push_back(u);
    }
    vector<vector<int>> lev(2, vector<int>(n + 1, -1));
    vector<vector<int>> par(2, vector<int>(n + 1, -1));
    for (int c = 0; c < 2; c++) {
        queue<int> qq;
        for (int v = 1; v <= n; v++) {
            if (initial[v] == c) {
                lev[c][v] = 0;
                par[c][v] = -1;
                qq.push(v);
            }
        }
        while (!qq.empty()) {
            int u = qq.front();
            qq.pop();
            for (int v : adj[u]) {
                if (lev[c][v] == -1) {
                    lev[c][v] = lev[c][u] + 1;
                    par[c][v] = u;
                    qq.push(v);
                }
            }
        }
    }
    vector<vector<int>> req(n + 1, vector<int>(101, -1));
    for (int c = 0; c < 2; c++) {
        vector<bool> mark(n + 1, false);
        for (int v = 1; v <= n; v++) {
            if (goal[v] == c) {
                int cur = v;
                while (cur != -1) {
                    mark[cur] = true;
                    if (lev[c][cur] == 0) break;
                    cur = par[c][cur];
                }
            }
        }
        for (int v = 1; v <= n; v++) {
            if (mark[v] && lev[c][v] > 0) {
                int s = lev[c][v];
                req[v][s] = c;
            }
        }
    }
    int max_t = 0;
    for (int v = 1; v <= n; v++) {
        int c = goal[v];
        max_t = max(max_t, lev[c][v]);
    }
    vector<vector<int>> states;
    vector<int> curr = initial;
    states.push_back(curr);
    for (int step = 1; step <= max_t; step++) {
        vector<int> next_state(n + 1);
        for (int v = 1; v <= n; v++) {
            int r = req[v][step];
            int choice;
            if (r != -1) {
                bool possible = (curr[v] == r);
                if (!possible) {
                    for (int nei : adj[v]) {
                        if (curr[nei] == r) {
                            possible = true;
                            break;
                        }
                    }
                }
                if (possible) {
                    choice = r;
                } else {
                    choice = curr[v];
                }
            } else {
                int tg = goal[v];
                bool possible = (curr[v] == tg);
                if (!possible) {
                    for (int nei : adj[v]) {
                        if (curr[nei] == tg) {
                            possible = true;
                            break;
                        }
                    }
                }
                if (possible) {
                    choice = tg;
                } else {
                    choice = curr[v];
                }
            }
            next_state[v] = choice;
        }
        curr = next_state;
        states.push_back(curr);
    }
    int k = max_t;
    cout << k << endl;
    for (auto& st : states) {
        for (int i = 1; i <= n; i++) {
            cout << st[i];
            if (i < n) cout << " ";
        }
        cout << endl;
    }
    return 0;
}