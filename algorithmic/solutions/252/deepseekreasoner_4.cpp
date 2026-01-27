#include <bits/stdc++.h>
using namespace std;

int n;

// ask query: ? u k |S| S...
// returns 0 or 1
int ask(int u, long long k, const vector<int>& S) {
    cout << "? " << u << " " << k << " " << S.size();
    for (int x : S) cout << " " << x;
    cout << endl;
    int resp;
    cin >> resp;
    return resp;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(0);
    cin >> n;
    vector<int> succ(n + 1);
    // find successor for each node using binary search
    for (int i = 1; i <= n; ++i) {
        vector<int> cand;
        for (int j = 1; j <= n; ++j) cand.push_back(j);
        while ((int)cand.size() > 1) {
            int m = cand.size();
            int half = m / 2;
            vector<int> left(cand.begin(), cand.begin() + half);
            int res = ask(i, 1, left);
            if (res == 1) {
                cand = vector<int>(cand.begin(), cand.begin() + half);
            } else {
                cand = vector<int>(cand.begin() + half, cand.end());
            }
        }
        succ[i] = cand[0];
    }
    // build reverse graph
    vector<vector<int>> rev(n + 1);
    for (int i = 1; i <= n; ++i) {
        rev[succ[i]].push_back(i);
    }
    // find the cycle reachable from 1
    vector<bool> vis(n + 1, false);
    vector<int> path;
    int cur = 1;
    while (!vis[cur]) {
        vis[cur] = true;
        path.push_back(cur);
        cur = succ[cur];
    }
    // cur is the first repeated node (start of cycle)
    int cycle_start = 0;
    for (int i = 0; i < (int)path.size(); ++i) {
        if (path[i] == cur) {
            cycle_start = i;
            break;
        }
    }
    vector<bool> in_cycle(n + 1, false);
    for (int i = cycle_start; i < (int)path.size(); ++i) {
        in_cycle[path[i]] = true;
    }
    // BFS on reverse graph from all cycle nodes
    vector<bool> in_comp(n + 1, false);
    queue<int> q;
    for (int i = 1; i <= n; ++i) {
        if (in_cycle[i]) {
            in_comp[i] = true;
            q.push(i);
        }
    }
    while (!q.empty()) {
        int v = q.front(); q.pop();
        for (int prev : rev[v]) {
            if (!in_comp[prev]) {
                in_comp[prev] = true;
                q.push(prev);
            }
        }
    }
    // collect answer
    vector<int> ans;
    for (int i = 1; i <= n; ++i) {
        if (in_comp[i]) ans.push_back(i);
    }
    cout << "! " << ans.size();
    for (int x : ans) cout << " " << x;
    cout << endl;
    return 0;
}