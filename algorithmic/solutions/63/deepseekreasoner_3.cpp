#include <iostream>
#include <vector>
#include <queue>
#include <algorithm>
using namespace std;

int N, M;
vector<pair<int, int>> edges;
vector<vector<int>> adj;

// ask a query: orient edges away from source set S.
// if isP is true, S = [l, r]; else S = complement of [l, r].
int ask(int l, int r, bool isP) {
    vector<int> dist(N, -1);
    queue<int> q;
    // mark source set
    for (int i = 0; i < N; i++) {
        bool inRange = (l <= i && i <= r);
        if ((isP && inRange) || (!isP && !inRange)) {
            dist[i] = 0;
            q.push(i);
        }
    }
    // BFS
    while (!q.empty()) {
        int u = q.front(); q.pop();
        for (int v : adj[u]) {
            if (dist[v] == -1) {
                dist[v] = dist[u] + 1;
                q.push(v);
            }
        }
    }
    // output orientation
    cout << 0;
    for (auto &e : edges) {
        int u = e.first, v = e.second;
        int d;
        if (dist[u] < dist[v]) d = 0;          // u -> v
        else if (dist[u] > dist[v]) d = 1;     // v -> u
        else d = (u < v ? 0 : 1);              // tie-break by id
        // map to input order: edge is given as (U_i, V_i) with U_i < V_i
        if (d == 0) {
            // orientation from U_i to V_i
            cout << " 0";
        } else {
            cout << " 1";
        }
    }
    cout << endl;
    cout.flush();
    int ans;
    cin >> ans;
    return ans;
}

// find A in [l, r] knowing that B is not in [l, r]
int findA(int l, int r) {
    while (l < r) {
        int mid = (l + r) / 2;
        int res = ask(l, mid, true);   // type P
        if (res == 1) r = mid;
        else l = mid + 1;
    }
    return l;
}

// find B in [l, r] knowing that A is not in [l, r]
int findB(int l, int r) {
    while (l < r) {
        int mid = (l + r) / 2;
        int res = ask(l, mid, false);  // type Q
        if (res == 1) r = mid;
        else l = mid + 1;
    }
    return l;
}

// recursive search for both A and B in [l, r]
pair<int, int> solve(int l, int r) {
    if (l + 1 == r) {   // two nodes
        // check order
        int resP = ask(l, l, true);
        if (resP == 1) return {l, r};
        int resQ = ask(l, l, false);
        if (resQ == 1) return {r, l};
        // should not happen
        return {-1, -1};
    }
    int mid = (l + r) / 2;
    int p1 = ask(l, mid, true);
    int p2 = ask(l, mid, false);
    if (p1 == 1 && p2 == 0) {
        int A = findA(l, mid);
        int B = findB(mid + 1, r);
        return {A, B};
    } else if (p1 == 0 && p2 == 1) {
        int B = findB(l, mid);     // using type Q
        int A = findA(mid + 1, r); // using type P
        return {A, B};
    } else { // both 0: both in left or both in right
        // try left first
        pair<int, int> cand = solve(l, mid);
        // verify candidate
        int v1 = ask(cand.first, cand.first, true);
        int v2 = ask(cand.second, cand.second, false);
        if (v1 == 1 && v2 == 1) return cand;
        // else try right
        cand = solve(mid + 1, r);
        v1 = ask(cand.first, cand.first, true);
        v2 = ask(cand.second, cand.second, false);
        if (v1 == 1 && v2 == 1) return cand;
        // should not happen
        return {-1, -1};
    }
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(0);
    cin >> N >> M;
    edges.resize(M);
    adj.resize(N);
    for (int i = 0; i < M; i++) {
        int u, v;
        cin >> u >> v;
        edges[i] = {u, v};
        adj[u].push_back(v);
        adj[v].push_back(u);
    }
    pair<int, int> ans = solve(0, N - 1);
    cout << 1 << " " << ans.first << " " << ans.second << endl;
    cout.flush();
    return 0;
}