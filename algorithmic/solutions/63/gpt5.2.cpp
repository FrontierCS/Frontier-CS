#include <bits/stdc++.h>
using namespace std;

struct SplitMix64 {
    uint64_t x;
    explicit SplitMix64(uint64_t seed = 0) : x(seed) {}
    uint64_t next() {
        uint64_t z = (x += 0x9e3779b97f4a7c15ULL);
        z = (z ^ (z >> 30)) * 0xbf58476d1ce4e5b9ULL;
        z = (z ^ (z >> 27)) * 0x94d049bb133111ebULL;
        return z ^ (z >> 31);
    }
    uint32_t next_u32() { return (uint32_t)next(); }
    int next_int(int lo, int hi) { // inclusive
        return lo + (int)(next() % (uint64_t)(hi - lo + 1));
    }
    bool next_bool() { return (next() >> 63) & 1ULL; }
};

struct EvalData {
    vector<uint8_t> dir;
    vector<int> comp;
    int K = 0;
    vector<uint64_t> reach; // K * words bitsets over vertices
    uint64_t count1 = 0;
    uint64_t worst = 0;
    void clear() {
        dir.clear();
        comp.clear();
        reach.clear();
        K = 0;
        count1 = 0;
        worst = 0;
    }
};

static inline int ctz64(uint64_t x) { return __builtin_ctzll(x); }
static inline int pop64(uint64_t x) { return __builtin_popcountll(x); }

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int N, M;
    cin >> N >> M;
    vector<int> U(M), V(M);
    vector<vector<pair<int,int>>> adj(N);
    adj.reserve(N);
    for (int i = 0; i < M; i++) {
        cin >> U[i] >> V[i];
        adj[U[i]].push_back({V[i], i});
        adj[V[i]].push_back({U[i], i});
    }

    // Build a spanning tree by BFS from 0
    vector<int> parent(N, -1);
    vector<int> parentEdge(N, -1);
    vector<vector<int>> treeAdj(N);
    treeAdj.reserve(N);

    {
        queue<int> q;
        vector<char> vis(N, 0);
        vis[0] = 1;
        q.push(0);
        while (!q.empty()) {
            int x = q.front(); q.pop();
            for (auto [y, ei] : adj[x]) {
                if (!vis[y]) {
                    vis[y] = 1;
                    parent[y] = x;
                    parentEdge[y] = ei;
                    treeAdj[x].push_back(y);
                    treeAdj[y].push_back(x);
                    q.push(y);
                }
            }
        }
        // Graph connected, so all visited.
    }

    // tin/tout for subtree checks in rooted tree at 0
    vector<int> tin(N), tout(N);
    {
        int timer = 0;
        vector<int> it(N, 0);
        vector<int> st;
        st.reserve(N);
        st.push_back(0);
        parent[0] = -1;
        while (!st.empty()) {
            int v = st.back();
            if (it[v] == 0) tin[v] = timer++;
            if (it[v] == (int)treeAdj[v].size()) {
                tout[v] = timer;
                st.pop_back();
                continue;
            }
            int to = treeAdj[v][it[v]++];
            if (to == parent[v]) continue;
            parent[to] = v;
            st.push_back(to);
        }
    }

    auto inSubtree = [&](int root, int x) -> bool {
        return tin[root] <= tin[x] && tin[x] < tout[root];
    };

    int words = (N + 63) / 64;
    uint64_t lastMask = (N % 64 == 0) ? ~0ULL : ((1ULL << (N % 64)) - 1ULL);

    // Candidate pairs: for each A (row), bitset of possible B.
    vector<uint64_t> cand((size_t)N * words, 0);
    for (int a = 0; a < N; a++) {
        uint64_t *row = &cand[(size_t)a * words];
        for (int w = 0; w < words; w++) row[w] = ~0ULL;
        row[words - 1] &= lastMask;
        row[a / 64] &= ~(1ULL << (a % 64));
    }

    uint64_t totalC = (uint64_t)N * (uint64_t)(N - 1);
    vector<int> active;
    active.reserve(N);
    for (int i = 0; i < N; i++) active.push_back(i);

    SplitMix64 rng((uint64_t)chrono::high_resolution_clock::now().time_since_epoch().count() ^ 0x9e3779b97f4a7c15ULL);

    // Work buffers for SCC
    vector<int> headOut(N), headRev(N), nextOut(M), nextRev(M), toOut(M), toRev(M);
    vector<char> vis(N);
    vector<int> order; order.reserve(N);

    auto evaluate = [&](EvalData &ed) {
        // Build directed graph from ed.dir
        fill(headOut.begin(), headOut.end(), -1);
        fill(headRev.begin(), headRev.end(), -1);
        for (int i = 0; i < M; i++) {
            int a = (ed.dir[i] == 0) ? U[i] : V[i];
            int b = (ed.dir[i] == 0) ? V[i] : U[i];
            toOut[i] = b;
            nextOut[i] = headOut[a];
            headOut[a] = i;

            toRev[i] = a;
            nextRev[i] = headRev[b];
            headRev[b] = i;
        }

        // Kosaraju 1st pass: order
        fill(vis.begin(), vis.end(), 0);
        order.clear();
        struct Frame { int v; int e; };
        vector<Frame> st;
        st.reserve(N);

        for (int s = 0; s < N; s++) {
            if (vis[s]) continue;
            vis[s] = 1;
            st.push_back({s, headOut[s]});
            while (!st.empty()) {
                Frame &f = st.back();
                if (f.e == -1) {
                    order.push_back(f.v);
                    st.pop_back();
                    continue;
                }
                int ei = f.e;
                f.e = nextOut[ei];
                int w = toOut[ei];
                if (!vis[w]) {
                    vis[w] = 1;
                    st.push_back({w, headOut[w]});
                }
            }
        }

        // Kosaraju 2nd pass: components
        ed.comp.assign(N, -1);
        int K = 0;
        vector<int> stack2;
        stack2.reserve(N);

        for (int idx = N - 1; idx >= 0; idx--) {
            int v = order[idx];
            if (ed.comp[v] != -1) continue;
            ed.comp[v] = K;
            stack2.push_back(v);
            while (!stack2.empty()) {
                int x = stack2.back();
                stack2.pop_back();
                for (int ei = headRev[x]; ei != -1; ei = nextRev[ei]) {
                    int y = toRev[ei];
                    if (ed.comp[y] == -1) {
                        ed.comp[y] = K;
                        stack2.push_back(y);
                    }
                }
            }
            K++;
        }
        ed.K = K;

        // Condensation DAG edges (unique)
        const int SHIFT = 14;
        const uint32_t MASK = (1u << SHIFT) - 1u;
        vector<uint32_t> packs;
        packs.reserve(M);
        for (int i = 0; i < M; i++) {
            int a = (ed.dir[i] == 0) ? U[i] : V[i];
            int b = (ed.dir[i] == 0) ? V[i] : U[i];
            int ca = ed.comp[a];
            int cb = ed.comp[b];
            if (ca != cb) {
                packs.push_back((uint32_t)((ca << SHIFT) | cb));
            }
        }
        sort(packs.begin(), packs.end());
        packs.erase(unique(packs.begin(), packs.end()), packs.end());

        vector<int> outdeg(K, 0), indeg(K, 0);
        for (uint32_t p : packs) {
            int a = (int)(p >> SHIFT);
            int b = (int)(p & MASK);
            outdeg[a]++;
            indeg[b]++;
        }

        vector<int> start(K + 1, 0);
        for (int i = 0; i < K; i++) start[i + 1] = start[i] + outdeg[i];
        int E = start[K];
        vector<int> csrTo(E);
        vector<int> cur = start;
        for (uint32_t p : packs) {
            int a = (int)(p >> SHIFT);
            int b = (int)(p & MASK);
            csrTo[cur[a]++] = b;
        }

        // Toposort
        vector<int> topo;
        topo.reserve(K);
        deque<int> dq;
        for (int i = 0; i < K; i++) if (indeg[i] == 0) dq.push_back(i);
        while (!dq.empty()) {
            int x = dq.front();
            dq.pop_front();
            topo.push_back(x);
            for (int ei = start[x]; ei < start[x + 1]; ei++) {
                int y = csrTo[ei];
                if (--indeg[y] == 0) dq.push_back(y);
            }
        }
        // Reachability DP over vertices bitsets
        ed.reach.assign((size_t)K * words, 0ULL);
        for (int v = 0; v < N; v++) {
            int c = ed.comp[v];
            ed.reach[(size_t)c * words + (v >> 6)] |= 1ULL << (v & 63);
        }
        for (int ti = (int)topo.size() - 1; ti >= 0; ti--) {
            int x = topo[ti];
            uint64_t *rx = &ed.reach[(size_t)x * words];
            for (int ei = start[x]; ei < start[x + 1]; ei++) {
                int y = csrTo[ei];
                uint64_t *ry = &ed.reach[(size_t)y * words];
                for (int w = 0; w < words; w++) rx[w] |= ry[w];
            }
        }

        // Count how many remaining candidates would answer 1
        uint64_t cnt = 0;
        for (int a : active) {
            const uint64_t *row = &cand[(size_t)a * words];
            const uint64_t *ra = &ed.reach[(size_t)ed.comp[a] * words];
            for (int w = 0; w < words; w++) cnt += (uint64_t)pop64(row[w] & ra[w]);
        }
        ed.count1 = cnt;
        uint64_t other = totalC - cnt;
        ed.worst = max(cnt, other);
    };

    vector<int> distP(N), distC(N);
    auto bfs_tree = [&](int s, vector<int> &dist) {
        fill(dist.begin(), dist.end(), -1);
        deque<int> dq;
        dist[s] = 0;
        dq.push_back(s);
        while (!dq.empty()) {
            int x = dq.front(); dq.pop_front();
            for (int y : treeAdj[x]) {
                if (dist[y] == -1) {
                    dist[y] = dist[x] + 1;
                    dq.push_back(y);
                }
            }
        }
    };

    auto gen_random = [&](vector<uint8_t> &dir) {
        dir.resize(M);
        for (int i = 0; i < M; i++) dir[i] = (uint8_t)(rng.next() & 1ULL);
    };

    auto gen_perm = [&](vector<uint8_t> &dir) {
        vector<uint64_t> rank(N);
        for (int i = 0; i < N; i++) rank[i] = rng.next();
        dir.resize(M);
        for (int i = 0; i < M; i++) {
            int u = U[i], v = V[i]; // u < v
            if (rank[u] < rank[v]) dir[i] = 0;
            else if (rank[u] > rank[v]) dir[i] = 1;
            else dir[i] = 0; // tie, u->v
        }
    };

    auto gen_cut = [&](vector<uint8_t> &dir, bool forward) {
        // pick random child c != 0
        int c = (N == 2) ? 1 : rng.next_int(1, N - 1);
        int p = parent[c];
        if (p < 0) { // should not happen unless N==1
            c = 1;
            p = 0;
        }
        bfs_tree(p, distP);
        bfs_tree(c, distC);

        dir.resize(M);
        for (int i = 0; i < M; i++) {
            int u = U[i], v = V[i];
            bool inU = inSubtree(c, u);
            bool inV = inSubtree(c, v);

            int from, to;
            if (inU != inV) {
                // cross edge: sources -> destinations
                bool uInS = inU; // S is subtree(c)
                if (forward) {
                    // S -> T
                    if (uInS) { from = u; to = v; }
                    else { from = v; to = u; }
                } else {
                    // T -> S
                    if (uInS) { from = v; to = u; }
                    else { from = u; to = v; }
                }
            } else if (inU) {
                // inside S
                int du = distC[u], dv = distC[v];
                if (forward) {
                    // toward c: farther -> closer
                    if (du > dv) { from = u; to = v; }
                    else if (du < dv) { from = v; to = u; }
                    else { if (rng.next_bool()) { from = u; to = v; } else { from = v; to = u; } }
                } else {
                    // away from c: closer -> farther
                    if (du < dv) { from = u; to = v; }
                    else if (du > dv) { from = v; to = u; }
                    else { if (rng.next_bool()) { from = u; to = v; } else { from = v; to = u; } }
                }
            } else {
                // inside T
                int du = distP[u], dv = distP[v];
                if (forward) {
                    // away from p: closer -> farther
                    if (du < dv) { from = u; to = v; }
                    else if (du > dv) { from = v; to = u; }
                    else { if (rng.next_bool()) { from = u; to = v; } else { from = v; to = u; } }
                } else {
                    // toward p: farther -> closer
                    if (du > dv) { from = u; to = v; }
                    else if (du < dv) { from = v; to = u; }
                    else { if (rng.next_bool()) { from = u; to = v; } else { from = v; to = u; } }
                }
            }

            // encode
            dir[i] = (uint8_t)((from == U[i] && to == V[i]) ? 0 : 1);
        }
    };

    auto ask_query = [&](const vector<uint8_t> &dir) -> int {
        string out;
        out.reserve((size_t)2 * M + 4);
        out.push_back('0');
        for (int i = 0; i < M; i++) {
            out.push_back(' ');
            out.push_back(char('0' + dir[i]));
        }
        out.push_back('\n');
        cout << out;
        cout.flush();
        int x;
        if (!(cin >> x)) exit(0);
        return x;
    };

    auto output_answer = [&](int A, int B) {
        cout << "1 " << A << " " << B << "\n";
        cout.flush();
        exit(0);
    };

    auto apply_update = [&](const EvalData &best, int ans) {
        vector<int> newActive;
        newActive.reserve(active.size());
        uint64_t newTotal = 0;

        for (int a : active) {
            uint64_t *row = &cand[(size_t)a * words];
            const uint64_t *ra = &best.reach[(size_t)best.comp[a] * words];
            uint64_t any = 0;
            for (int w = 0; w < words; w++) {
                uint64_t val;
                if (ans == 1) val = row[w] & ra[w];
                else val = row[w] & ~ra[w];
                if (w == words - 1) val &= lastMask;
                row[w] = val;
                any |= val;
                newTotal += (uint64_t)pop64(val);
            }
            row[a / 64] &= ~(1ULL << (a % 64));
            // clearing self bit might have changed any/newTotal by at most 1; fix conservatively
            // (self bit should already be 0; but keep correctness)
            if (any) {
                // recompute any if self bit was the only one
                if ((any == (1ULL << (a % 64))) && (a / 64 == words - 1 ? ((row[a / 64] & lastMask) == 0) : (row[a / 64] == 0))) {
                    uint64_t check = 0;
                    for (int w = 0; w < words; w++) check |= row[w];
                    if (check) newActive.push_back(a);
                } else {
                    uint64_t check = 0;
                    for (int w = 0; w < words; w++) check |= row[w];
                    if (check) newActive.push_back(a);
                }
            } else {
                // row might still have bits after masking/clearing; verify
                uint64_t check = 0;
                for (int w = 0; w < words; w++) check |= row[w];
                if (check) newActive.push_back(a);
            }
        }

        active.swap(newActive);
        totalC = newTotal;
    };

    int queries = 0;
    while (queries < 600) {
        if (totalC == 1) break;

        int maxTries;
        if (totalC > 20000000ULL) maxTries = 6;
        else if (totalC > 200000ULL) maxTries = 4;
        else maxTries = 3;
        if (totalC <= 5000ULL) maxTries = 10;

        EvalData best, temp;
        bool haveBest = false;

        for (int t = 0; t < maxTries; t++) {
            int type = (int)(rng.next() % 100ULL);
            if (type < 40) {
                bool forward = rng.next_bool();
                gen_cut(temp.dir, forward);
            } else if (type < 70) {
                gen_perm(temp.dir);
            } else {
                gen_random(temp.dir);
            }

            evaluate(temp);
            if (temp.count1 == 0 || temp.count1 == totalC) continue;
            if (!haveBest || temp.worst < best.worst) {
                best = std::move(temp);
                temp.clear();
                haveBest = true;
                if (best.worst * 10ULL <= totalC * 7ULL) break; // <= 70% remaining worst-case
            }
        }

        if (!haveBest) {
            // Fallback: keep sampling until non-trivial or give up.
            for (int t = 0; t < 25 && !haveBest; t++) {
                gen_random(temp.dir);
                evaluate(temp);
                if (temp.count1 != 0 && temp.count1 != totalC) {
                    best = std::move(temp);
                    temp.clear();
                    haveBest = true;
                    break;
                }
            }
        }

        if (!haveBest) {
            // As last resort, just ask a random query (may not shrink, but should be rare).
            best.dir.clear();
            gen_random(best.dir);
            evaluate(best);
        }

        int ans = ask_query(best.dir);
        apply_update(best, ans);
        queries++;
    }

    // Extract answer from candidates
    int A = -1, B = -1;
    for (int a = 0; a < N; a++) {
        const uint64_t *row = &cand[(size_t)a * words];
        for (int w = 0; w < words; w++) {
            uint64_t x = row[w];
            if (x) {
                int b = (w << 6) + ctz64(x);
                if (b < N && b != a) {
                    A = a;
                    B = b;
                    break;
                }
            }
        }
        if (A != -1) break;
    }
    if (A == -1) {
        // Should not happen; fallback to something valid
        A = 0;
        B = 1;
    }
    output_answer(A, B);
    return 0;
}