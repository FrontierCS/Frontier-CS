#include <bits/stdc++.h>
using namespace std;

static const int N = 30;
static const int M = 30;
static const int D = 4;

// Direction mapping: 0:left,1:up,2:right,3:down
static const int di[D] = {0,-1,0,1};
static const int dj[D] = {-1,0,1,0};

// to[t][d]: direction to the next tile, or -1 if cannot enter
static const int toTable[8][4] = {
    {1, 0, -1, -1},  // 0: L<->U
    {3, -1, -1, 0},  // 1: L<->D
    {-1, -1, 3, 2},  // 2: R<->D
    {-1, 2, 1, -1},  // 3: U<->R
    {1, 0, 3, 2},    // 4: L<->U and R<->D (two curves)
    {3, 2, 1, 0},    // 5: L<->D and R<->U (two curves)
    {2, -1, 0, -1},  // 6: L<->R (horizontal)
    {-1, 3, -1, 1}   // 7: U<->D (vertical)
};

inline int idx(int i, int j, int d){ return ((i*M + j) << 2) | d; }

struct Solver {
    int initTile[N][M];  // input tile types
    int rot[N][M];       // rotations 0..3 (number of 90deg CCW)
    int curTile[N][M];   // tile type after rotation
    mt19937 rng;

    Solver() : rng((uint32_t)chrono::steady_clock::now().time_since_epoch().count()) {}

    static inline int rotateType(int t, int r) {
        if (t <= 3) return (t + r) & 3;
        if (t <= 5) return (r & 1) ? (t ^ 1) : t; // 4<->5
        return (r & 1) ? (t ^ 1) : t;             // 6<->7
    }

    void readInput() {
        vector<string> tokens;
        tokens.reserve(N*M);
        while ((int)tokens.size() < N*M) {
            string s;
            if (!(cin >> s)) break;
            if ((int)s.size() == 30) {
                for (char c : s) tokens.push_back(string(1, c));
            } else {
                tokens.push_back(s);
            }
        }
        int ptr = 0;
        for (int i = 0; i < N; ++i) {
            for (int j = 0; j < M; ++j) {
                if (ptr < (int)tokens.size()) {
                    initTile[i][j] = tokens[ptr][0] - '0';
                    ptr++;
                } else {
                    initTile[i][j] = 0;
                }
            }
        }
    }

    inline void applyRotation() {
        for (int i = 0; i < N; ++i)
            for (int j = 0; j < M; ++j)
                curTile[i][j] = rotateType(initTile[i][j], rot[i][j]);
    }

    // Compute top two cycle lengths and score = L1 * L2
    long long computeScore(int &outL1, int &outL2) {
        static uint8_t visited[(N*M*D + 7)/8];
        memset(visited, 0, sizeof(visited));

        static int seenId[N*M*D];
        static int seenStep[N*M*D];
        static int visitToken = 1;
        visitToken++; if (visitToken == 0) { // rare wrap, reset
            fill(begin(seenId), end(seenId), 0);
            visitToken = 1;
        }

        auto isVisited = [&](int s)->bool {
            return (visited[s>>3] >> (s&7)) & 1;
        };
        auto setVisited = [&](int s) {
            visited[s>>3] |= (1u << (s&7));
        };

        int best1 = 0, best2 = 0;
        for (int i = 0; i < N; ++i){
            for (int j = 0; j < M; ++j){
                for (int d = 0; d < 4; ++d){
                    int s = idx(i,j,d);
                    if (isVisited(s)) continue;
                    if (toTable[curTile[i][j]][d] == -1) { setVisited(s); continue; }

                    int ci = i, cj = j, cd = d;
                    int step = 0;
                    int pathStart = s;
                    int token = visitToken++;
                    // Walk along the directed edges
                    while (true) {
                        int cur = idx(ci, cj, cd);
                        if (isVisited(cur)) {
                            // mark entire path states visited
                            int ii = i, jj = j, dd = d;
                            int s2 = idx(ii, jj, dd);
                            while (true) {
                                if (isVisited(s2)) break;
                                setVisited(s2);
                                int t2 = toTable[curTile[ii][jj]][dd];
                                if (t2 == -1) break;
                                int ni = ii + di[t2];
                                int nj = jj + dj[t2];
                                if (ni < 0 || ni >= N || nj < 0 || nj >= M) break;
                                int nd = (t2 + 2) & 3;
                                if (ii == ci && jj == cj && dd == cd) {
                                    setVisited(s2);
                                    break;
                                }
                                ii = ni; jj = nj; dd = nd; s2 = idx(ii, jj, dd);
                            }
                            break;
                        }
                        if (seenId[cur] == token) {
                            // found a cycle
                            int loopLen = step - seenStep[cur];
                            // record loopLen
                            if (loopLen >= best1) { best2 = best1; best1 = loopLen; }
                            else if (loopLen > best2) best2 = loopLen;
                            // mark states visited
                            int ii = i, jj = j, dd = d;
                            int s2 = idx(ii, jj, dd);
                            while (true) {
                                if (isVisited(s2)) break;
                                setVisited(s2);
                                int t2 = toTable[curTile[ii][jj]][dd];
                                if (t2 == -1) break;
                                int ni = ii + di[t2];
                                int nj = jj + dj[t2];
                                if (ni < 0 || ni >= N || nj < 0 || nj >= M) break;
                                int nd = (t2 + 2) & 3;
                                if (ii == ci && jj == cj && dd == cd) {
                                    setVisited(s2);
                                    break;
                                }
                                ii = ni; jj = nj; dd = nd; s2 = idx(ii, jj, dd);
                            }
                            break;
                        }
                        seenId[cur] = token;
                        seenStep[cur] = step;

                        int d2 = toTable[curTile[ci][cj]][cd];
                        if (d2 == -1) {
                            // broken path
                            // mark states visited
                            int ii = i, jj = j, dd = d;
                            int s2 = idx(ii, jj, dd);
                            while (true) {
                                if (isVisited(s2)) break;
                                setVisited(s2);
                                int t2 = toTable[curTile[ii][jj]][dd];
                                if (t2 == -1) break;
                                int ni = ii + di[t2];
                                int nj = jj + dj[t2];
                                if (ni < 0 || ni >= N || nj < 0 || nj >= M) break;
                                int nd = (t2 + 2) & 3;
                                if (ii == ci && jj == cj && dd == cd) {
                                    setVisited(s2);
                                    break;
                                }
                                ii = ni; jj = nj; dd = nd; s2 = idx(ii, jj, dd);
                            }
                            break;
                        }
                        int ni = ci + di[d2];
                        int nj = cj + dj[d2];
                        if (ni < 0 || ni >= N || nj < 0 || nj >= M) {
                            // broken
                            int ii = i, jj = j, dd = d;
                            int s2 = idx(ii, jj, dd);
                            while (true) {
                                if (isVisited(s2)) break;
                                setVisited(s2);
                                int t2 = toTable[curTile[ii][jj]][dd];
                                if (t2 == -1) break;
                                int nni = ii + di[t2];
                                int nnj = jj + dj[t2];
                                if (nni < 0 || nni >= N || nnj < 0 || nnj >= M) break;
                                int nnd = (t2 + 2) & 3;
                                if (ii == ci && jj == cj && dd == cd) {
                                    setVisited(s2);
                                    break;
                                }
                                ii = nni; jj = nnj; dd = nnd; s2 = idx(ii, jj, dd);
                            }
                            break;
                        }
                        int nd = (d2 + 2) & 3;

                        ci = ni; cj = nj; cd = nd;
                        step++;
                    }
                }
            }
        }
        outL1 = best1; outL2 = best2;
        long long sc = 1LL * best1 * best2;
        return sc;
    }

    void solve() {
        // Initialize rotations randomly
        uniform_int_distribution<int> dist4(0,3);
        for (int i = 0; i < N; ++i)
            for (int j = 0; j < M; ++j)
                rot[i][j] = dist4(rng);
        applyRotation();

        int L1, L2;
        long long bestScore = computeScore(L1, L2);
        auto bestRot = vector<int>(N*M);
        for (int i = 0; i < N; ++i)
            for (int j = 0; j < M; ++j)
                bestRot[i*M + j] = rot[i][j];

        // Simulated annealing-like random local search
        const double TIME_LIMIT = 1.9; // seconds
        auto time_start = chrono::steady_clock::now();

        uniform_int_distribution<int> diCell(0, N-1), djCell(0, M-1);
        uniform_int_distribution<int> drot(0,3);

        // Temperature parameters
        const double T0 = 5.0;
        const double T1 = 0.1;

        int iter = 0;
        while (true) {
            ++iter;
            auto now = chrono::steady_clock::now();
            double elapsed = chrono::duration<double>(now - time_start).count();
            if (elapsed > TIME_LIMIT) break;
            double t = elapsed / TIME_LIMIT;
            double Temp = T0 * pow(T1 / T0, t);

            int i = diCell(rng);
            int j = djCell(rng);
            int newr = drot(rng);
            if (newr == rot[i][j]) continue;

            int oldr = rot[i][j];
            int oldtype = curTile[i][j];
            rot[i][j] = newr;
            curTile[i][j] = rotateType(initTile[i][j], newr);

            int nL1,nL2;
            long long newScore = computeScore(nL1, nL2);
            long long diff = newScore - bestScore;

            bool accept = false;
            if (diff >= 0) {
                accept = true;
            } else {
                double prob = exp((double)diff / Temp);
                uniform_real_distribution<double> uni(0.0, 1.0);
                if (uni(rng) < prob) accept = true;
            }
            if (accept) {
                if (newScore > bestScore) {
                    bestScore = newScore;
                    for (int ii = 0; ii < N; ++ii)
                        for (int jj = 0; jj < M; ++jj)
                            bestRot[ii*M + jj] = rot[ii][jj];
                }
            } else {
                // revert
                rot[i][j] = oldr;
                curTile[i][j] = oldtype;
            }
        }

        // Use best found rotations
        for (int i = 0; i < N; ++i)
            for (int j = 0; j < M; ++j)
                rot[i][j] = bestRot[i*M + j];

        // Output
        string out;
        out.reserve(N*M);
        for (int i = 0; i < N; ++i)
            for (int j = 0; j < M; ++j)
                out.push_back(char('0' + (rot[i][j] & 3)));
        cout << out << '\n';
    }
};

int main(){
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    Solver solver;
    solver.readInput();
    solver.solve();

    return 0;
}