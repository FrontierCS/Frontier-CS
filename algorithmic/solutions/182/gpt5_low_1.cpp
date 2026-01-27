#include <bits/stdc++.h>
using namespace std;

struct FastScanner {
    static const int BUFSIZE = 1 << 20;
    int idx, size;
    char buf[BUFSIZE];
    FastScanner() : idx(0), size(0) {}
    inline char getch() {
        if (idx >= size) {
            size = (int)fread(buf, 1, BUFSIZE, stdin);
            idx = 0;
            if (size == 0) return 0;
        }
        return buf[idx++];
    }
    template <typename T>
    bool readInt(T &out) {
        char c; T sign = 1; T val = 0;
        c = getch();
        if (!c) return false;
        while (c != '-' && (c < '0' || c > '9')) {
            c = getch();
            if (!c) return false;
        }
        if (c == '-') { sign = -1; c = getch(); }
        for (; c >= '0' && c <= '9'; c = getch()) val = val * 10 + (c - '0');
        out = val * sign;
        return true;
    }
} In;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int N, M;
    if (!In.readInt(N)) return 0;
    In.readInt(M);

    vector<pair<int,int>> edges;
    edges.reserve(M);
    vector<vector<int>> incEdges(N + 1);
    edges.resize(M);
    for (int i = 0; i < M; ++i) {
        int u, v;
        In.readInt(u);
        In.readInt(v);
        edges[i] = {u, v};
        incEdges[u].push_back(i);
        incEdges[v].push_back(i);
    }

    vector<char> edgeCovered(M, 0);
    vector<int> degUncov(N + 1, 0);
    for (int v = 1; v <= N; ++v) degUncov[v] = (int)incEdges[v].size();

    // Max-heap by current uncovered incident edge count
    priority_queue<pair<int,int>> pq;
    for (int v = 1; v <= N; ++v) pq.emplace(degUncov[v], v);

    vector<char> selected(N + 1, 0);
    long long remainingEdges = M;

    while (remainingEdges > 0 && !pq.empty()) {
        auto [d, v] = pq.top(); pq.pop();
        if (d != degUncov[v]) continue; // outdated
        if (selected[v]) continue;
        if (degUncov[v] == 0) continue; // no contribution
        // Select v
        selected[v] = 1;
        // Cover incident edges
        for (int ei : incEdges[v]) {
            if (!edgeCovered[ei]) {
                edgeCovered[ei] = 1;
                --remainingEdges;
                int a = edges[ei].first, b = edges[ei].second;
                int u = (a == v ? b : a);
                if (degUncov[u] > 0) {
                    --degUncov[u];
                    pq.emplace(degUncov[u], u);
                }
                if (degUncov[v] > 0) {
                    --degUncov[v];
                }
            }
        }
        // Optionally push updated v (not necessary since it's selected)
    }

    // Safety: if any edges remain (shouldn't), cover them arbitrarily by adding one endpoint
    if (remainingEdges > 0) {
        for (int i = 0; i < M; ++i) {
            if (!edgeCovered[i]) {
                int u = edges[i].first, v = edges[i].second;
                if (!selected[u] && !selected[v]) selected[u] = 1;
                edgeCovered[i] = 1;
            }
        }
    }

    // Prune: remove any selected vertex whose all neighbors are selected
    for (int v = 1; v <= N; ++v) {
        if (!selected[v]) continue;
        bool removable = true;
        for (int ei : incEdges[v]) {
            int a = edges[ei].first, b = edges[ei].second;
            int u = (a == v ? b : a);
            if (!selected[u]) { removable = false; break; }
        }
        if (removable) selected[v] = 0;
    }

    // Output
    for (int v = 1; v <= N; ++v) {
        cout << (selected[v] ? 1 : 0) << '\n';
    }
    return 0;
}