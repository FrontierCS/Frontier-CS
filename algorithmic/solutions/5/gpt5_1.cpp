#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int n, m;
    if (!(cin >> n >> m)) return 0;
    // scoring parameters, not used
    for (int i = 0; i < 10; ++i) {
        int x; cin >> x;
    }
    vector<vector<int>> out(n + 1), in(n + 1);
    out.reserve(n + 1);
    in.reserve(n + 1);
    for (int i = 0; i < m; ++i) {
        int u, v;
        cin >> u >> v;
        out[u].push_back(v);
        in[v].push_back(u);
    }

    // Choose a good starting vertex: maximum total degree
    int start = 1;
    size_t bestDeg = 0;
    for (int i = 1; i <= n; ++i) {
        size_t d = out[i].size() + in[i].size();
        if (d > bestDeg) {
            bestDeg = d;
            start = i;
        }
    }

    // Data structures for path as a doubly linked list
    vector<int> nxt(n + 1, -1), prv(n + 1, -1);
    vector<char> inPath(n + 1, 0);
    vector<int> outPtr(n + 1, 0), inPtr(n + 1, 0);
    int head = start, tail = start;
    inPath[start] = 1;

    auto extendEnds = [&]() -> bool {
        bool extended = false;
        while (true) {
            bool did = false;
            // Extend at tail using out-edges
            while (outPtr[tail] < (int)out[tail].size()) {
                int v = out[tail][outPtr[tail]++];
                if (!inPath[v]) {
                    // append v
                    nxt[tail] = v;
                    prv[v] = tail;
                    nxt[v] = -1;
                    inPath[v] = 1;
                    tail = v;
                    did = true;
                    extended = true;
                    break; // try extending further from new tail
                }
            }
            if (did) continue;

            // Extend at head using in-edges
            while (inPtr[head] < (int)in[head].size()) {
                int u = in[head][inPtr[head]++];
                if (!inPath[u]) {
                    // prepend u
                    prv[head] = u;
                    nxt[u] = head;
                    prv[u] = -1;
                    inPath[u] = 1;
                    head = u;
                    did = true;
                    extended = true;
                    break; // try extending further from new head
                }
            }
            if (!did) break;
        }
        return extended;
    };

    // Initial greedy extension
    extendEnds();

    // Insertion heuristic
    vector<int> mark(n + 1, 0);
    int stamp = 1;

    auto insertionPass = [&]() -> bool {
        bool insertedAny = false;
        for (int u = 1; u <= n; ++u) {
            if (inPath[u]) continue;

            // mark out-neighbors that are in the current path
            if (++stamp == INT_MAX - 1) {
                // reset marks to avoid overflow
                fill(mark.begin(), mark.end(), 0);
                stamp = 1;
            }
            for (int v : out[u]) {
                if (inPath[v]) mark[v] = stamp;
            }
            bool inserted = false;
            for (int x : in[u]) {
                if (!inPath[x]) continue;
                int y = nxt[x];
                if (y != -1 && mark[y] == stamp) {
                    // insert u between x and y
                    nxt[x] = u;
                    prv[u] = x;
                    nxt[u] = y;
                    prv[y] = u;
                    inPath[u] = 1;
                    inserted = true;
                    insertedAny = true;
                    break;
                }
            }
            // no push-front/back here; extendEnds() will handle those
        }
        return insertedAny;
    };

    // Iterate insertion + extension until no progress
    while (true) {
        bool changed = false;
        if (extendEnds()) changed = true;
        if (insertionPass()) changed = true;
        if (extendEnds()) changed = true;
        if (!changed) break;
    }

    // Extract path
    vector<int> path;
    path.reserve(n);
    int cur = head;
    while (cur != -1) {
        path.push_back(cur);
        cur = nxt[cur];
    }

    cout << (int)path.size() << "\n";
    for (size_t i = 0; i < path.size(); ++i) {
        if (i) cout << ' ';
        cout << path[i];
    }
    cout << "\n";
    return 0;
}