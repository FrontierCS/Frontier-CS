#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    int n, m;
    if (!(cin >> n >> m)) return 0;
    vector<string> g(n);
    for (int i = 0; i < n; ++i) cin >> g[i];
    int sr, sc, er, ec;
    cin >> sr >> sc >> er >> ec;
    --sr; --sc; --er; --ec;
    // Map blank cells to ids
    vector<vector<int>> id(n, vector<int>(m, -1));
    vector<pair<int,int>> cells;
    int B = 0;
    for (int i = 0; i < n; ++i) {
        for (int j = 0; j < m; ++j) {
            if (g[i][j] == '1') {
                id[i][j] = B++;
                cells.push_back({i,j});
            }
        }
    }
    if (id[sr][sc] == -1 || id[er][ec] == -1) {
        cout << -1 << '\n';
        return 0;
    }
    int sid = id[sr][sc];
    int tid = id[er][ec];
    if (B == 1) {
        // Only one cell, start == end == only blank
        cout << "" << '\n';
        return 0;
    }
    // Check connectivity from start
    vector<int> vis(B, 0);
    queue<int> q;
    vis[sid] = 1;
    q.push(sid);
    auto nbrs = [&](int idx, vector<int>& out){
        int i = cells[idx].first;
        int j = cells[idx].second;
        static int di[4] = {0,0,-1,1};
        static int dj[4] = {-1,1,0,0};
        out.clear();
        for (int d = 0; d < 4; ++d) {
            int ni = i + di[d], nj = j + dj[d];
            if (ni>=0 && ni<n && nj>=0 && nj<m && id[ni][nj]!=-1) {
                out.push_back(id[ni][nj]);
            }
        }
    };
    vector<int> out;
    while (!q.empty()) {
        int u = q.front(); q.pop();
        nbrs(u, out);
        for (int v: out) if (!vis[v]) vis[v]=1,q.push(v);
    }
    for (int i = 0; i < B; ++i) {
        if (!vis[i]) {
            cout << -1 << '\n';
            return 0;
        }
    }
    // Precompute direction transitions f_c
    // 0:L,1:R,2:U,3:D
    static int di[4] = {0,0,-1,1};
    static int dj[4] = {-1,1,0,0};
    vector<array<int,4>> f(B);
    for (int idx = 0; idx < B; ++idx) {
        int i = cells[idx].first;
        int j = cells[idx].second;
        for (int d = 0; d < 4; ++d) {
            int ni = i + di[d], nj = j + dj[d];
            if (ni>=0 && ni<n && nj>=0 && nj<m && id[ni][nj]!=-1) f[idx][d] = id[ni][nj];
            else f[idx][d] = idx;
        }
    }
    // BFS distance to target for tie-breaks
    vector<int> dist(B, -1);
    queue<int> qd;
    dist[tid] = 0; qd.push(tid);
    while (!qd.empty()) {
        int u = qd.front(); qd.pop();
        for (int vdir = 0; vdir < 4; ++vdir) {
            int v = f[u][vdir];
            if (v != u && dist[v] == -1) { dist[v] = dist[u] + 1; qd.push(v); }
        }
    }
    // Prepare bitset helpers
    int W = (B + 63) / 64;
    vector<uint64_t> bitmask(B);
    vector<int> widx(B);
    for (int i = 0; i < B; ++i) {
        bitmask[i] = 1ULL << (i & 63);
        widx[i] = i >> 6;
    }
    auto popcount_bits = [&](const vector<uint64_t>& a)->int{
        int s = 0;
        for (int i = 0; i < W; ++i) s += (int)__builtin_popcountll(a[i]);
        return s;
    };
    auto is_superset = [&](const vector<uint64_t>& A, const vector<uint64_t>& Bv)->bool{
        for (int i = 0; i < W; ++i) {
            if ((A[i] | Bv[i]) != A[i]) return false;
        }
        return true;
    };
    auto char_of = [&](int d)->char{
        if (d==0) return 'L';
        if (d==1) return 'R';
        if (d==2) return 'U';
        return 'D';
    };

    string bestAnswer;
    bool solved = false;

    // Attempts: mid = -1 (none), or 0..3 for L,R,U,D
    vector<int> attempts;
    attempts.push_back(-1);
    attempts.push_back(0);
    attempts.push_back(1);
    attempts.push_back(2);
    attempts.push_back(3);

    mt19937 rng((uint32_t)chrono::steady_clock::now().time_since_epoch().count());

    for (int mid : attempts) {
        // Initialize F and cov
        vector<int> F(B);
        vector<vector<uint64_t>> cov(B, vector<uint64_t>(W, 0));
        vector<int> Ftmp(B);
        vector<vector<uint64_t>> covNew(B, vector<uint64_t>(W, 0));
        vector<int> X; // wraps in chronological order
        vector<uint64_t> visitedCur(W, 0);
        int endCur = sid;
        int lenInit = 0;
        if (mid == -1) {
            for (int i = 0; i < B; ++i) F[i] = i;
            // cov already zero
            // visited includes start only at beginning
            visitedCur[widx[sid]] |= bitmask[sid];
            endCur = sid;
            lenInit = 0;
        } else {
            for (int i = 0; i < B; ++i) {
                int p1 = f[i][mid];
                F[i] = p1;
                cov[i][widx[p1]] |= bitmask[p1];
            }
            // visited: start and after mid move
            visitedCur[widx[sid]] |= bitmask[sid];
            visitedCur[widx[F[sid]]] |= bitmask[F[sid]];
            endCur = F[sid];
            lenInit = 1;
        }
        int visitedCount = popcount_bits(visitedCur);
        if (visitedCount == B && endCur == tid) {
            string left, right;
            // left is reversed X; mid optional; right is X
            left.reserve(X.size());
            right.reserve(X.size());
            for (int i = (int)X.size()-1; i >= 0; --i) left.push_back(char_of(X[i]));
            for (int i = 0; i < (int)X.size(); ++i) right.push_back(char_of(X[i]));
            string ans;
            ans.reserve(left.size() + (mid==-1?0:1) + right.size());
            ans += left;
            if (mid != -1) ans.push_back(char_of(mid));
            ans += right;
            bestAnswer = ans;
            solved = true;
            break;
        }
        int maxSteps = (1000000 - lenInit) / 2;
        if (maxSteps < 0) continue;
        for (int step = 0; step < maxSteps && !(visitedCount == B && endCur == tid); ++step) {
            // Evaluate 4 candidates
            int bestC = -1;
            int bestVisCount = -1;
            int bestDist = INT_MAX;
            bool wantSuperset = true;
            if (visitedCount < B) wantSuperset = true;
            else wantSuperset = true; // prefer keeping coverage once full
            // If coverage is full and end already at target, we would have exited.
            // Now select c
            array<vector<uint64_t>, 4> candVisWords;
            array<int,4> candVisCnt;
            array<int,4> candEnd;
            array<bool,4> candSuper;
            for (int d = 0; d < 4; ++d) {
                int p1 = f[sid][d];
                int p2 = F[p1];
                int p3 = f[p2][d];
                candEnd[d] = p3;
                candVisWords[d].assign(W, 0);
                int w1 = widx[p1], w3 = widx[p3], ws = widx[sid];
                uint64_t b1 = bitmask[p1], b3 = bitmask[p3], bs = bitmask[sid];
                int cnt = 0;
                bool super = true;
                for (int i = 0; i < W; ++i) {
                    uint64_t word = cov[p1][i];
                    if (i == w1) word |= b1;
                    if (i == w3) word |= b3;
                    if (i == ws) word |= bs;
                    candVisWords[d][i] = word;
                    if (wantSuperset) {
                        if ((word | visitedCur[i]) != word) super = false;
                    }
                    cnt += (int)__builtin_popcountll(word);
                }
                candVisCnt[d] = cnt;
                candSuper[d] = super;
            }
            // Selection strategy:
            // Primary: if coverage incomplete, maximize candVisCnt; ties: min dist to target; else random small tie-break
            // If coverage complete, keep superset and minimize dist; ties arbitrary
            vector<int> order = {0,1,2,3};
            shuffle(order.begin(), order.end(), rng);
            if (visitedCount < B) {
                int tmpBestVis = -1;
                int tmpBestDist = INT_MAX;
                int tmpBestIdx = -1;
                // Prefer supersets first
                for (int pass = 0; pass < 2; ++pass) {
                    for (int d : order) {
                        if (pass==0 && !candSuper[d]) continue;
                        if (pass==1 && candSuper[d]) continue;
                        int vcnt = candVisCnt[d];
                        int dd = dist[candEnd[d]];
                        if (dd < 0) dd = INT_MAX/2;
                        if (vcnt > tmpBestVis || (vcnt == tmpBestVis && dd < tmpBestDist)) {
                            tmpBestVis = vcnt;
                            tmpBestDist = dd;
                            tmpBestIdx = d;
                        }
                    }
                    if (tmpBestIdx != -1) break;
                }
                bestC = tmpBestIdx;
            } else {
                // coverage full: keep superset, minimize distance to target
                int tmpBestDist = INT_MAX;
                int tmpBestIdx = -1;
                for (int pass = 0; pass < 2; ++pass) {
                    for (int d : order) {
                        if (pass==0 && !candSuper[d]) continue;
                        if (pass==1 && candSuper[d]) continue;
                        int dd = dist[candEnd[d]];
                        if (dd < 0) dd = INT_MAX/2;
                        if (dd < tmpBestDist) {
                            tmpBestDist = dd;
                            tmpBestIdx = d;
                        }
                    }
                    if (tmpBestIdx != -1) break;
                }
                bestC = tmpBestIdx;
            }
            if (bestC == -1) break; // should not happen
            // Commit bestC
            int c = bestC;
            // Update F and cov
            for (int p = 0; p < B; ++p) {
                int p1 = f[p][c];
                int p2 = F[p1];
                int p3 = f[p2][c];
                Ftmp[p] = p3;
                // cov new = cov[p1] | {p1} | {p3}
                // Copy cov[p1]
                for (int i = 0; i < W; ++i) covNew[p][i] = cov[p1][i];
                covNew[p][widx[p1]] |= bitmask[p1];
                covNew[p][widx[p3]] |= bitmask[p3];
            }
            F.swap(Ftmp);
            cov.swap(covNew);
            // Update visitedCur and counts and endCur
            visitedCur.swap(candVisWords[c]);
            visitedCount = candVisCnt[c];
            endCur = candEnd[c];
            X.push_back(c);
        }
        if (visitedCount == B && endCur == tid) {
            // Build answer string
            string left, right;
            left.reserve(X.size());
            right.reserve(X.size());
            for (int i = (int)X.size()-1; i >= 0; --i) left.push_back(char_of(X[i]));
            for (int i = 0; i < (int)X.size(); ++i) right.push_back(char_of(X[i]));
            string ans;
            ans.reserve(left.size() + (mid==-1?0:1) + right.size());
            ans += left;
            if (mid != -1) ans.push_back(char_of(mid));
            ans += right;
            if ((int)ans.size() <= 1000000) {
                bestAnswer = ans;
                solved = true;
                break;
            }
        }
    }
    if (!solved) {
        cout << -1 << '\n';
        return 0;
    }
    cout << bestAnswer << '\n';
    return 0;
}