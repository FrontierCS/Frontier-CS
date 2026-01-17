#include <bits/stdc++.h>
using namespace std;

int main() {
    int N;
    cin >> N;
    vector<vector<int>> adj(N + 1);
    for (int x = 1; x <= N; ++x) {
        set<int> remaining;
        for (int j = 1; j <= N; ++j) remaining.insert(N + j);
        vector<int> special;
        while (!remaining.empty()) {
            vector<int> B(remaining.begin(), remaining.end());
            int k = B.size();
            if (k == 0) break;
            cout << "Query " << (1 + k) << " " << x;
            for (int b : B) cout << " " << b;
            cout << endl;
            int dd;
            cin >> dd;
            int exp = k + 1;
            if (dd == exp) break;
            // find one
            vector<int> curr = B;
            while (curr.size() > 1) {
                int mid = curr.size() / 2;
                vector<int> half(curr.begin(), curr.begin() + mid);
                cout << "Query " << (1 + half.size()) << " " << x;
                for (int b : half) cout << " " << b;
                cout << endl;
                cin >> dd;
                exp = half.size() + 1;
                if (dd == exp) {
                    curr.assign(curr.begin() + mid, curr.end());
                } else {
                    curr = half;
                }
            }
            int cand = curr[0];
            cout << "Query 2 " << x << " " << cand << endl;
            cin >> dd;
            if (dd == 1) {
                special.push_back(cand);
                remaining.erase(cand);
            }
        }
        for (int yy : special) {
            int ry = yy - N;
            adj[x].push_back(ry);
        }
    }
    // bipartite matching
    int n = N;
    vector<vector<int>> g = adj;
    vector<int> pairU(n + 1, -1);
    vector<int> pairV(n + 1, -1);
    vector<bool> vis(n + 1);
    auto dfs = [&](auto&& self, int u) -> bool {
        for (int v : g[u]) {
            if (vis[v]) continue;
            vis[v] = true;
            if (pairV[v] == -1 || self(self, pairV[v])) {
                pairU[u] = v;
                pairV[v] = u;
                return true;
            }
        }
        return false;
    };
    int matching = 0;
    for (int u = 1; u <= n; ++u) {
        if (pairU[u] == -1) {
            fill(vis.begin(), vis.end(), false);
            if (dfs(dfs, u)) ++matching;
        }
    }
    vector<pair<int, int>> ans;
    for (int u = 1; u <= n; ++u) {
        int v = pairU[u];
        int yy = v + N;
        if (u < yy) ans.emplace_back(u, yy);
        else ans.emplace_back(yy, u);
    }
    for (auto [a, b] : ans) {
        cout << "Answer " << a << " " << b << endl;
    }
    return 0;
}