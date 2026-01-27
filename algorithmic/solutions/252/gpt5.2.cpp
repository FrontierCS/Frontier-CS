#include <bits/stdc++.h>
using namespace std;

static int n;

static int ask(int u, long long k, const vector<int>& S) {
    cout << "? " << u << " " << k << " " << (int)S.size();
    for (int x : S) cout << " " << x;
    cout << "\n" << flush;

    int ans;
    if (!(cin >> ans)) exit(0);
    if (ans == -1) exit(0);
    return ans;
}

static int find_next_room(int u) {
    vector<int> cand(n);
    iota(cand.begin(), cand.end(), 1);

    while ((int)cand.size() > 1) {
        int mid = (int)cand.size() / 2;
        vector<int> S(cand.begin(), cand.begin() + mid);
        int ans = ask(u, 1, S);
        if (ans == 1) {
            cand.resize(mid);
        } else {
            vector<int> rest(cand.begin() + mid, cand.end());
            cand.swap(rest);
        }
    }
    return cand[0];
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    cin >> n;

    vector<int> a(n + 1, 0);
    for (int u = 1; u <= n; u++) {
        a[u] = find_next_room(u);
    }

    // Find cycle containing room 1.
    vector<int> pos(n + 1, -1);
    vector<int> path;
    int cur = 1;
    while (pos[cur] == -1) {
        pos[cur] = (int)path.size();
        path.push_back(cur);
        cur = a[cur];
    }
    int cycle_start_idx = pos[cur];
    vector<int> cycle_nodes;
    for (int i = cycle_start_idx; i < (int)path.size(); i++) cycle_nodes.push_back(path[i]);

    vector<char> in_cycle(n + 1, 0);
    for (int x : cycle_nodes) in_cycle[x] = 1;

    // Reverse edges for BFS to get all nodes that reach this cycle.
    vector<vector<int>> rev(n + 1);
    for (int u = 1; u <= n; u++) rev[a[u]].push_back(u);

    vector<char> vis(n + 1, 0);
    queue<int> q;
    for (int x : cycle_nodes) {
        vis[x] = 1;
        q.push(x);
    }

    while (!q.empty()) {
        int v = q.front(); q.pop();
        for (int p : rev[v]) {
            if (!vis[p]) {
                vis[p] = 1;
                q.push(p);
            }
        }
    }

    vector<int> A;
    for (int i = 1; i <= n; i++) if (vis[i]) A.push_back(i);
    sort(A.begin(), A.end());

    cout << "! " << (int)A.size();
    for (int x : A) cout << " " << x;
    cout << "\n" << flush;

    return 0;
}