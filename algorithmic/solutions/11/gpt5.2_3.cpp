#include <bits/stdc++.h>
using namespace std;

static inline int dirIdx(char c) {
    switch (c) {
        case 'L': return 0;
        case 'R': return 1;
        case 'U': return 2;
        case 'D': return 3;
    }
    return -1;
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
    vector<pair<int,int>> pos;
    pos.reserve(n * m);

    for (int r = 0; r < n; r++) for (int c = 0; c < m; c++) {
        if (g[r][c] == '1') {
            id[r][c] = (int)pos.size();
            pos.push_back({r, c});
        }
    }

    int N = (int)pos.size();
    int sIdx = id[sr][sc];
    int eIdx = id[er][ec];

    if (N == 1) {
        // Only one blank cell; start and exit are guaranteed blank, thus same cell.
        cout << "\n";
        return 0;
    }

    if (sIdx < 0 || eIdx < 0) {
        cout << "-1\n";
        return 0;
    }

    // Precompute transitions
    const array<char, 4> DCH = {'L','R','U','D'};
    const array<int, 4> dr = {0, 0, -1, 1};
    const array<int, 4> dc = {-1, 1, 0, 0};
    const array<int, 4> opp = {1, 0, 3, 2};

    vector<array<int,4>> nxt(N);
    for (int i = 0; i < N; i++) {
        auto [r, c] = pos[i];
        for (int d = 0; d < 4; d++) {
            int nr = r + dr[d], nc = c + dc[d];
            if (0 <= nr && nr < n && 0 <= nc && nc < m && g[nr][nc] == '1') {
                nxt[i][d] = id[nr][nc];
            } else {
                nxt[i][d] = i;
            }
        }
    }

    // Connectivity check: all blanks must be in one component
    {
        vector<uint8_t> vis(N, 0);
        vector<int> q;
        q.reserve(N);
        vis[sIdx] = 1;
        q.push_back(sIdx);
        for (size_t qi = 0; qi < q.size(); qi++) {
            int v = q[qi];
            for (int d = 0; d < 4; d++) {
                int u = nxt[v][d];
                if (u != v && !vis[u]) {
                    vis[u] = 1;
                    q.push_back(u);
                }
            }
        }
        if ((int)q.size() != N) {
            cout << "-1\n";
            return 0;
        }
    }

    // Build inverse transitions invPred[target][dir] has up to 2 predecessors
    vector<array<array<int,2>,4>> invPred(N);
    vector<array<uint8_t,4>> invCnt(N);
    for (int i = 0; i < N; i++) invCnt[i].fill(0);

    for (int u = 0; u < N; u++) {
        for (int d = 0; d < 4; d++) {
            int v = nxt[u][d];
            uint8_t &cnt = invCnt[v][d];
            if (cnt >= 2) {
                // Should never happen for this grid movement model
                // but keep safe.
                // We'll ignore extra, but that might break correctness.
                continue;
            }
            invPred[v][d][cnt++] = u;
        }
    }

    auto pairId = [N](int a, int b) -> int {
        if (a > b) std::swap(a, b);
        // offset = a*N - a*(a-1)/2
        return a * N - (a * (a - 1)) / 2 + (b - a);
    };

    int64_t Np64 = 1LL * N * (N + 1) / 2;
    if (Np64 > 2000000) { // safety
        cout << "-1\n";
        return 0;
    }
    int Np = (int)Np64;

    // Precompute pair endpoints
    vector<uint16_t> pairA(Np), pairB(Np);
    for (int a = 0; a < N; a++) {
        int offset = a * N - (a * (a - 1)) / 2;
        for (int b = a; b < N; b++) {
            int pid = offset + (b - a);
            pairA[pid] = (uint16_t)a;
            pairB[pid] = (uint16_t)b;
        }
    }

    // Reverse BFS on pair automaton to get shortest merge word for any pair
    vector<uint8_t> visPair(Np, 0);
    vector<int> distPair(Np, -1);
    vector<int> parentPair(Np, -1);
    vector<uint8_t> actPair(Np, 0);

    vector<int> qPair;
    qPair.reserve(Np);

    for (int i = 0; i < N; i++) {
        int pid = pairId(i, i);
        visPair[pid] = 1;
        distPair[pid] = 0;
        parentPair[pid] = pid;
        qPair.push_back(pid);
    }

    for (size_t qi = 0; qi < qPair.size(); qi++) {
        int curId = qPair[qi];
        int x = pairA[curId];
        int y = pairB[curId];
        int curDist = distPair[curId];

        for (int d = 0; d < 4; d++) {
            // predecessors where next[p]=x and next[q]=y
            for (int ip = 0; ip < (int)invCnt[x][d]; ip++) {
                int p = invPred[x][d][ip];
                for (int iq = 0; iq < (int)invCnt[y][d]; iq++) {
                    int qv = invPred[y][d][iq];
                    int pid = pairId(p, qv);
                    if (!visPair[pid]) {
                        visPair[pid] = 1;
                        distPair[pid] = curDist + 1;
                        parentPair[pid] = curId;
                        actPair[pid] = (uint8_t)d;
                        qPair.push_back(pid);
                    }
                }
            }
            if (x != y) {
                // swapped target (because pairs are unordered)
                for (int ip = 0; ip < (int)invCnt[y][d]; ip++) {
                    int p = invPred[y][d][ip];
                    for (int iq = 0; iq < (int)invCnt[x][d]; iq++) {
                        int qv = invPred[x][d][iq];
                        int pid = pairId(p, qv);
                        if (!visPair[pid]) {
                            visPair[pid] = 1;
                            distPair[pid] = curDist + 1;
                            parentPair[pid] = curId;
                            actPair[pid] = (uint8_t)d;
                            qPair.push_back(pid);
                        }
                    }
                }
            }
        }
    }

    if ((int)qPair.size() != Np) {
        cout << "-1\n";
        return 0;
    }

    auto mergeWord = [&](int a, int b) -> string {
        int pid = pairId(a, b);
        if (distPair[pid] < 0) return string();
        string w;
        w.reserve((size_t)distPair[pid]);
        while (pairA[pid] != pairB[pid]) {
            uint8_t d = actPair[pid];
            w.push_back(DCH[d]);
            pid = parentPair[pid];
        }
        return w;
    };

    auto applyWordToSet = [&](const vector<int>& S, const string& w) -> vector<int> {
        vector<int> res;
        res.reserve(S.size());
        for (int s : S) {
            int cur = s;
            for (char c : w) cur = nxt[cur][dirIdx(c)];
            res.push_back(cur);
        }
        sort(res.begin(), res.end());
        res.erase(unique(res.begin(), res.end()), res.end());
        return res;
    };

    auto apply1 = [&](const vector<int>& S, int d) -> vector<int> {
        vector<int> res;
        res.reserve(S.size());
        for (int s : S) res.push_back(nxt[s][d]);
        sort(res.begin(), res.end());
        res.erase(unique(res.begin(), res.end()), res.end());
        return res;
    };

    auto apply2 = [&](const vector<int>& S, int d1, int d2) -> vector<int> {
        vector<int> res;
        res.reserve(S.size());
        for (int s : S) res.push_back(nxt[nxt[s][d1]][d2]);
        sort(res.begin(), res.end());
        res.erase(unique(res.begin(), res.end()), res.end());
        return res;
    };

    // Build synchronizing word Wsync that maps all states to a single state u
    vector<int> Sstates(N);
    iota(Sstates.begin(), Sstates.end(), 0);

    string Wsync;
    Wsync.reserve(200000);

    // soft limit to keep final answer under 1e6:
    const int SOFT_W_LIMIT = 495000;

    while (Sstates.size() > 1) {
        if ((int)Wsync.size() > SOFT_W_LIMIT) {
            cout << "-1\n";
            return 0;
        }

        // Greedy compression with length 1
        int bestD = -1;
        vector<int> bestImg;
        size_t bestSz = Sstates.size();
        for (int d = 0; d < 4; d++) {
            auto img = apply1(Sstates, d);
            if (img.size() < bestSz) {
                bestSz = img.size();
                bestD = d;
                bestImg.swap(img);
            }
        }
        if (bestD != -1 && bestSz < Sstates.size()) {
            Wsync.push_back(DCH[bestD]);
            Sstates.swap(bestImg);
            continue;
        }

        // Greedy compression with length 2
        int bestD1 = -1, bestD2 = -1;
        vector<int> bestImg2;
        bestSz = Sstates.size();
        for (int d1 = 0; d1 < 4; d1++) {
            for (int d2 = 0; d2 < 4; d2++) {
                auto img = apply2(Sstates, d1, d2);
                if (img.size() < bestSz) {
                    bestSz = img.size();
                    bestD1 = d1; bestD2 = d2;
                    bestImg2.swap(img);
                }
            }
        }
        if (bestD1 != -1 && bestSz < Sstates.size()) {
            Wsync.push_back(DCH[bestD1]);
            Wsync.push_back(DCH[bestD2]);
            Sstates.swap(bestImg2);
            continue;
        }

        // Pair merge step
        int a = Sstates[0];
        int bestB = -1;
        int bestDist = INT_MAX;
        for (size_t i = 1; i < Sstates.size(); i++) {
            int b = Sstates[i];
            int pid = pairId(a, b);
            int d = distPair[pid];
            if (d >= 0 && d < bestDist) {
                bestDist = d;
                bestB = b;
            }
        }
        if (bestB == -1) {
            cout << "-1\n";
            return 0;
        }
        string w = mergeWord(a, bestB);
        if (w.empty()) {
            cout << "-1\n";
            return 0;
        }
        Wsync += w;
        Sstates = applyWordToSet(Sstates, w);
    }

    int u = Sstates[0];

    // Shortest path Q from u to exit eIdx (ordinary adjacency)
    string Q;
    {
        vector<int> par(N, -1);
        vector<char> parMove(N, 0);
        deque<int> dq;
        par[u] = u;
        dq.push_back(u);
        while (!dq.empty()) {
            int v = dq.front(); dq.pop_front();
            if (v == eIdx) break;
            for (int d = 0; d < 4; d++) {
                int to = nxt[v][d];
                if (to == v) continue;
                if (par[to] == -1) {
                    par[to] = v;
                    parMove[to] = DCH[d];
                    dq.push_back(to);
                }
            }
        }
        if (par[eIdx] == -1) {
            cout << "-1\n";
            return 0;
        }
        string rev;
        int cur = eIdx;
        while (cur != u) {
            rev.push_back(parMove[cur]);
            cur = par[cur];
        }
        reverse(rev.begin(), rev.end());
        Q = rev;
    }

    string suffix = Wsync + Q;
    string prefix(suffix.rbegin(), suffix.rend());

    // Compute p = state after applying prefix from start
    int p = sIdx;
    for (char c : prefix) p = nxt[p][dirIdx(c)];

    // Build DFS tour X starting at p visiting all blank cells (in this connected component)
    string X;
    X.reserve((size_t)2 * (N - 1));
    vector<uint8_t> visDfs(N, 0);

    function<void(int)> dfs = [&](int v) {
        visDfs[v] = 1;
        for (int d = 0; d < 4; d++) {
            int to = nxt[v][d];
            if (to == v) continue;
            if (!visDfs[to]) {
                X.push_back(DCH[d]);
                dfs(to);
                X.push_back(DCH[opp[d]]);
            }
        }
    };
    dfs(p);

    string revX(X.rbegin(), X.rend());

    // Build final answer: prefix + X + reverse(X) + suffix
    string ans;
    ans.reserve(prefix.size() + X.size() + revX.size() + suffix.size());
    ans += prefix;
    ans += X;
    ans += revX;
    ans += suffix;

    if (ans.size() > 1000000) {
        cout << "-1\n";
        return 0;
    }

    // Validate
    {
        vector<uint8_t> vis(N, 0);
        int cur = sIdx;
        vis[cur] = 1;
        int cnt = 1;
        for (char c : ans) {
            cur = nxt[cur][dirIdx(c)];
            if (!vis[cur]) {
                vis[cur] = 1;
                cnt++;
            }
        }
        if (cur != eIdx || cnt != N) {
            cout << "-1\n";
            return 0;
        }
        // Palindrome check (optional, cheap)
        for (size_t i = 0, j = ans.size(); i < j; i++, j--) {
            if (ans[i] != ans[j - 1]) {
                cout << "-1\n";
                return 0;
            }
        }
    }

    cout << ans << "\n";
    return 0;
}