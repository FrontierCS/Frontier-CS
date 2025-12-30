#include <bits/stdc++.h>
using namespace std;

static const int H = 30, W = 30;
static const int NODES = H * W * 4;

// Directions: 0=left,1=up,2=right,3=down
static const int di[4] = {0, -1, 0, 1};
static const int dj[4] = {-1, 0, 1, 0};

// to[t][d]: for tile state t (0..7), if a train enters from direction d (0..3), direction to the next tile
// -1 indicates blocked (cannot enter)
static const int TO_TABLE[8][4] = {
    {1, 0, -1, -1},
    {3, -1, -1, 0},
    {-1, -1, 3, 2},
    {-1, 2, 1, -1},
    {1, 0, 3, 2},
    {3, 2, 1, 0},
    {2, -1, 0, -1},
    {-1, 3, -1, 1},
};

// Rotations: rotate state 90deg CCW
static const int ROT[8] = {1,2,3,0,5,4,7,6};

struct EvalResult {
    long long score;
    int L1, L2;
};

struct Solver {
    int baseTile[H][W];   // initial tile state (0..7)
    int rotCount[H][W];   // rotations (0..3)
    int curState[H][W];   // current tile state after rotations
    int nextIdx[NODES];   // functional graph next pointer for each state-node, -1 if invalid

    mt19937 rng;
    chrono::steady_clock::time_point startTime;
    double timeLimit;

    Solver(): rng((unsigned)chrono::steady_clock::now().time_since_epoch().count()) {}

    inline int stateAfterRot(int t, int r) const {
        // Apply rotation r times
        // Precompute power by applying ROT r times
        if (r == 0) return t;
        if (r == 1) return ROT[t];
        if (r == 2) return ROT[ROT[t]];
        return ROT[ROT[ROT[t]]];
    }

    void readInput() {
        for (int i = 0; i < H; i++) {
            string s;
            cin >> s;
            for (int j = 0; j < W; j++) {
                baseTile[i][j] = s[j] - '0';
            }
        }
    }

    void initRotations() {
        // Initialize rotations to minimize boundary breakage
        for (int i = 0; i < H; i++) {
            for (int j = 0; j < W; j++) {
                int bestR = 0;
                int bestScore = INT_MAX;
                for (int r = 0; r < 4; r++) {
                    int t = stateAfterRot(baseTile[i][j], r);
                    int broken = 0;
                    // Consider incoming directions from existing neighbors only
                    for (int d = 0; d < 4; d++) {
                        int ni = i + di[d];
                        int nj = j + dj[d];
                        if (ni < 0 || ni >= H || nj < 0 || nj >= W) continue; // no neighbor from this side
                        int d2 = TO_TABLE[t][d];
                        if (d2 == -1) continue; // this entry is blocked, fine
                        int oi = i + di[d2];
                        int oj = j + dj[d2];
                        if (oi < 0 || oi >= H || oj < 0 || oj >= W) broken++;
                    }
                    if (broken < bestScore || (broken == bestScore && (int)(rng()%2)==0)) {
                        bestScore = broken;
                        bestR = r;
                    }
                }
                rotCount[i][j] = bestR;
                curState[i][j] = stateAfterRot(baseTile[i][j], bestR);
            }
        }
    }

    inline int encode(int i, int j, int d) const {
        return ((i * W + j) << 2) | d;
    }

    void buildNext() {
        // Build nextIdx for the functional graph
        // For each (i,j,d) where d is the entering direction to tile (i,j)
        for (int i = 0; i < H; i++) {
            for (int j = 0; j < W; j++) {
                int t = curState[i][j];
                int base = ((i * W + j) << 2);
                for (int d = 0; d < 4; d++) {
                    int d2 = TO_TABLE[t][d];
                    if (d2 == -1) {
                        nextIdx[base + d] = -1;
                        continue;
                    }
                    int ni = i + di[d2];
                    int nj = j + dj[d2];
                    if (ni < 0 || ni >= H || nj < 0 || nj >= W) {
                        nextIdx[base + d] = -1;
                        continue;
                    }
                    int nd = (d2 + 2) & 3;
                    nextIdx[base + d] = encode(ni, nj, nd);
                }
            }
        }
    }

    EvalResult evaluate() {
        // Compute two largest cycle lengths in the functional graph nextIdx
        static int seenIter[NODES];
        static int seenStep[NODES];
        static unsigned char done[NODES];
        static bool initialized = false;
        if (!initialized) {
            initialized = true;
            memset(seenIter, -1, sizeof(seenIter));
            memset(seenStep, 0, sizeof(seenStep));
            memset(done, 0, sizeof(done));
        } else {
            // Reset arrays lazily: we'll use per-start marker values
            // seenIter filled with -1 to mark not seen in current chain id.
            // But we use chain id equals starting node index, so we only need to reset done[]
            memset(done, 0, sizeof(done));
            // seenIter values are overwritten when used.
        }

        int best1 = 0, best2 = 0;

        for (int s = 0; s < NODES; s++) {
            if (done[s]) continue;
            int x = s;
            if (nextIdx[x] == -1) { done[x] = 1; continue; }

            int step = 0;
            // Use s as chain id marker
            while (true) {
                seenIter[x] = s;
                seenStep[x] = step;
                int nx = nextIdx[x];
                if (nx == -1) {
                    break;
                }
                if (done[nx]) {
                    break;
                }
                if (seenIter[nx] == s) {
                    int cycLen = step + 1 - seenStep[nx];
                    if (cycLen >= best1) {
                        best2 = best1;
                        best1 = cycLen;
                    } else if (cycLen > best2) {
                        best2 = cycLen;
                    }
                    break;
                }
                x = nx;
                step++;
            }
            // Mark all nodes seen in this chain as done
            x = s;
            while (!done[x] && seenIter[x] == s) {
                done[x] = 1;
                int nx = nextIdx[x];
                if (nx == -1) break;
                x = nx;
            }
        }

        EvalResult res;
        res.L1 = best1;
        res.L2 = best2;
        res.score = 1LL * best1 * best2;
        return res;
    }

    void applyRotation(int i, int j, int r) {
        rotCount[i][j] = r;
        curState[i][j] = stateAfterRot(baseTile[i][j], r);
    }

    void rebuildAndEval(EvalResult &res) {
        buildNext();
        res = evaluate();
    }

    void solve() {
        startTime = chrono::steady_clock::now();
        timeLimit = 1.95; // seconds

        initRotations();
        buildNext();
        EvalResult cur = evaluate();

        // Simple greedy pass: for each tile, try all 4 rotations and pick best
        {
            vector<int> order(H * W);
            iota(order.begin(), order.end(), 0);
            shuffle(order.begin(), order.end(), rng);
            for (int idx = 0; idx < (int)order.size(); idx++) {
                int v = order[idx];
                int i = v / W, j = v % W;
                int bestR = rotCount[i][j];
                long long bestScore = cur.score;
                int origR = rotCount[i][j];
                int origState = curState[i][j];
                for (int r = 0; r < 4; r++) {
                    if (r == origR) continue;
                    applyRotation(i, j, r);
                    rebuildAndEval(cur);
                    if (cur.score > bestScore) {
                        bestScore = cur.score;
                        bestR = r;
                    }
                    // restore for next trial
                    applyRotation(i, j, origR);
                    curState[i][j] = stateAfterRot(baseTile[i][j], origR);
                }
                if (bestR != origR) {
                    applyRotation(i, j, bestR);
                    rebuildAndEval(cur);
                } else {
                    // no change, ensure cur is consistent
                    applyRotation(i, j, origR);
                    rebuildAndEval(cur);
                }
                auto now = chrono::steady_clock::now();
                double elapsed = chrono::duration<double>(now - startTime).count();
                if (elapsed > timeLimit * 0.4) break;
            }
        }

        // Simulated annealing
        vector<vector<int>> bestRot(H, vector<int>(W));
        long long bestScore = cur.score;
        for (int i = 0; i < H; i++) {
            for (int j = 0; j < W; j++) bestRot[i][j] = rotCount[i][j];
        }

        const double T0 = 3e6;
        const double T1 = 1e2;
        int iter = 0;

        while (true) {
            iter++;
            if ((iter & 1023) == 0) {
                auto now = chrono::steady_clock::now();
                double elapsed = chrono::duration<double>(now - startTime).count();
                if (elapsed > timeLimit) break;
            }
            auto now = chrono::steady_clock::now();
            double elapsed = chrono::duration<double>(now - startTime).count();
            double progress = elapsed / timeLimit;
            if (progress > 1.0) progress = 1.0;
            double temp = T0 * pow(T1 / T0, progress);

            int i = (int)(rng() % H);
            int j = (int)(rng() % W);

            int newR = (rotCount[i][j] + 1 + (int)(rng() % 3)) & 3; // pick a different rotation
            int oldR = rotCount[i][j];
            applyRotation(i, j, newR);

            EvalResult cand;
            rebuildAndEval(cand);

            long long delta = cand.score - cur.score;
            if (delta >= 0) {
                cur = cand;
                if (cur.score > bestScore) {
                    bestScore = cur.score;
                    for (int a = 0; a < H; a++) for (int b = 0; b < W; b++) bestRot[a][b] = rotCount[a][b];
                }
            } else {
                double prob = exp((double)delta / temp);
                uint32_t rv = rng();
                double rnd = (rv >> 8) * (1.0 / (double)(UINT32_MAX >> 8));
                if (rnd < prob) {
                    cur = cand; // accept
                } else {
                    // revert
                    applyRotation(i, j, oldR);
                    rebuildAndEval(cur);
                }
            }
        }

        // Output best solution
        // rotCount is current; we need to output bestRot
        string out;
        out.reserve(H * W);
        for (int i = 0; i < H; i++) {
            for (int j = 0; j < W; j++) out.push_back(char('0' + bestRot[i][j]));
        }
        cout << out << '\n';
    }
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    Solver solver;
    solver.readInput();
    solver.solve();

    return 0;
}