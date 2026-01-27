#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int n, m;
    if (!(cin >> n >> m)) return 0;
    vector<int> a(10);
    for (int i = 0; i < 10; ++i) cin >> a[i]; // scoring parameters, unused

    vector<vector<int>> g(n + 1), rg(n + 1);
    g.reserve(n + 1);
    rg.reserve(n + 1);
    for (int i = 0; i < m; ++i) {
        int u, v;
        cin >> u >> v;
        g[u].push_back(v);
        rg[v].push_back(u);
    }
    for (int i = 1; i <= n; ++i) {
        sort(g[i].begin(), g[i].end());
        sort(rg[i].begin(), rg[i].end());
    }

    auto hasEdge = [&](int u, int v) -> bool {
        const auto &gu = g[u];
        return binary_search(gu.begin(), gu.end(), v);
    };

    vector<int> nxt(n + 1, 0), prv(n + 1, 0);
    vector<char> inP(n + 1, 0);

    // Random order
    vector<int> order(n);
    iota(order.begin(), order.end(), 1);
    uint64_t seed = chrono::high_resolution_clock::now().time_since_epoch().count();
    shuffle(order.begin(), order.end(), mt19937_64(seed));

    int head = 0, tail = 0;

    auto insert_between = [&](int u, int v, int w) {
        // u -> v -> w
        nxt[u] = v;
        prv[v] = u;
        nxt[v] = w;
        prv[w] = v;
        inP[v] = 1;
    };

    auto try_insert = [&](int v) -> bool {
        if (inP[v]) return false;
        if (head == 0) {
            head = tail = v;
            inP[v] = 1;
            nxt[v] = prv[v] = 0;
            return true;
        }
        // append
        if (hasEdge(tail, v)) {
            nxt[tail] = v;
            prv[v] = tail;
            nxt[v] = 0;
            tail = v;
            inP[v] = 1;
            return true;
        }
        // prepend
        if (hasEdge(v, head)) {
            prv[head] = v;
            nxt[v] = head;
            prv[v] = 0;
            head = v;
            inP[v] = 1;
            return true;
        }
        // try insert using outgoing edges v -> w (w in path), need prev[w] -> v
        const auto &out = g[v];
        for (int w : out) {
            if (!inP[w]) continue;
            int u = prv[w];
            if (u == 0) continue; // w is head; prepend already checked
            if (hasEdge(u, v)) {
                insert_between(u, v, w);
                return true;
            }
        }
        // try insert using incoming edges u -> v (u in path), need v -> next[u]
        const auto &in = rg[v];
        for (int u : in) {
            if (!inP[u]) continue;
            int w = nxt[u];
            if (w == 0) continue; // u is tail; append already checked
            if (hasEdge(v, w)) {
                insert_between(u, v, w);
                return true;
            }
        }
        return false;
    };

    // Build initial path
    head = tail = order[0];
    inP[head] = 1;
    prv[head] = nxt[head] = 0;

    vector<int> remain;
    remain.reserve(n);
    for (int i = 1; i < n; ++i) remain.push_back(order[i]);

    // Perform a few passes to try to insert remaining vertices
    int max_passes = 3;
    for (int pass = 0; pass < max_passes && !remain.empty(); ++pass) {
        shuffle(remain.begin(), remain.end(), mt19937_64(seed + pass + 1));
        vector<int> nextRemain;
        nextRemain.reserve(remain.size());
        int insertedThisPass = 0;
        for (int v : remain) {
            if (inP[v]) continue;
            if (!try_insert(v)) {
                nextRemain.push_back(v);
            } else {
                insertedThisPass++;
            }
        }
        remain.swap(nextRemain);
        if (insertedThisPass == 0) break;
    }

    // Output result
    vector<int> path;
    path.reserve(n);
    for (int x = head; x != 0; x = nxt[x]) path.push_back(x);

    cout << (int)path.size() << "\n";
    for (int i = 0; i < (int)path.size(); ++i) {
        if (i) cout << ' ';
        cout << path[i];
    }
    cout << "\n";
    return 0;
}