#include <bits/stdc++.h>
using namespace std;

static const int DIRS = 4;
static const int dr[DIRS] = {0, 0, -1, 1};
static const int dc[DIRS] = {-1, 1, 0, 0};
static const char dch[DIRS] = {'L', 'R', 'U', 'D'};
static const int oppDir[DIRS] = {1, 0, 3, 2};

static inline int pairIndex(int a, int b, int N) {
    if (a > b) std::swap(a, b);
    // count pairs (i,j) with i < a: sum_{i=0}^{a-1} (N-i) = a*N - a*(a-1)/2
    return a * N - (a * (a - 1)) / 2 + (b - a);
}

static string shortestPath(
    int N, int src, int dst,
    const array<vector<uint16_t>, DIRS>& nxt
) {
    if (src == dst) return "";
    vector<int> par(N, -1);
    vector<int> pdir(N, -1);
    queue<int> q;
    par[src] = src;
    q.push(src);
    while (!q.empty()) {
        int u = q.front(); q.pop();
        for (int d = 0; d < DIRS; d++) {
            int v = (int)nxt[d][u];
            if (v == u) continue;
            if (par[v] != -1) continue;
            par[v] = u;
            pdir[v] = d;
            if (v == dst) {
                while (!q.empty()) q.pop();
                break;
            }
            q.push(v);
        }
    }
    if (par[dst] == -1) return ""; // should not happen in connected component
    string path;
    int cur = dst;
    while (cur != src) {
        int d = pdir[cur];
        path.push_back(dch[d]);
        cur = par[cur];
    }
    reverse(path.begin(), path.end());
    return path;
}

static inline void applyWordToSet(
    vector<uint16_t>& S,
    const string& w,
    const array<vector<uint16_t>, DIRS>& nxt,
    const array<int, 256>& cmap
) {
    for (char c : w) {
        int d = cmap[(unsigned char)c];
        for (uint16_t &x : S) x = nxt[d][x];
    }
}

static inline int applyWordToState(
    int s,
    const string& w,
    const array<vector<uint16_t>, DIRS>& nxt,
    const array<int, 256>& cmap
) {
    uint16_t x = (uint16_t)s;
    for (char c : w) x = nxt[cmap[(unsigned char)c]][x];
    return (int)x;
}

static bool isResetWordToSingle(
    int N,
    const string& w,
    const array<vector<uint16_t>, DIRS>& nxt,
    const array<int, 256>& cmap,
    int &singleState
) {
    vector<uint16_t> cur(N);
    for (int i = 0; i < N; i++) cur[i] = (uint16_t)i;
    applyWordToSet(cur, w, nxt, cmap);
    uint16_t x = cur[0];
    for (int i = 1; i < N; i++) if (cur[i] != x) return false;
    singleState = (int)x;
    return true;
}

static bool verifyResetToExit(
    int N,
    int exitId,
    const string& R,
    const array<vector<uint16_t>, DIRS>& nxt,
    const array<int, 256>& cmap
) {
    for (int s = 0; s < N; s++) {
        int end = applyWordToState(s, R, nxt, cmap);
        if (end != exitId) return false;
    }
    return true;
}

static string buildTourFromRoot(
    int N,
    int root,
    const array<vector<uint16_t>, DIRS>& nxt
) {
    vector<char> vis(N, 0);
    vector<int> parent(N, -1);
    vector<int> pdir(N, -1);
    vector<vector<int>> children(N);

    queue<int> q;
    vis[root] = 1;
    parent[root] = root;
    q.push(root);

    while (!q.empty()) {
        int u = q.front(); q.pop();
        for (int d = 0; d < DIRS; d++) {
            int v = (int)nxt[d][u];
            if (v == u) continue;
            if (vis[v]) continue;
            vis[v] = 1;
            parent[v] = u;
            pdir[v] = d;
            children[u].push_back(v);
            q.push(v);
        }
    }

    // If not all visited, graph not connected; return empty to indicate failure.
    for (int i = 0; i < N; i++) if (!vis[i]) return string();

    string tour;
    tour.reserve(max(0, 2 * (N - 1)));

    function<void(int)> dfs = [&](int u) {
        for (int v : children[u]) {
            int d = pdir[v];
            tour.push_back(dch[d]);
            dfs(v);
            tour.push_back(dch[oppDir[d]]);
        }
    };

    dfs(root);
    return tour;
}

static vector<string> makeHeuristicCandidates(int n, int m) {
    int U = n, D = n, L = m, R = m;

    auto rep = [&](char c, int k) {
        return string(max(0, k), c);
    };

    vector<string> cand;
    cand.reserve(200);

    // Simple corner pushes (long enough to clamp)
    cand.push_back(rep('U', U) + rep('L', L));
    cand.push_back(rep('U', U) + rep('R', R));
    cand.push_back(rep('D', D) + rep('L', L));
    cand.push_back(rep('D', D) + rep('R', R));

    string sweep1 = rep('U', U) + rep('L', L) + rep('D', D) + rep('R', R);
    string sweep2 = rep('U', U) + rep('R', R) + rep('D', D) + rep('L', L);
    string sweep3 = rep('L', L) + rep('U', U) + rep('R', R) + rep('D', D);
    string sweep4 = rep('R', R) + rep('U', U) + rep('L', L) + rep('D', D);

    for (int k = 1; k <= 50; k++) {
        string w;
        w.reserve(sweep1.size() * k);
        for (int i = 0; i < k; i++) w += sweep1;
        cand.push_back(w);
    }
    for (int k = 1; k <= 30; k++) {
        string w;
        w.reserve(sweep2.size() * k);
        for (int i = 0; i < k; i++) w += sweep2;
        cand.push_back(w);
    }
    for (int k = 1; k <= 20; k++) {
        string w;
        w.reserve(sweep3.size() * k);
        for (int i = 0; i < k; i++) w += sweep3;
        cand.push_back(w);
    }
    for (int k = 1; k <= 20; k++) {
        string w;
        w.reserve(sweep4.size() * k);
        for (int i = 0; i < k; i++) w += sweep4;
        cand.push_back(w);
    }

    // ULDR repeats
    for (int k = 1; k <= 2000; k += 50) {
        string w;
        w.reserve(4 * k);
        for (int i = 0; i < k; i++) {
            w.push_back('U'); w.push_back('L'); w.push_back('D'); w.push_back('R');
        }
        cand.push_back(w);
    }

    return cand;
}

static bool greedySync(
    int N,
    const array<vector<uint16_t>, DIRS>& nxt,
    string &syncWord,
    int &finalState,
    int maxSteps = 50000
) {
    vector<int> seenAt(N, -1);
    int iter = 0;

    vector<uint16_t> S(N);
    for (int i = 0; i < N; i++) S[i] = (uint16_t)i;

    auto dedup = [&]() {
        iter++;
        vector<uint16_t> ns;
        ns.reserve(S.size());
        for (uint16_t x : S) {
            if (seenAt[x] != iter) {
                seenAt[x] = iter;
                ns.push_back(x);
            }
        }
        S.swap(ns);
    };

    dedup();
    if (S.size() == 1) {
        finalState = (int)S[0];
        syncWord.clear();
        return true;
    }

    syncWord.clear();
    syncWord.reserve(min(500000, maxSteps));

    int noImprove = 0;
    for (int step = 0; step < maxSteps; step++) {
        if (S.size() == 1) break;

        size_t bestSize = SIZE_MAX;
        int bestD = 0;

        // Evaluate each single-letter move
        for (int d = 0; d < DIRS; d++) {
            iter++;
            size_t sz = 0;
            for (uint16_t x : S) {
                uint16_t y = nxt[d][x];
                if (seenAt[y] != iter) {
                    seenAt[y] = iter;
                    sz++;
                }
            }
            if (sz < bestSize) {
                bestSize = sz;
                bestD = d;
            }
        }

        size_t before = S.size();
        for (uint16_t &x : S) x = nxt[bestD][x];
        dedup();
        syncWord.push_back(dch[bestD]);

        if (S.size() < before) noImprove = 0;
        else if (++noImprove > 5000) break; // avoid stalling too long

        if ((int)syncWord.size() > 500000) break;
    }

    if (S.size() == 1) {
        finalState = (int)S[0];
        return true;
    }
    return false;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n, m;
    cin >> n >> m;
    vector<string> g(n);
    for (int i = 0; i < n; i++) cin >> g[i];

    int sr, sc, er, ec;
    cin >> sr >> sc >> er >> ec;
    --sr; --sc; --er; --ec;

    vector<vector<int>> id(n, vector<int>(m, -1));
    vector<pair<int,int>> coord;
    coord.reserve(n*m);

    for (int i = 0; i < n; i++) for (int j = 0; j < m; j++) {
        if (g[i][j] == '1') {
            id[i][j] = (int)coord.size();
            coord.push_back({i,j});
        }
    }

    int N = (int)coord.size();
    if (N == 0) {
        cout << "-1\n";
        return 0;
    }

    int startId = id[sr][sc];
    int exitId = id[er][ec];
    if (startId < 0 || exitId < 0) {
        cout << "-1\n";
        return 0;
    }

    // Connectivity check from start (must reach all blank cells)
    vector<char> vis(N, 0);
    queue<int> q;
    vis[startId] = 1;
    q.push(startId);
    while (!q.empty()) {
        int u = q.front(); q.pop();
        auto [r,c] = coord[u];
        for (int d = 0; d < DIRS; d++) {
            int nr = r + dr[d], nc = c + dc[d];
            if (nr < 0 || nr >= n || nc < 0 || nc >= m) continue;
            if (id[nr][nc] < 0) continue;
            int v = id[nr][nc];
            if (!vis[v]) {
                vis[v] = 1;
                q.push(v);
            }
        }
    }
    for (int i = 0; i < N; i++) {
        if (!vis[i]) {
            cout << "-1\n";
            return 0;
        }
    }

    array<int, 256> cmap;
    cmap.fill(-1);
    cmap[(unsigned char)'L'] = 0;
    cmap[(unsigned char)'R'] = 1;
    cmap[(unsigned char)'U'] = 2;
    cmap[(unsigned char)'D'] = 3;

    // Build transition table for commands
    array<vector<uint16_t>, DIRS> nxt;
    for (int d = 0; d < DIRS; d++) nxt[d].assign(N, 0);

    for (int u = 0; u < N; u++) {
        auto [r,c] = coord[u];
        for (int d = 0; d < DIRS; d++) {
            int nr = r + dr[d], nc = c + dc[d];
            if (nr < 0 || nr >= n || nc < 0 || nc >= m) {
                nxt[d][u] = (uint16_t)u;
            } else {
                int v = id[nr][nc];
                if (v < 0) nxt[d][u] = (uint16_t)u;
                else nxt[d][u] = (uint16_t)v;
            }
        }
    }

    // Build tour rooted at exit
    string tour = buildTourFromRoot(N, exitId, nxt);
    if ((int)tour.size() == 0 && N > 1) {
        cout << "-1\n";
        return 0;
    }

    // Find reset word to exit: R maps any state to exitId
    string Rword;

    // 1) Heuristic candidates
    {
        auto cand = makeHeuristicCandidates(n, m);
        for (const string &w : cand) {
            int single = -1;
            if (!isResetWordToSingle(N, w, nxt, cmap, single)) continue;
            string pathToExit = shortestPath(N, single, exitId, nxt);
            string R = w + pathToExit;
            if (verifyResetToExit(N, exitId, R, nxt, cmap)) {
                Rword = std::move(R);
                break;
            }
        }
    }

    // 2) Greedy synchronization if heuristics failed
    if (Rword.empty()) {
        string syncW;
        int single = -1;
        if (greedySync(N, nxt, syncW, single, 50000)) {
            string pathToExit = shortestPath(N, single, exitId, nxt);
            string R = syncW + pathToExit;
            if (verifyResetToExit(N, exitId, R, nxt, cmap)) {
                Rword = std::move(R);
            }
        }
    }

    // 3) Exact synchronization via pair BFS if still needed
    if (Rword.empty()) {
        int numPairs = N * (N + 1) / 2;

        // Incoming edge lists using arrays as linked lists
        vector<int> head(numPairs, -1);
        vector<int> ePre;
        vector<int> eNext;
        vector<uint8_t> eDir;
        ePre.reserve(4LL * numPairs);
        eNext.reserve(4LL * numPairs);
        eDir.reserve(4LL * numPairs);

        auto addEdge = [&](int toPair, int prePair, int dir) {
            int idEdge = (int)ePre.size();
            ePre.push_back(prePair);
            eDir.push_back((uint8_t)dir);
            eNext.push_back(head[toPair]);
            head[toPair] = idEdge;
        };

        for (int a = 0; a < N; a++) {
            for (int b = a; b < N; b++) {
                int preIdx = pairIndex(a, b, N);
                for (int d = 0; d < DIRS; d++) {
                    int na = nxt[d][a];
                    int nb = nxt[d][b];
                    if (na > nb) std::swap(na, nb);
                    int toIdx = pairIndex(na, nb, N);
                    addEdge(toIdx, preIdx, d);
                }
            }
        }

        vector<int> dist(numPairs, -1);
        vector<int> parentNext(numPairs, -1);
        vector<uint8_t> parentDir(numPairs, 255);
        queue<int> qbfs;

        for (int i = 0; i < N; i++) {
            int idx = pairIndex(i, i, N);
            dist[idx] = 0;
            qbfs.push(idx);
        }

        while (!qbfs.empty()) {
            int cur = qbfs.front(); qbfs.pop();
            int nd = dist[cur] + 1;
            for (int e = head[cur]; e != -1; e = eNext[e]) {
                int pre = ePre[e];
                if (dist[pre] != -1) continue;
                dist[pre] = nd;
                parentNext[pre] = cur;
                parentDir[pre] = eDir[e];
                qbfs.push(pre);
            }
        }

        for (int i = 0; i < numPairs; i++) {
            if (dist[i] == -1) {
                cout << "-1\n";
                return 0;
            }
        }

        auto mergeWordForPairIdx = [&](int idx) -> string {
            int len = dist[idx];
            string w;
            w.reserve(len);
            while (dist[idx] > 0) {
                uint8_t d = parentDir[idx];
                w.push_back(dch[d]);
                idx = parentNext[idx];
            }
            return w;
        };

        vector<int> seenAt(N, -1);
        int iter = 0;

        vector<uint16_t> S;
        S.reserve(N);
        for (int i = 0; i < N; i++) S.push_back((uint16_t)i);

        auto dedupS = [&]() {
            iter++;
            vector<uint16_t> ns;
            ns.reserve(S.size());
            for (uint16_t x : S) {
                if (seenAt[x] != iter) {
                    seenAt[x] = iter;
                    ns.push_back(x);
                }
            }
            S.swap(ns);
        };
        dedupS();

        string syncWord;
        syncWord.reserve(200000);

        while (S.size() > 1) {
            int k = (int)S.size();
            int lim = min(10, k);

            int bestP = (int)S[0], bestQ = (int)S[1];
            int bestLen = INT_MAX;

            for (int i = 0; i < lim; i++) {
                int p = (int)S[i];
                int localBestLen = INT_MAX;
                int localBestQ = -1;
                for (int j = 0; j < k; j++) {
                    int qv = (int)S[j];
                    if (qv == p) continue;
                    int idx = pairIndex(p, qv, N);
                    int d = dist[idx];
                    if (d >= 0 && d < localBestLen) {
                        localBestLen = d;
                        localBestQ = qv;
                        if (d == 0) break;
                    }
                }
                if (localBestQ != -1 && localBestLen < bestLen) {
                    bestLen = localBestLen;
                    bestP = p;
                    bestQ = localBestQ;
                }
            }

            int idx = pairIndex(bestP, bestQ, N);
            string mw = mergeWordForPairIdx(idx);

            syncWord += mw;
            applyWordToSet(S, mw, nxt, cmap);
            dedupS();

            if ((int)syncWord.size() > 500000) {
                cout << "-1\n";
                return 0;
            }
        }

        int singleState = (int)S[0];
        string pathToExit = shortestPath(N, singleState, exitId, nxt);
        Rword = syncWord + pathToExit;

        if (!verifyResetToExit(N, exitId, Rword, nxt, cmap)) {
            cout << "-1\n";
            return 0;
        }
    }

    string W = Rword + tour;
    if ((long long)W.size() * 2LL > 1000000LL) {
        cout << "-1\n";
        return 0;
    }

    string revW = W;
    reverse(revW.begin(), revW.end());
    string ans;
    ans.reserve(revW.size() + W.size());
    ans += revW;
    ans += W;

    cout << ans << "\n";
    return 0;
}