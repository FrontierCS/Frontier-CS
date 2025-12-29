#include <bits/stdc++.h>
using namespace std;

static const int N = 30;
static const int M = N * N;
static const int P = M * 4;

struct XorShift {
    uint64_t x;
    XorShift(uint64_t seed=88172645463393265ull) { x = seed; }
    inline uint32_t next() {
        x ^= x << 7;
        x ^= x >> 9;
        return (uint32_t)x;
    }
    inline uint32_t operator()() { return next(); }
};

static const int di[4] = {0, -1, 0, 1};   // left, up, right, down
static const int dj[4] = {-1, 0, 1, 0};
static const int toTbl[8][4] = {
    {1, 0, -1, -1},
    {3, -1, -1, 0},
    {-1, -1, 3, 2},
    {-1, 2, 1, -1},
    {1, 0, 3, 2},
    {3, 2, 1, 0},
    {2, -1, 0, -1},
    {-1, 3, -1, 1},
};
static const int rotccw[8] = {1,2,3,0,5,4,7,6};
inline int rotateTile(int t, int r) {
    r &= 3;
    if (r == 0) return t;
    if (r == 1) return rotccw[t];
    if (r == 2) return rotccw[rotccw[t]];
    return rotccw[rotccw[rotccw[t]]];
}

struct Timer {
    chrono::high_resolution_clock::time_point st;
    Timer() { reset(); }
    void reset() { st = chrono::high_resolution_clock::now(); }
    double elapsed_ms() const {
        auto now = chrono::high_resolution_clock::now();
        return chrono::duration<double, milli>(now - st).count();
    }
};

struct Solver {
    int base[M];
    int rot[M];
    int trot[M];

    // Buffers for score calculation
    unsigned short seenRun[P]; // store run_id (mod 65535 safe)
    unsigned short posIdx[P];
    unsigned char finalized[P];

    int run_id;

    Solver() {
        memset(base, 0, sizeof(base));
        memset(rot, 0, sizeof(rot));
        memset(trot, 0, sizeof(trot));
        memset(seenRun, 0, sizeof(seenRun));
        memset(posIdx, 0, sizeof(posIdx));
        memset(finalized, 0, sizeof(finalized));
        run_id = 0;
    }

    inline void update_trot_cell(int idx) {
        trot[idx] = rotateTile(base[idx], rot[idx]);
    }

    inline void compute_trot_all() {
        for (int i = 0; i < M; i++) trot[i] = rotateTile(base[i], rot[i]);
    }

    inline long long computeScore() {
        // Reset finalized marks
        memset(finalized, 0, sizeof(finalized));
        // We won't clear seenRun/posIdx arrays fully; we rely on run_id increment
        // run_id is 16-bit; to avoid overflow wrap issues, reset arrays when near limit
        if (run_id > 65000) {
            memset(seenRun, 0, sizeof(seenRun));
            run_id = 0;
        }

        long long best1 = 0, best2 = 0;
        vector<int> stack;
        stack.reserve(P);

        for (int id = 0; id < P; id++) {
            int cell = id >> 2;
            int d = id & 3;
            int t = trot[cell];
            if (toTbl[t][d] == -1) continue;
            if (finalized[id]) continue;

            ++run_id;
            stack.clear();
            int cur = id;
            long long cycLen = 0;
            while (true) {
                if (finalized[cur]) break;
                if (seenRun[cur] == run_id) {
                    int at = posIdx[cur];
                    cycLen = (int)stack.size() - at;
                    break;
                }
                seenRun[cur] = run_id;
                posIdx[cur] = (unsigned short)stack.size();
                stack.push_back(cur);

                int c = cur >> 2;
                int dir = cur & 3;
                int tt = trot[c];
                int d2 = toTbl[tt][dir];
                if (d2 == -1) break;
                int i = c / N, j = c % N;
                int ni = i + di[d2], nj = j + dj[d2];
                if (ni < 0 || ni >= N || nj < 0 || nj >= N) break;
                int nd = (d2 + 2) & 3;
                int nc = (ni * N + nj);
                cur = (nc << 2) | nd;
            }

            for (int v : stack) finalized[v] = 1;
            if (cycLen > 0) {
                if (cycLen >= best1) { best2 = best1; best1 = cycLen; }
                else if (cycLen > best2) { best2 = cycLen; }
            }
        }
        if (best2 <= 0) return 0;
        return best1 * best2;
    }

    string solve() {
        ios::sync_with_stdio(false);
        cin.tie(nullptr);

        // Read input
        for (int i = 0; i < N; i++) {
            string s; cin >> s;
            for (int j = 0; j < N; j++) {
                base[i * N + j] = s[j] - '0';
            }
        }

        Timer timer;
        const double TIME_LIMIT = 1950.0; // ms

        XorShift rng(chrono::high_resolution_clock::now().time_since_epoch().count());

        // Initialize rotations randomly
        for (int i = 0; i < M; i++) {
            rot[i] = rng() & 3;
        }
        compute_trot_all();

        long long curScore = computeScore();
        long long bestScore = curScore;
        vector<int> bestRot(rot, rot + M);

        // Simulated annealing parameters
        const double T0 = 5.0;
        const double T1 = 0.1;

        int iterations = 0;
        while (true) {
            double t = timer.elapsed_ms();
            if (t >= TIME_LIMIT) break;
            double progress = t / TIME_LIMIT;
            double Temp = T0 * pow(T1 / T0, progress);

            int idx = (int)(rng() % M);
            int oldr = rot[idx];
            int delta = (int)(rng() % 3) + 1; // 1..3, ensure change
            int newr = (oldr + delta) & 3;

            rot[idx] = newr;
            update_trot_cell(idx);

            long long newScore = computeScore();

            long long diff = newScore - curScore;
            bool accept = false;
            if (diff >= 0) {
                accept = true;
            } else {
                double prob = exp(diff / Temp);
                uint32_t rv = rng();
                double rnd = (rv & 0xFFFFFF) / double(0x1000000);
                if (rnd < prob) accept = true;
            }

            if (accept) {
                curScore = newScore;
                if (curScore > bestScore) {
                    bestScore = curScore;
                    bestRot.assign(rot, rot + M);
                }
            } else {
                // revert
                rot[idx] = oldr;
                update_trot_cell(idx);
            }
            iterations++;
        }

        // Output best rotation plan
        string out;
        out.resize(M);
        for (int i = 0; i < M; i++) out[i] = char('0' + (bestRot[i] & 3));
        return out;
    }
};

int main() {
    Solver solver;
    string ans = solver.solve();
    cout << ans << "\n";
    return 0;
}