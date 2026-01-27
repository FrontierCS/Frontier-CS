#include <bits/stdc++.h>
using namespace std;

struct FastScanner {
    static const int BUFSIZE = 1 << 20;
    int idx, size;
    char buf[BUFSIZE];
    FastScanner(): idx(0), size(0) {}
    inline char read() {
        if (idx >= size) {
            size = (int)fread(buf, 1, BUFSIZE, stdin);
            idx = 0;
            if (size == 0) return 0;
        }
        return buf[idx++];
    }
    bool nextInt(int &out) {
        char c;
        int sgn = 1;
        int x = 0;
        c = read();
        if (!c) return false;
        while (c <= ' ') {
            c = read();
            if (!c) return false;
        }
        if (c == '-') { sgn = -1; c = read(); }
        for (; c >= '0' && c <= '9'; c = read()) {
            x = x * 10 + (c - '0');
        }
        out = x * sgn;
        return true;
    }
};

static inline int otherEndpoint(const pair<int,int>& e, int v) {
    return (e.first == v) ? e.second : e.first;
}

vector<char> cover_matching(const vector<pair<int,int>>& edges, int N) {
    vector<char> inS(N, 0);
    vector<char> matched(N, 0);
    for (const auto &e : edges) {
        int u = e.first, v = e.second;
        if (!matched[u] && !matched[v]) {
            matched[u] = matched[v] = 1;
            inS[u] = inS[v] = 1;
        }
    }
    return inS;
}

vector<char> cover_greedy(const vector<pair<int,int>>& edges, const vector<vector<int>>& incEdges, int N, int M) {
    vector<int> degUncov(N, 0);
    for (int i = 0; i < N; ++i) degUncov[i] = (int)incEdges[i].size();
    vector<char> covered(M, 0);
    vector<char> inS(N, 0);

    priority_queue<pair<int,int>> pq;
    for (int i = 0; i < N; ++i) pq.push({degUncov[i], i});

    int coveredCount = 0;

    auto selectV = [&](int v) {
        if (inS[v]) return;
        inS[v] = 1;
        for (int ei : incEdges[v]) {
            if (!covered[ei]) {
                covered[ei] = 1;
                ++coveredCount;
                int w = otherEndpoint(edges[ei], v);
                degUncov[w]--;
                pq.push({degUncov[w], w});
            }
        }
    };

    while (coveredCount < M) {
        if (pq.empty()) break; // Should not happen
        auto top = pq.top(); pq.pop();
        int val = top.first, v = top.second;
        if (val != degUncov[v]) continue;
        if (val == 0) {
            // Fallback: pick an uncovered edge and select both endpoints to ensure progress
            int eidx = -1;
            for (int i = 0; i < M; ++i) if (!covered[i]) { eidx = i; break; }
            if (eidx == -1) break;
            int a = edges[eidx].first;
            int b = edges[eidx].second;
            // Select both endpoints to cover at least this edge
            selectV(a);
            selectV(b);
            continue;
        }
        selectV(v);
    }
    return inS;
}

void prune_cover(vector<char>& inS, const vector<pair<int,int>>& edges, const vector<vector<int>>& incEdges) {
    int N = (int)inS.size();
    for (int v = 0; v < N; ++v) {
        if (!inS[v]) continue;
        bool canRemove = true;
        for (int ei : incEdges[v]) {
            int u = otherEndpoint(edges[ei], v);
            if (!inS[u]) { canRemove = false; break; }
        }
        if (canRemove) inS[v] = 0;
    }
}

int cover_size(const vector<char>& inS) {
    int s = 0;
    for (char c : inS) s += (c != 0);
    return s;
}

int main() {
    FastScanner fs;
    int N, M;
    if (!fs.nextInt(N)) return 0;
    fs.nextInt(M);

    vector<pair<int,int>> edges;
    edges.reserve(M);
    vector<int> deg(N, 0);

    for (int i = 0; i < M; ++i) {
        int u, v;
        fs.nextInt(u);
        fs.nextInt(v);
        --u; --v;
        edges.emplace_back(u, v);
        deg[u]++; deg[v]++;
    }

    vector<vector<int>> incEdges(N);
    for (int i = 0; i < N; ++i) incEdges[i].reserve(deg[i]);
    for (int i = 0; i < M; ++i) {
        int u = edges[i].first, v = edges[i].second;
        incEdges[u].push_back(i);
        incEdges[v].push_back(i);
    }

    vector<char> sMatch = cover_matching(edges, N);
    prune_cover(sMatch, edges, incEdges);

    vector<char> sGreedy = cover_greedy(edges, incEdges, N, M);
    prune_cover(sGreedy, edges, incEdges);

    vector<char>* best = &sGreedy;
    if (cover_size(sMatch) < cover_size(sGreedy)) best = &sMatch;

    string out;
    out.reserve(N * 2);
    for (int i = 0; i < N; ++i) {
        out.push_back((*best)[i] ? '1' : '0');
        out.push_back('\n');
    }
    fwrite(out.c_str(), 1, out.size(), stdout);
    return 0;
}