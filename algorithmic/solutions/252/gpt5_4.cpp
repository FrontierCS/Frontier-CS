#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int n;
    if (!(cin >> n)) return 0;
    
    vector<int> a(n + 1);
    bool ok = true;
    for (int i = 1; i <= n; ++i) {
        if (!(cin >> a[i])) { ok = false; break; }
    }
    if (!ok) {
        cout << 1 << " " << 1 << "\n";
        return 0;
    }
    
    vector<vector<int>> rev(n + 1);
    for (int i = 1; i <= n; ++i) {
        int v = a[i];
        if (v < 1) v = 1;
        if (v > n) v = n;
        rev[v].push_back(i);
    }
    
    vector<char> inR(n + 1, false);
    int v = 1;
    while (!inR[v]) {
        inR[v] = true;
        v = a[v];
        if (v < 1) v = 1;
        if (v > n) v = n;
    }
    
    vector<char> vis(n + 1, false);
    deque<int> dq;
    for (int i = 1; i <= n; ++i) {
        if (inR[i]) {
            vis[i] = true;
            dq.push_back(i);
        }
    }
    while (!dq.empty()) {
        int u = dq.front(); dq.pop_front();
        for (int w : rev[u]) {
            if (!vis[w]) {
                vis[w] = true;
                dq.push_back(w);
            }
        }
    }
    
    vector<int> ans;
    for (int i = 1; i <= n; ++i) if (vis[i]) ans.push_back(i);
    sort(ans.begin(), ans.end());
    
    cout << ans.size();
    for (size_t i = 0; i < ans.size(); ++i) {
        cout << " " << ans[i];
    }
    cout << "\n";
    
    return 0;
}