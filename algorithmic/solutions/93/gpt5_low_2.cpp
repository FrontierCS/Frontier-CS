#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int n, ty;
    if (!(cin >> n >> ty)) return 0;
    
    auto ask = [&](const vector<int>& vec) -> int {
        cout << "? " << vec.size();
        for (int v : vec) cout << " " << v;
        cout << "\n" << flush;
        int R;
        if (!(cin >> R)) exit(0);
        return R;
    };
    
    int root = 1;
    for (int v = 1; v <= n; ++v) {
        vector<int> q;
        q.push_back(v);
        for (int u = 1; u <= n; ++u) if (u != v) q.push_back(u);
        int ans = ask(q);
        if (ans == 1) { root = v; break; }
    }
    
    vector<int> par(n+1, root);
    par[root] = 0;
    
    cout << "!";
    for (int i = 1; i <= n; ++i) cout << " " << par[i];
    cout << "\n" << flush;
    return 0;
}