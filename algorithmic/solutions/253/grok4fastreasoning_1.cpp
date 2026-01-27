#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    int t;
    cin >> t;
    for (int test = 0; test < t; ++test) {
        int n, m;
        cin >> n >> m;
        vector<pair<int, int>> roads(m + 1);
        for (int i = 1; i <= m; ++i) {
            int a, b;
            cin >> a >> b;
            roads[i] = {a, b};
        }
        // Block all roads
        for (int i = 1; i <= m; ++i) {
            cout << "- " << i << endl;
        }
        // Find s
        int s = -1;
        for (int i = 1; i <= n; ++i) {
            cout << "? 1 " << i << endl;
            int ans;
            cin >> ans;
            if (ans == -1) return 0;
            if (ans == 1) {
                s = i;
            }
        }
        // Now s is found
        vector<bool> visited(n + 1, false);
        visited[s] = true;
        vector<bool> is_repaired(m + 1, false);
        vector<vector<int>> tree_adj(n + 1);
        bool changed = true;
        while (changed) {
            changed = false;
            vector<int> curr_unreached;
            for (int i = 1; i <= n; ++i) {
                if (!visited[i]) {
                    curr_unreached.push_back(i);
                }
            }
            for (int v : curr_unreached) {
                // Collect candidates
                vector<int> cands;
                for (int i = 1; i <= m; ++i) {
                    int x = roads[i].first;
                    int y = roads[i].second;
                    bool cond1 = (x == v && visited[y]);
                    bool cond2 = (y == v && visited[x]);
                    if (cond1 || cond2) {
                        cands.push_back(i);
                    }
                }
                int num_rep = 0;
                int chosen = -1;
                for (int i : cands) {
                    int u = (roads[i].first == v ? roads[i].second : roads[i].first);
                    // + i
                    cout << "+ " << i << endl;
                    // ? 1 v
                    cout << "? 1 " << v << endl;
                    int ans;
                    cin >> ans;
                    if (ans == -1) return 0;
                    if (ans == 1) {
                        is_repaired[i] = true;
                        num_rep++;
                        if (chosen == -1) {
                            chosen = i;
                        }
                    }
                    // - i
                    cout << "- " << i << endl;
                }
                if (num_rep > 0 && chosen != -1) {
                    // Keep chosen unblocked
                    cout << "+ " << chosen << endl;
                    // Add to tree
                    int u = (roads[chosen].first == v ? roads[chosen].second : roads[chosen].first);
                    tree_adj[u].push_back(v);
                    tree_adj[v].push_back(u);
                    visited[v] = true;
                    changed = true;
                }
            }
        }
        // Now output
        cout << "!";
        for (int i = 1; i <= m; ++i) {
            cout << " " << (is_repaired[i] ? 1 : 0);
        }
        cout << endl;
        int verdict;
        cin >> verdict;
        if (verdict == -1 || verdict == 0) {
            return 0;
        }
    }
    return 0;
}