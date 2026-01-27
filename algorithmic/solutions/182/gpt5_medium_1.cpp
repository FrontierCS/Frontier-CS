#include <bits/stdc++.h>
using namespace std;

struct FastScanner {
    static const int BUFSIZE = 1<<20;
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
    bool readInt(int &out) {
        char c; int sgn = 1; int x = 0;
        c = getch();
        while (c && (c < '0' || c > '9') && c != '-') c = getch();
        if (!c) return false;
        if (c == '-') { sgn = -1; c = getch(); }
        for (; c >= '0' && c <= '9'; c = getch()) x = x*10 + (c - '0');
        out = x * sgn;
        return true;
    }
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    FastScanner fs;
    int N, M;
    if (!fs.readInt(N)) return 0;
    fs.readInt(M);
    vector<int> U(M), V(M);
    vector<int> deg(N+1, 0);
    for (int i = 0; i < M; ++i) {
        int u, v;
        fs.readInt(u);
        fs.readInt(v);
        U[i] = u; V[i] = v;
        deg[u]++; deg[v]++;
    }

    // Build CSR adjacency
    vector<int> off(N+2, 0);
    for (int i = 1; i <= N; ++i) off[i+1] = off[i] + deg[i];
    vector<int> to(off[N+1]);
    vector<int> ptr = off;
    for (int i = 0; i < M; ++i) {
        int a = U[i], b = V[i];
        to[ptr[a]++] = b;
        to[ptr[b]++] = a;
    }

    // Greedy vertex cover by selecting max uncovered-degree vertices
    vector<char> inS(N+1, 0);
    vector<int> cnt(N+1, 0);
    for (int i = 1; i <= N; ++i) cnt[i] = deg[i];

    priority_queue<pair<int,int>> pq;
    for (int i = 1; i <= N; ++i) pq.push({cnt[i], i});

    while (!pq.empty()) {
        auto [c, v] = pq.top(); pq.pop();
        if (c != cnt[v] || inS[v]) continue;
        if (c <= 0) break; // all remaining vertices have 0 uncovered degree
        inS[v] = 1;
        cnt[v] = 0;
        for (int it = off[v]; it < off[v+1]; ++it) {
            int u = to[it];
            if (!inS[u]) {
                cnt[u]--;
                pq.push({cnt[u], u});
            }
        }
    }

    // Prune redundant vertices: remove v in S if all its neighbors are in S
    vector<int> need(N+1, 0);
    queue<int> q;
    for (int v = 1; v <= N; ++v) if (inS[v]) {
        int c0 = 0;
        for (int it = off[v]; it < off[v+1]; ++it) {
            int u = to[it];
            if (!inS[u]) c0++;
        }
        need[v] = c0;
        if (c0 == 0) q.push(v);
    }
    while (!q.empty()) {
        int v = q.front(); q.pop();
        if (!inS[v] || need[v] != 0) continue;
        inS[v] = 0;
        for (int it = off[v]; it < off[v+1]; ++it) {
            int u = to[it];
            if (inS[u]) {
                need[u]++; // v transitioned from inS to not inS
            }
        }
    }

    // Output
    for (int i = 1; i <= N; ++i) {
        cout << (inS[i] ? 1 : 0) << '\n';
    }
    return 0;
}