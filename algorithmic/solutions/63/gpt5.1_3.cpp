#include <bits/stdc++.h>
using namespace std;

int N, M;
vector<int> U_, V_;
vector<vector<int>> adj;
vector<int> idx_, low_, compOf, st;
vector<char> onStack;
int idxCounter, compCnt;

void dfs_scc(int v) {
    idx_[v] = low_[v] = idxCounter++;
    st.push_back(v);
    onStack[v] = 1;
    for (int to : adj[v]) {
        if (idx_[to] == -1) {
            dfs_scc(to);
            low_[v] = min(low_[v], low_[to]);
        } else if (onStack[to]) {
            low_[v] = min(low_[v], idx_[to]);
        }
    }
    if (low_[v] == idx_[v]) {
        while (true) {
            int x = st.back();
            st.pop_back();
            onStack[x] = 0;
            compOf[x] = compCnt;
            if (x == v) break;
        }
        compCnt++;
    }
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    if (!(cin >> N >> M)) return 0;
    U_.resize(M);
    V_.resize(M);
    for (int i = 0; i < M; ++i) {
        cin >> U_[i] >> V_[i];
    }

    int W = (N + 63) / 64;
    uint64_t lastMask = (N % 64) ? ((1ULL << (N % 64)) - 1) : ~0ULL;

    // Candidate matrix: cand[a][b] == 1 if pair (a,b) is still possible
    vector<vector<uint64_t>> cand(N, vector<uint64_t>(W, ~0ULL));
    for (int i = 0; i < N; ++i) {
        cand[i][W - 1] &= lastMask;
    }
    for (int i = 0; i < N; ++i) {
        cand[i][i >> 6] &= ~(1ULL << (i & 63)); // A != B
    }
    long long pairCount = 1LL * N * (N - 1);

    // Structures for SCC and component DAG
    adj.assign(N, vector<int>());
    idx_.assign(N, -1);
    low_.assign(N, 0);
    compOf.assign(N, -1);
    onStack.assign(N, 0);
    st.reserve(N);

    vector<vector<uint64_t>> compVerts(N, vector<uint64_t>(W));
    vector<vector<uint64_t>> compReach(N, vector<uint64_t>(W));
    vector<vector<int>> cadj(N);
    vector<int> indeg(N);
    vector<int> topo;
    vector<int> dir(M);

    mt19937_64 rng(
        (unsigned long long)chrono::steady_clock::now().time_since_epoch().count()
    );

    const int MAX_QUERIES = 100;

    for (int q = 0; q < MAX_QUERIES && pairCount > 1; ++q) {
        // Random orientation for each edge
        for (int i = 0; i < M; ++i) {
            dir[i] = (int)(rng() & 1ULL);
        }

        // Output query
        cout << 0;
        for (int i = 0; i < M; ++i) {
            cout << ' ' << dir[i];
        }
        cout << '\n';
        cout.flush();

        int ans;
        if (!(cin >> ans)) return 0;
        if (ans != 0 && ans != 1) return 0;

        // Build directed graph according to orientation
        for (int i = 0; i < N; ++i) adj[i].clear();
        for (int i = 0; i < M; ++i) {
            int u = U_[i], v = V_[i];
            if (dir[i] == 0) {
                adj[u].push_back(v);
            } else {
                adj[v].push_back(u);
            }
        }

        // Tarjan SCC
        fill(idx_.begin(), idx_.end(), -1);
        fill(low_.begin(), low_.end(), 0);
        fill(compOf.begin(), compOf.end(), -1);
        fill(onStack.begin(), onStack.end(), 0);
        st.clear();
        idxCounter = 0;
        compCnt = 0;
        for (int v = 0; v < N; ++v) {
            if (idx_[v] == -1) dfs_scc(v);
        }

        int C = compCnt;

        // Build component DAG
        for (int c = 0; c < C; ++c) {
            cadj[c].clear();
            indeg[c] = 0;
        }
        for (int u = 0; u < N; ++u) {
            int cu = compOf[u];
            for (int v : adj[u]) {
                int cv = compOf[v];
                if (cu != cv) {
                    cadj[cu].push_back(cv);
                    indeg[cv]++;
                }
            }
        }

        // Topological order of components
        topo.clear();
        topo.reserve(C);
        deque<int> dq;
        for (int c = 0; c < C; ++c) {
            if (indeg[c] == 0) dq.push_back(c);
        }
        while (!dq.empty()) {
            int c = dq.front();
            dq.pop_front();
            topo.push_back(c);
            for (int to : cadj[c]) {
                if (--indeg[to] == 0) dq.push_back(to);
            }
        }

        // Initialize component vertex bitsets
        for (int c = 0; c < C; ++c) {
            fill(compVerts[c].begin(), compVerts[c].end(), 0);
        }
        for (int v = 0; v < N; ++v) {
            int c = compOf[v];
            compVerts[c][v >> 6] |= 1ULL << (v & 63);
        }
        // Copy to compReach
        for (int c = 0; c < C; ++c) {
            auto &src = compVerts[c];
            auto &dst = compReach[c];
            for (int wi = 0; wi < W; ++wi) dst[wi] = src[wi];
        }

        // DP on DAG to compute reachable vertex sets per component
        for (int ti = C - 1; ti >= 0; --ti) {
            int c = topo[ti];
            auto &rc = compReach[c];
            for (int to : cadj[c]) {
                auto &rt = compReach[to];
                for (int wi = 0; wi < W; ++wi) {
                    rc[wi] |= rt[wi];
                }
            }
        }

        // Update candidate pairs according to answer
        for (int a = 0; a < N; ++a) {
            auto &row = cand[a];
            auto &rc = compReach[compOf[a]];
            if (ans == 1) {
                for (int wi = 0; wi < W - 1; ++wi) {
                    row[wi] &= rc[wi];
                }
                row[W - 1] &= rc[W - 1] & lastMask;
            } else {
                for (int wi = 0; wi < W - 1; ++wi) {
                    row[wi] &= ~rc[wi];
                }
                row[W - 1] &= (~rc[W - 1]) & lastMask;
            }
        }

        // Recompute pairCount
        long long newCount = 0;
        for (int a = 0; a < N; ++a) {
            for (int wi = 0; wi < W; ++wi) {
                newCount += __builtin_popcountll(cand[a][wi]);
            }
        }
        pairCount = newCount;
        if (pairCount <= 1) break;
    }

    // Decode remaining candidate pair
    int A = -1, B = -1;
    for (int a = 0; a < N; ++a) {
        for (int wi = 0; wi < W; ++wi) {
            uint64_t w = cand[a][wi];
            if (w) {
                int bit = __builtin_ctzll(w);
                int b = wi * 64 + bit;
                if (b < N) {
                    A = a;
                    B = b;
                    break;
                }
            }
        }
        if (A != -1) break;
    }
    if (A == -1) {
        A = 0;
        B = (N > 1 ? 1 : 0);
    }

    cout << 1 << ' ' << A << ' ' << B << '\n';
    cout.flush();
    return 0;
}