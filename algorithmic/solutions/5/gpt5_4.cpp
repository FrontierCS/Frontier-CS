#include <bits/stdc++.h>
using namespace std;

struct FastScanner {
    static inline int gc() {
        static const int BUFSIZE = 1 << 20;
        static char buf[BUFSIZE];
        static int idx = BUFSIZE, size = BUFSIZE;
        if (idx >= size) {
            size = (int)fread(buf, 1, BUFSIZE, stdin);
            idx = 0;
            if (size == 0) return EOF;
        }
        return buf[idx++];
    }
    template<typename T>
    bool readInt(T &out) {
        int c, s = 1;
        T x = 0;
        c = gc();
        if (c == EOF) return false;
        while (c!='-' && (c<'0'||c>'9')) {
            c = gc();
            if (c == EOF) return false;
        }
        if (c=='-') { s = -1; c = gc(); }
        for (; c>='0' && c<='9'; c=gc()) x = x*10 + (c - '0');
        out = x * s;
        return true;
    }
} In;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    int n, m;
    if (!In.readInt(n)) return 0;
    In.readInt(m);
    // read the 10 scoring parameters, but ignore
    for (int i = 0; i < 10; ++i) {
        int tmp; In.readInt(tmp);
    }

    // Graph adjacency lists (compressed)
    vector<int> headG(n + 1, -1), headR(n + 1, -1);
    vector<int> toG(m), nextG(m);
    vector<int> toR(m), nextR(m);

    int eidx = 0;
    for (int i = 0; i < m; ++i) {
        int u, v;
        In.readInt(u); In.readInt(v);
        toG[eidx] = v; nextG[eidx] = headG[u]; headG[u] = eidx;
        toR[eidx] = u; nextR[eidx] = headR[v]; headR[v] = eidx;
        ++eidx;
    }

    // Kosaraju first pass: order by finish time (iterative)
    vector<char> vis(n + 1, 0);
    vector<int> order; order.reserve(n);
    vector<int> cur(n + 1, -1);
    for (int v = 1; v <= n; ++v) {
        if (vis[v]) continue;
        // iterative DFS
        vector<int> st;
        st.reserve(1024);
        st.push_back(v);
        vis[v] = 1;
        cur[v] = headG[v];
        while (!st.empty()) {
            int x = st.back();
            int &it = cur[x];
            bool pushed = false;
            while (it != -1) {
                int ei = it;
                it = nextG[ei];
                int u = toG[ei];
                if (!vis[u]) {
                    vis[u] = 1;
                    cur[u] = headG[u];
                    st.push_back(u);
                    pushed = true;
                    break;
                }
            }
            if (!pushed) {
                st.pop_back();
                order.push_back(x);
            }
        }
    }

    // Kosaraju second pass: assign components using reverse graph
    vector<int> comp(n + 1, -1);
    int cc = 0;
    for (int i = n - 1; i >= 0; --i) {
        int v = order[i];
        if (comp[v] != -1) continue;
        // BFS/DFS on reverse graph
        vector<int> st;
        st.reserve(1024);
        st.push_back(v);
        comp[v] = cc;
        while (!st.empty()) {
            int x = st.back();
            st.pop_back();
            for (int ei = headR[x]; ei != -1; ei = nextR[ei]) {
                int u = toR[ei];
                if (comp[u] == -1) {
                    comp[u] = cc;
                    st.push_back(u);
                }
            }
        }
        ++cc;
    }

    // Build comp node list (compressed representation)
    vector<int> cnt(cc, 0);
    for (int v = 1; v <= n; ++v) cnt[comp[v]]++;
    vector<int> compStart(cc + 1, 0);
    for (int i = 1; i <= cc; ++i) compStart[i] = compStart[i - 1] + cnt[i - 1];
    vector<int> compOrder(n);
    vector<int> placed(cc, 0);
    for (int v = 1; v <= n; ++v) {
        int c = comp[v];
        compOrder[compStart[c] + placed[c]++] = v;
    }

    // Build component graph (DAG)
    vector<int> C_head(cc, -1);
    vector<int> C_to;
    vector<int> C_next;
    C_to.reserve(m);
    C_next.reserve(m);
    // Also store representative original vertices for each comp-edge
    vector<int> C_fromVertex;
    vector<int> C_toVertex;
    C_fromVertex.reserve(m);
    C_toVertex.reserve(m);
    vector<int> indeg(cc, 0);
    int C_eidx = 0;
    for (int u = 1; u <= n; ++u) {
        int cu = comp[u];
        for (int ei = headG[u]; ei != -1; ei = nextG[ei]) {
            int v = toG[ei];
            int cv = comp[v];
            if (cu != cv) {
                C_to.push_back(cv);
                C_next.push_back(C_head[cu]);
                C_head[cu] = C_eidx;
                C_fromVertex.push_back(u);
                C_toVertex.push_back(v);
                indeg[cv]++;
                C_eidx++;
            }
        }
    }

    // Topological order on component graph (Kahn)
    vector<int> topo;
    topo.reserve(cc);
    deque<int> dq;
    for (int i = 0; i < cc; ++i) if (indeg[i] == 0) dq.push_back(i);
    while (!dq.empty()) {
        int u = dq.front(); dq.pop_front();
        topo.push_back(u);
        for (int ei = C_head[u]; ei != -1; ei = C_next[ei]) {
            int v = C_to[ei];
            if (--indeg[v] == 0) dq.push_back(v);
        }
    }
    if ((int)topo.size() < cc) {
        // Shouldn't happen due to SCC condensation, but guard anyway
        // Fallback: just list components in index order
        topo.clear();
        for (int i = 0; i < cc; ++i) topo.push_back(i);
    }

    // Longest path DP on component DAG
    vector<int> dp(cc, 1), par(cc, -1);
    // We don't actually need to store specific edge indices for connecting across comps
    for (int u : topo) {
        for (int ei = C_head[u]; ei != -1; ei = C_next[ei]) {
            int v = C_to[ei];
            if (dp[v] < dp[u] + 1) {
                dp[v] = dp[u] + 1;
                par[v] = u;
            }
        }
    }
    int bestEnd = 0;
    for (int i = 0; i < cc; ++i) {
        if (dp[i] > dp[bestEnd]) bestEnd = i;
    }
    vector<int> compPath;
    for (int x = bestEnd; x != -1; x = par[x]) compPath.push_back(x);
    reverse(compPath.begin(), compPath.end());

    // Utility arrays for building paths inside components
    vector<int> curOut(n + 1, -2), curIn(n + 1, -2); // iterators for neighbor scans
    vector<int> usedStamp(n + 1, 0); int usedTok = 1;
    vector<int> bfsStamp(n + 1, 0); int bfsTok = 1;
    vector<int> bfsPred(n + 1, -1);
    vector<char> hasOutToNext(n + 1, 0); // mark vertices in current component that have edge to next component

    auto ensureCurOutInit = [&](int v) {
        if (curOut[v] == -2) curOut[v] = headG[v];
    };
    auto ensureCurInInit = [&](int v) {
        if (curIn[v] == -2) curIn[v] = headR[v];
    };

    auto extend_tail = [&](deque<int> &path, int compId, int nextComp)->bool {
        int t = path.back();
        ensureCurOutInit(t);
        int &it = curOut[t];
        while (it != -1) {
            int ei = it;
            it = nextG[ei];
            int u = toG[ei];
            if (comp[u] == compId && usedStamp[u] != usedTok) {
                if (nextComp == -1 || hasOutToNext[u]) {
                    usedStamp[u] = usedTok;
                    path.push_back(u);
                    return true;
                }
            }
        }
        return false;
    };

    auto extend_head = [&](deque<int> &path, int compId)->bool {
        int h = path.front();
        ensureCurInInit(h);
        int &itR = curIn[h];
        while (itR != -1) {
            int ei = itR;
            itR = nextR[ei];
            int p = toR[ei];
            if (comp[p] == compId && usedStamp[p] != usedTok) {
                usedStamp[p] = usedTok;
                path.push_front(p);
                return true;
            }
        }
        return false;
    };

    // BFS inside component c from s to any node with hasOutToNext=true
    auto bfs_to_exit = [&](int c, int s)->int {
        if (hasOutToNext[s]) return s;
        bfsTok++;
        deque<int> q;
        q.push_back(s);
        bfsStamp[s] = bfsTok;
        bfsPred[s] = -1;
        while (!q.empty()) {
            int x = q.front(); q.pop_front();
            for (int ei = headG[x]; ei != -1; ei = nextG[ei]) {
                int u = toG[ei];
                if (comp[u] != c) continue;
                if (bfsStamp[u] == bfsTok) continue;
                bfsStamp[u] = bfsTok;
                bfsPred[u] = x;
                if (hasOutToNext[u]) return u;
                q.push_back(u);
            }
        }
        // ideally shouldn't happen if there is an edge from this comp to next comp
        return s;
    };

    // Build path inside component 'c' with optional next component 'nextC' and entry vertex 's'
    auto build_component_path = [&](int c, int nextC, int s)->vector<int> {
        // Mark hasOutToNext for vertices in this component if nextC != -1
        if (nextC != -1) {
            for (int idx = compStart[c]; idx < compStart[c + 1]; ++idx) {
                int v = compOrder[idx];
                hasOutToNext[v] = 0;
                for (int ei = headG[v]; ei != -1; ei = nextG[ei]) {
                    int u = toG[ei];
                    if (comp[u] == nextC) { hasOutToNext[v] = 1; break; }
                }
            }
        }

        usedTok++;
        deque<int> dq;
        // If need to ensure end has edge to next comp, find shortest path s -> exit
        if (nextC != -1) {
            int exitNode = bfs_to_exit(c, s);
            // reconstruct path s -> exitNode
            vector<int> tmp;
            int x = exitNode;
            while (x != -1) {
                tmp.push_back(x);
                x = bfsPred[x];
            }
            reverse(tmp.begin(), tmp.end());
            for (int v : tmp) {
                usedStamp[v] = usedTok;
                dq.push_back(v);
            }
        } else {
            // no next comp, start from s
            usedStamp[s] = usedTok;
            dq.push_back(s);
        }

        // Greedy two-ended extension
        while (true) {
            bool extended = false;
            // Try extending tail (with condition if nextC != -1)
            if (extend_tail(dq, c, nextC)) {
                extended = true;
            } else {
                // Try extending head freely
                if (extend_head(dq, c)) {
                    extended = true;
                }
            }
            if (!extended) break;
        }

        // Convert deque to vector
        vector<int> res;
        res.reserve(dq.size());
        for (int v : dq) res.push_back(v);
        return res;
    };

    vector<int> result;
    result.reserve(n);

    if (compPath.empty()) {
        // Shouldn't happen, but fallback: pick vertex 1
        cout << 1 << "\n1\n";
        return 0;
    }

    int kcp = (int)compPath.size();
    int sNext = -1;

    // First component
    {
        int c = compPath[0];
        int nextC = (kcp >= 2 ? compPath[1] : -1);

        int s0 = compOrder[compStart[c]]; // arbitrary start
        vector<int> part = build_component_path(c, nextC, s0);
        // append to result
        for (int v : part) result.push_back(v);

        if (nextC != -1) {
            // choose neighbor in nextC from tail
            int tail = result.back();
            int chosen = -1;
            for (int ei = headG[tail]; ei != -1; ei = nextG[ei]) {
                int u = toG[ei];
                if (comp[u] == nextC) { chosen = u; break; }
            }
            if (chosen == -1) {
                // As a fallback, pick the first cross-edge between components
                // This should be rare if build_component_path ensured tail has outgoing to nextC
                for (int ei = C_head[c]; ei != -1; ei = C_next[ei]) {
                    if (C_to[ei] == nextC) { chosen = C_toVertex[ei]; break; }
                }
                if (chosen == -1) {
                    // extreme fallback: pick any vertex in nextC
                    chosen = compOrder[compStart[nextC]];
                }
            }
            sNext = chosen;
        }
    }

    // Rest components
    for (int idx = 1; idx < kcp; ++idx) {
        int c = compPath[idx];
        int nextC = (idx + 1 < kcp ? compPath[idx + 1] : -1);
        if (sNext == -1) {
            // pick arbitrary entry if missing (shouldn't happen)
            sNext = compOrder[compStart[c]];
        }
        vector<int> part = build_component_path(c, nextC, sNext);
        for (int v : part) result.push_back(v);

        if (nextC != -1) {
            int tail = result.back();
            int chosen = -1;
            for (int ei = headG[tail]; ei != -1; ei = nextG[ei]) {
                int u = toG[ei];
                if (comp[u] == nextC) { chosen = u; break; }
            }
            if (chosen == -1) {
                for (int ei = C_head[c]; ei != -1; ei = C_next[ei]) {
                    if (C_to[ei] == nextC) { chosen = C_toVertex[ei]; break; }
                }
                if (chosen == -1) {
                    chosen = compOrder[compStart[nextC]];
                }
            }
            sNext = chosen;
        }
    }

    // Output result path
    cout << (int)result.size() << "\n";
    for (size_t i = 0; i < result.size(); ++i) {
        if (i) cout << ' ';
        cout << result[i];
    }
    cout << "\n";
    return 0;
}