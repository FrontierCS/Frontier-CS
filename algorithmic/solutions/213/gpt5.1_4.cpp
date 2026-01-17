#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n;
    if (!(cin >> n)) return 0;
    vector<int> a(n + 1);
    for (int i = 1; i <= n; ++i) cin >> a[i];

    if (n == 1) {
        cout << 1 << "\n" << 0 << "\n";
        return 0;
    }

    int X;
    vector<int> pos(n + 1);
    for (int i = 1; i <= n; ++i) pos[a[i]] = i;

    vector<tuple<int,int,int>> ops;

    auto apply = [&](int l, int dir) {
        int len = X;
        int r = l + len - 1;
        int buf[5];
        for (int i = 0; i < len; ++i) buf[i] = a[l + i];
        if (dir == 0) { // left
            for (int i = 0; i < len; ++i) a[l + i] = buf[(i + 1) % len];
        } else { // right
            for (int i = 0; i < len; ++i) a[l + i] = buf[(i - 1 + len) % len];
        }
        for (int i = 0; i < len; ++i) pos[a[l + i]] = l + i;
        ops.emplace_back(l, r, dir);
    };

    if (n <= 4) {
        X = 2;
        for (int i = 1; i <= n; ++i) {
            for (int j = 1; j <= n - i; ++j) {
                if (a[j] > a[j + 1]) {
                    apply(j, 0);
                }
            }
        }
        cout << X << "\n" << ops.size() << "\n";
        for (auto &t : ops) {
            int l, r, d;
            tie(l, r, d) = t;
            cout << l << " " << r << " " << d << "\n";
        }
        return 0;
    }

    // n >= 5
    X = 4;
    ops.clear();
    // pos is already initialized correctly

    // BFS precompute for tail of length 5 with operations on segments of length 4
    const int K = 5;
    int fact[6] = {1, 1, 2, 6, 24, 120};
    auto encode = [&](const array<int, K> &p) -> int {
        int id = 0;
        for (int i = 0; i < K; ++i) {
            int smaller = 0;
            for (int j = i + 1; j < K; ++j)
                if (p[j] < p[i]) ++smaller;
            id += smaller * fact[K - 1 - i];
        }
        return id;
    };

    static bool bfsBuilt = false;
    static int parentArr[120];
    static int opToHere[120];
    static array<int, K> permById[120];
    static int rootId;

    if (!bfsBuilt) {
        for (int i = 0; i < 120; ++i) parentArr[i] = -2;
        array<int, K> rootPerm = {0, 1, 2, 3, 4};
        rootId = encode(rootPerm);
        queue<int> q;
        vector<char> vis(120, false);
        vis[rootId] = true;
        parentArr[rootId] = -1;
        permById[rootId] = rootPerm;
        q.push(rootId);
        while (!q.empty()) {
            int id = q.front(); q.pop();
            auto p = permById[id];
            array<int, K> np;
            for (int op = 0; op < 4; ++op) {
                if (op == 0) { // left [0..3]
                    np[0] = p[1]; np[1] = p[2]; np[2] = p[3]; np[3] = p[0]; np[4] = p[4];
                } else if (op == 1) { // right [0..3]
                    np[0] = p[3]; np[1] = p[0]; np[2] = p[1]; np[3] = p[2]; np[4] = p[4];
                } else if (op == 2) { // left [1..4]
                    np[0] = p[0]; np[1] = p[2]; np[2] = p[3]; np[3] = p[4]; np[4] = p[1];
                } else { // op == 3, right [1..4]
                    np[0] = p[0]; np[1] = p[4]; np[2] = p[1]; np[3] = p[2]; np[4] = p[3];
                }
                int nid = encode(np);
                if (!vis[nid]) {
                    vis[nid] = true;
                    parentArr[nid] = id;
                    opToHere[nid] = op; // from parent to nid
                    permById[nid] = np;
                    q.push(nid);
                }
            }
        }
        bfsBuilt = true;
    }

    auto getTailPath = [&](array<int, K> &startPerm) -> vector<int> {
        int id = encode(startPerm);
        vector<int> path;
        while (id != rootId) {
            int op = opToHere[id];
            int inv;
            if (op == 0) inv = 1;
            else if (op == 1) inv = 0;
            else if (op == 2) inv = 3;
            else inv = 2;
            path.push_back(inv);
            id = parentArr[id];
        }
        return path;
    };

    // Main algorithm: handle positions 1..n-5
    for (int i = 1; i <= n - 5; ++i) {
        int v = i;
        while (pos[v] >= i + 3) {
            int p = pos[v];
            int l = p - 3;
            apply(l, 1); // right shift [l..l+3]
        }
        int p = pos[v];
        if (p == i) {
            continue;
        } else if (p == i + 1) {
            apply(i, 0); // left shift [i..i+3]
        } else if (p == i + 2) {
            apply(i, 0);
            apply(i, 0);
        } else {
            // should not occur
        }
    }

    // Tail of 5 elements: positions [n-4..n]
    array<int, K> tailPerm;
    for (int idx = 0; idx < 5; ++idx) {
        tailPerm[idx] = a[n - 4 + idx] - (n - 4);
    }
    vector<int> tailOps = getTailPath(tailPerm);
    for (int op : tailOps) {
        if (op == 0) apply(n - 4, 0);
        else if (op == 1) apply(n - 4, 1);
        else if (op == 2) apply(n - 3, 0);
        else apply(n - 3, 1);
    }

    cout << X << "\n" << ops.size() << "\n";
    for (auto &t : ops) {
        int l, r, d;
        tie(l, r, d) = t;
        cout << l << " " << r << " " << d << "\n";
    }

    return 0;
}