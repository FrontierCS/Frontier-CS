#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n;
    if (!(cin >> n)) return 0;
    vector<int> a(n + 1, 0);
    for (int i = 1; i <= n; i++) {
        if (!(cin >> a[i])) {
            // Fallback: output all nodes if input is incomplete
            cout << n;
            for (int j = 1; j <= n; j++) cout << " " << j;
            cout << "\n";
            return 0;
        }
    }

    vector<vector<int>> rev(n + 1);
    for (int i = 1; i <= n; i++) {
        if (a[i] >= 1 && a[i] <= n) {
            rev[a[i]].push_back(i);
        } else {
            // Invalid mapping; fallback
            cout << n;
            for (int j = 1; j <= n; j++) cout << " " << j;
            cout << "\n";
            return 0;
        }
    }

    vector<char> inB(n + 1, false);
    int u = 1;
    while (!inB[u]) {
        inB[u] = true;
        u = a[u];
    }

    vector<char> inA = inB;
    queue<int> q;
    for (int i = 1; i <= n; i++) {
        if (inB[i]) q.push(i);
    }

    while (!q.empty()) {
        int v = q.front(); q.pop();
        for (int w : rev[v]) {
            if (!inA[w]) {
                inA[w] = true;
                q.push(w);
            }
        }
    }

    vector<int> ans;
    for (int i = 1; i <= n; i++) if (inA[i]) ans.push_back(i);

    cout << ans.size();
    for (int x : ans) cout << " " << x;
    cout << "\n";

    return 0;
}