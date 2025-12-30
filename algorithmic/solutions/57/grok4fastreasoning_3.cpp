#include <bits/stdc++.h>
using namespace std;

int main() {
    int t;
    cin >> t;
    for (int test = 0; test < t; test++) {
        int n;
        cin >> n;
        vector<vector<int>> adj(n + 1);
        for (int i = 0; i < n - 1; i++) {
            int u, v;
            cin >> u >> v;
            adj[u].push_back(v);
            adj[v].push_back(u);
        }
        vector<int> s(n + 1);
        for (int u = 1; u <= n; u++) {
            cout << "? 1 1 " << u << endl;
            fflush(stdout);
            cin >> s[u];
        }
        vector<int> cands;
        for (int u = 1; u <= n; u++) {
            if (abs(s[u]) == 1) cands.push_back(u);
        }
        int m = cands.size();
        vector<vector<int>> As(m, vector<int>(n + 1, 0));
        for (int i = 0; i < m; i++) {
            int r = cands[i];
            vector<int> par(n + 1, 0);
            vector<int> aa(n + 1, 0);
            queue<int> q;
            q.push(r);
            par[r] = -1;
            aa[r] = s[r];
            vector<bool> vis(n + 1, false);
            vis[r] = true;
            while (!q.empty()) {
                int p = q.front();
                q.pop();
                for (int nei : adj[p]) {
                    if (!vis[nei]) {
                        vis[nei] = true;
                        par[nei] = p;
                        aa[nei] = s[nei] - s[p];
                        q.push(nei);
                    }
                }
            }
            As[i] = aa;
        }
        bool all_same = (m <= 1);
        if (m > 1) {
            all_same = true;
            for (int i = 1; i < m && all_same; i++) {
                bool eq = true;
                for (int v = 1; v <= n; v++) {
                    if (As[i][v] != As[0][v]) {
                        eq = false;
                        break;
                    }
                }
                if (!eq) all_same = false;
            }
        }
        vector<int> toggle_count(n + 1, 0);
        if (all_same) {
            cout << "!";
            for (int v = 1; v <= n; v++) {
                int val = (m == 0 ? 1 : As[0][v]);  // fallback, though m!=0
                cout << " " << val;
            }
            cout << endl;
            fflush(stdout);
            continue;
        }
        vector<int> current(m);
        for (int i = 0; i < m; i++) current[i] = i;
        while (current.size() > 1) {
            int l = current.size();
            int best_x = -1;
            int best_min = -1;
            double best_balance = 1e9;
            for (int xx = 1; xx <= n; xx++) {
                int p1 = 0;
                for (int j : current) {
                    if (As[j][xx] == 1) p1++;
                }
                int mm = min(p1, l - p1);
                double balance = abs(p1 - 0.5 * l);
                if (mm > best_min || (mm == best_min && balance < best_balance)) {
                    best_min = mm;
                    best_balance = balance;
                    best_x = xx;
                }
            }
            // verify best_x
            cout << "? 1 1 " << best_x << endl;
            fflush(stdout);
            int curr_old;
            cin >> curr_old;
            cout << "? 2 " << best_x << endl;
            fflush(stdout);
            toggle_count[best_x]++;
            cout << "? 1 1 " << best_x << endl;
            fflush(stdout);
            int newf;
            cin >> newf;
            int current_a = (curr_old - newf) / 2;
            int prev_t = toggle_count[best_x] - 1;
            int sign = (prev_t % 2 == 0 ? 1 : -1);
            vector<int> new_current;
            for (int j : current) {
                int predicted_current = As[j][best_x] * sign;
                if (predicted_current == current_a) {
                    new_current.push_back(j);
                }
            }
            current = new_current;
        }
        int the_i = current[0];
        cout << "!";
        for (int v = 1; v <= n; v++) {
            int val = As[the_i][v];
            int t = toggle_count[v] % 2;
            if (t == 1) val = -val;
            cout << " " << val;
        }
        cout << endl;
        fflush(stdout);
    }
    return 0;
}