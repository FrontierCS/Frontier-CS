#include <bits/stdc++.h>
using namespace std;

static const int H = 30;
static const int W = 30;
static const int N = H * W;
static const int STATES = N * 4;

static const int di[4] = {0, -1, 0, 1};
static const int dj[4] = {-1, 0, 1, 0};
// to[t][d] provided by the problem statement
static const int TO[8][4] = {
    {1, 0, -1, -1},
    {3, -1, -1, 0},
    {-1, -1, 3, 2},
    {-1, 2, 1, -1},
    {1, 0, 3, 2},
    {3, 2, 1, 0},
    {2, -1, 0, -1},
    {-1, 3, -1, 1},
};

inline int rotate_type(int t, int r) {
    if (t <= 3) return (t + r) & 3;
    if (t <= 5) return (r & 1) ? (9 - t) : t;  // 4 <-> 5
    return (r & 1) ? (13 - t) : t;             // 6 <-> 7
}

struct Evaluator {
    int base_t[N];
    int rot[N];     // 0..3
    int tile[N];    // rotated type
    int nxt[STATES];

    Evaluator() {
        memset(base_t, 0, sizeof(base_t));
        memset(rot, 0, sizeof(rot));
        memset(tile, 0, sizeof(tile));
        for (int i = 0; i < STATES; i++) nxt[i] = -1;
    }

    inline void apply_rotation() {
        for (int k = 0; k < N; k++) {
            tile[k] = rotate_type(base_t[k], rot[k]);
        }
    }

    inline void build_next() {
        // Fill nxt mapping based on current tile[]
        for (int i = 0; i < H; i++) {
            for (int j = 0; j < W; j++) {
                int k = i * W + j;
                int t = tile[k];
                for (int d = 0; d < 4; d++) {
                    int idx = (k << 2) | d;
                    int d2 = TO[t][d];
                    if (d2 == -1) {
                        nxt[idx] = -1;
                        continue;
                    }
                    int ni = i + di[d2];
                    int nj = j + dj[d2];
                    if (ni < 0 || ni >= H || nj < 0 || nj >= W) {
                        nxt[idx] = -1;
                        continue;
                    }
                    int nd = (d2 + 2) & 3;
                    int nk = ni * W + nj;
                    nxt[idx] = (nk << 2) | nd;
                }
            }
        }
    }

    inline int compute_score(int &L1_out, int &L2_out) {
        // Compute cycles in the directed graph nxt[]
        static unsigned char vis[STATES];
        static int seen_id[STATES];
        static int seen_pos[STATES];
        memset(vis, 0, sizeof(vis));
        int iterMark = 1;
        int L1 = 0, L2 = 0;

        vector<int> path;
        path.reserve(STATES);

        for (int v = 0; v < STATES; v++) {
            if (nxt[v] == -1 || vis[v]) continue;
            path.clear();
            int cur = v;
            while (true) {
                if (cur == -1) break;
                if (vis[cur]) break;
                if (seen_id[cur] == iterMark) {
                    int cycLen = (int)path.size() - seen_pos[cur];
                    if (cycLen >= L1) {
                        L2 = L1;
                        L1 = cycLen;
                    } else if (cycLen > L2) {
                        L2 = cycLen;
                    }
                    break;
                }
                seen_id[cur] = iterMark;
                seen_pos[cur] = (int)path.size();
                path.push_back(cur);
                cur = nxt[cur];
            }
            for (int u : path) vis[u] = 1;
            iterMark++;
        }
        L1_out = L1;
        L2_out = L2;
        if (L2 == 0) return 0;
        return L1 * L2;
    }
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    Evaluator E;

    // Read input: 30 lines, each length 30 of chars '0'..'7'
    for (int i = 0; i < H; i++) {
        string s; cin >> s;
        for (int j = 0; j < W; j++) {
            int k = i * W + j;
            E.base_t[k] = s[j] - '0';
        }
    }

    // Initialize rotations
    std::mt19937 rng((uint32_t)chrono::high_resolution_clock::now().time_since_epoch().count());
    for (int k = 0; k < N; k++) {
        int t = E.base_t[k];
        if (t <= 3) {
            E.rot[k] = rng() & 3; // 0..3
        } else {
            E.rot[k] = (rng() & 1); // parity matters only
        }
    }

    auto start = chrono::high_resolution_clock::now();
    const double TIME_LIMIT = 1.85; // seconds

    // Initial evaluation
    E.apply_rotation();
    E.build_next();
    int L1, L2;
    int curScore = E.compute_score(L1, L2);

    vector<int> bestRot(E.rot, E.rot + N);
    int bestScore = curScore;
    int bestL1 = L1, bestL2 = L2;

    // Simulated annealing
    const double T0 = 50.0, T1 = 1.0;
    int iter = 0;

    while (true) {
        iter++;
        auto now = chrono::high_resolution_clock::now();
        double elapsed = chrono::duration<double>(now - start).count();
        if (elapsed > TIME_LIMIT) break;
        double progress = elapsed / TIME_LIMIT;
        double T = T0 + (T1 - T0) * progress;

        int k = (int)(rng() % N);
        int t = E.base_t[k];
        int oldr = E.rot[k];
        int newr;
        if (t <= 3) {
            // choose a rotation different from current
            int add = (int)(rng() % 3) + 1;
            newr = (oldr + add) & 3;
        } else {
            // toggle parity
            newr = oldr ^ 1;
        }
        if (newr == oldr) continue;

        E.rot[k] = newr;
        // Recompute only affected structures by full recomputation (simpler)
        E.apply_rotation();
        E.build_next();
        int nL1, nL2;
        int newScore = E.compute_score(nL1, nL2);

        int delta = newScore - curScore;
        bool accept = false;
        if (delta >= 0) {
            accept = true;
        } else {
            double prob = exp((double)delta / T);
            uint32_t rv = rng();
            double r01 = (rv % 1000000) / 1000000.0;
            if (r01 < prob) accept = true;
        }

        if (accept) {
            curScore = newScore;
            if (newScore > bestScore) {
                bestScore = newScore;
                bestL1 = nL1;
                bestL2 = nL2;
                for (int i = 0; i < N; i++) bestRot[i] = E.rot[i];
            }
        } else {
            // revert
            E.rot[k] = oldr;
            E.apply_rotation();
            E.build_next();
        }
    }

    // Output best rotations found
    string out;
    out.reserve(N);
    for (int i = 0; i < N; i++) {
        out.push_back(char('0' + (bestRot[i] & 3)));
    }
    cout << out << "\n";
    return 0;
}