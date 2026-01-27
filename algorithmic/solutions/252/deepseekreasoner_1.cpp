#include <bits/stdc++.h>
using namespace std;

int n;
vector<int> a;
vector<vector<int>> rev;

bool ask(int u, int k, const vector<int>& S) {
    cout << "? " << u << " " << k << " " << S.size();
    for (int x : S) cout << " " << x;
    cout << endl;
    int res;
    cin >> res;
    return res == 1;
}

int find_successor(int u) {
    vector<int> cand;
    for (int i = 1; i <= n; i++) cand.push_back(i);
    while (cand.size() > 1) {
        int m = cand.size() / 2;
        vector<int> S(cand.begin(), cand.begin() + m);
        bool res = ask(u, 1, S);
        if (res) {
            cand.resize(m);
        } else {
            cand.erase(cand.begin(), cand.begin() + m);
        }
    }
    return cand[0];
}

int main() {
    cin >> n;
    a.resize(n+1);
    rev.resize(n+1);
    
    for (int u = 1; u <= n; u++) {
        a[u] = find_successor(u);
    }
    
    for (int u = 1; u <= n; u++) {
        rev[a[u]].push_back(u);
    }
    
    vector<bool> vis(n+1, false);
    queue<int> q;
    vis[1] = true;
    q.push(1);
    while (!q.empty()) {
        int v = q.front(); q.pop();
        int nxt = a[v];
        if (!vis[nxt]) {
            vis[nxt] = true;
            q.push(nxt);
        }
        for (int pre : rev[v]) {
            if (!vis[pre]) {
                vis[pre] = true;
                q.push(pre);
            }
        }
    }
    
    vector<int> ans;
    for (int i = 1; i <= n; i++) {
        if (vis[i]) ans.push_back(i);
    }
    
    cout << "! " << ans.size();
    for (int x : ans) cout << " " << x;
    cout << endl;
    
    return 0;
}