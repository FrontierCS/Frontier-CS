#include <bits/stdc++.h>
using namespace std;

static int edgeCache[1005][1005];

int n;
long long l1, l2;

int querySegments(int l, int r) {
    cout << "1 " << l << " " << r << "\n";
    cout.flush();
    int x;
    if (!(cin >> x)) exit(0);
    if (x < 0) exit(0);
    return x;
}

int getEdges(int l, int r) {
    if (l > r) return 0;
    if (l < 1 || r > n) return 0;
    int &res = edgeCache[l][r];
    if (res != -1) return res;
    int seg = querySegments(l, r);
    res = (r - l + 1) - seg;
    return res;
}

int leftCount(int v, int l) { // neighbors of v in [l, v-1]
    if (l > v - 1) return 0;
    return getEdges(l, v) - getEdges(l, v - 1);
}

int rightCount(int v, int r) { // neighbors of v in [v+1, r]
    if (r < v + 1) return 0;
    return getEdges(v, r) - getEdges(v + 1, r);
}

vector<int> findLeftNeighbors(int v, int kleft) {
    vector<int> res;
    if (kleft == 0 || v == 1) return res;

    auto cnt = [&](int l) -> int {
        return leftCount(v, l);
    };

    int lo = 1, hi = v - 1, firstZero = v; // smallest l with cnt(l)==0
    while (lo <= hi) {
        int mid = (lo + hi) >> 1;
        if (cnt(mid) == 0) {
            firstZero = mid;
            hi = mid - 1;
        } else {
            lo = mid + 1;
        }
    }
    int u2 = firstZero - 1;
    res.push_back(u2);

    if (kleft == 2) {
        lo = 1, hi = u2;
        int firstLe1 = u2 + 1; // smallest l with cnt(l)<=1
        while (lo <= hi) {
            int mid = (lo + hi) >> 1;
            if (cnt(mid) <= 1) {
                firstLe1 = mid;
                hi = mid - 1;
            } else {
                lo = mid + 1;
            }
        }
        int u1 = firstLe1 - 1;
        res.push_back(u1);
    }

    sort(res.begin(), res.end());
    res.erase(unique(res.begin(), res.end()), res.end());
    return res;
}

vector<int> findRightNeighbors(int v, int kright) {
    vector<int> res;
    if (kright == 0 || v == n) return res;

    auto cnt = [&](int r) -> int {
        return rightCount(v, r);
    };

    int lo = v + 1, hi = n, u1 = n + 1;
    while (lo <= hi) {
        int mid = (lo + hi) >> 1;
        if (cnt(mid) >= 1) {
            u1 = mid;
            hi = mid - 1;
        } else {
            lo = mid + 1;
        }
    }
    res.push_back(u1);

    if (kright == 2) {
        lo = v + 1, hi = n;
        int u2 = n + 1;
        while (lo <= hi) {
            int mid = (lo + hi) >> 1;
            if (cnt(mid) >= 2) {
                u2 = mid;
                hi = mid - 1;
            } else {
                lo = mid + 1;
            }
        }
        res.push_back(u2);
    }

    sort(res.begin(), res.end());
    res.erase(unique(res.begin(), res.end()), res.end());
    return res;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    cin >> n >> l1 >> l2;
    if (!cin) return 0;

    for (int i = 0; i <= 1004; i++)
        for (int j = 0; j <= 1004; j++)
            edgeCache[i][j] = -1;

    if (n == 1) {
        cout << "3 1\n";
        cout.flush();
        return 0;
    }

    vector<vector<int>> adj(n + 1);

    auto addEdge = [&](int a, int b) {
        if (a < 1 || a > n || b < 1 || b > n || a == b) return;
        auto addOne = [&](int u, int v) {
            for (int x : adj[u]) if (x == v) return;
            adj[u].push_back(v);
        };
        addOne(a, b);
        addOne(b, a);
    };

    for (int v = 1; v <= n; v++) {
        int kleft = leftCount(v, 1);
        int kright = rightCount(v, n);

        vector<int> L = findLeftNeighbors(v, kleft);
        vector<int> R = findRightNeighbors(v, kright);

        for (int u : L) addEdge(v, u);
        for (int u : R) addEdge(v, u);
    }

    vector<int> ends;
    for (int i = 1; i <= n; i++) {
        sort(adj[i].begin(), adj[i].end());
        adj[i].erase(unique(adj[i].begin(), adj[i].end()), adj[i].end());
        if ((int)adj[i].size() == 1) ends.push_back(i);
    }

    auto buildPermutationFromStart = [&](int start) -> vector<int> {
        vector<int> perm(n + 1, 0);
        int prev = 0, cur = start;
        for (int val = 1; val <= n; val++) {
            perm[cur] = val;
            int nxt = 0;
            for (int x : adj[cur]) if (x != prev) { nxt = x; break; }
            prev = cur;
            cur = nxt;
            if (val != n && cur == 0) break;
        }
        return perm;
    };

    vector<int> perm;
    if ((int)ends.size() >= 1) {
        perm = buildPermutationFromStart(ends[0]);
        int filled = 0;
        for (int i = 1; i <= n; i++) if (perm[i]) filled++;
        if (filled != n && (int)ends.size() >= 2) perm = buildPermutationFromStart(ends[1]);
    } else {
        perm = buildPermutationFromStart(1);
    }

    cout << "3";
    for (int i = 1; i <= n; i++) cout << " " << perm[i];
    cout << "\n";
    cout.flush();
    return 0;
}