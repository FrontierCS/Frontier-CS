#include <bits/stdc++.h>
using namespace std;

static const int H = 30;
static const int W = 30;

struct XorShift64 {
    uint64_t x;
    XorShift64(uint64_t seed = 88172645463393265ull) : x(seed) {}
    inline uint64_t next() {
        x ^= x << 7;
        x ^= x >> 9;
        return x;
    }
    inline uint32_t next_u32() { return (uint32_t)next(); }
    inline uint32_t operator()() { return next_u32(); }
    inline int next_int(int n) { return (int)(next_u32() % n); }
};

int di[4] = {0, -1, 0, 1};
int dj[4] = {-1, 0, 1, 0};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    vector<vector<int>> base(H, vector<int>(W, 0));
    for (int i = 0; i < H; i++) {
        string s;
        if (!(cin >> s)) return 0;
        for (int j = 0; j < W; j++) {
            base[i][j] = s[j] - '0';
        }
    }

    // to[t][d]
    int to_arr[8][4] = {
        {1, 0, -1, -1},
        {3, -1, -1, 0},
        {-1, -1, 3, 2},
        {-1, 2, 1, -1},
        {1, 0, 3, 2},
        {3, 2, 1, 0},
        {2, -1, 0, -1},
        {-1, 3, -1, 1}
    };

    // open mask for each type
    int openMask[8] = {0};
    for (int t = 0; t < 8; t++) {
        int m = 0;
        for (int d = 0; d < 4; d++) if (to_arr[t][d] != -1) m |= (1 << d);
        openMask[t] = m;
    }

    // rotation mapping: rotType[t][r] => type after rotating t CCW r times (r in 0..3)
    int rotType[8][4];
    for (int t = 0; t < 8; t++) {
        for (int r = 0; r < 4; r++) {
            if (t <= 3) {
                rotType[t][r] = (t + r) % 4;
            } else if (t <= 5) {
                rotType[t][r] = (r % 2 == 0) ? t : (9 - t); // 4<->5
            } else {
                rotType[t][r] = (r % 2 == 0) ? t : (13 - t); // 6<->7
            }
        }
    }

    auto tileLocalScore = [&](const vector<vector<int>>& curType, int i, int j, int typeAt)->int {
        int score = 0;
        int mask = openMask[typeAt];
        for (int s = 0; s < 4; s++) {
            bool openSelf = (mask >> s) & 1;
            int ni = i + di[s];
            int nj = j + dj[s];
            if (ni < 0 || ni >= H || nj < 0 || nj >= W) {
                if (openSelf) score -= 1;
            } else {
                if (openSelf) {
                    int ntype = curType[ni][nj];
                    bool openNei = ((openMask[ntype] >> (s ^ 2)) & 1);
                    score += (openNei ? 1 : -1);
                }
            }
        }
        return score;
    };

    XorShift64 rng(chrono::high_resolution_clock::now().time_since_epoch().count());

    auto startTime = chrono::high_resolution_clock::now();
    const double TIME_LIMIT = 1.75; // seconds

    vector<vector<int>> bestR(H, vector<int>(W, 0));
    long long bestEnergy = LLONG_MIN;

    while (true) {
        auto now = chrono::high_resolution_clock::now();
        double elapsed = chrono::duration<double>(now - startTime).count();
        if (elapsed > TIME_LIMIT) break;

        vector<vector<int>> r(H, vector<int>(W, 0));
        vector<vector<int>> curType(H, vector<int>(W, 0));

        // Random initialization
        for (int i = 0; i < H; i++) {
            for (int j = 0; j < W; j++) {
                r[i][j] = rng.next_int(4);
                curType[i][j] = rotType[base[i][j]][r[i][j]];
            }
        }

        bool improved = true;
        int iter = 0;
        while (improved) {
            auto now2 = chrono::high_resolution_clock::now();
            double elapsed2 = chrono::duration<double>(now2 - startTime).count();
            if (elapsed2 > TIME_LIMIT) break;

            improved = false;
            vector<int> order(H * W);
            iota(order.begin(), order.end(), 0);
            // Shuffle to avoid bias
            for (int k = (int)order.size() - 1; k > 0; --k) {
                int idx = rng.next_int(k + 1);
                swap(order[k], order[idx]);
            }

            for (int idx = 0; idx < H * W; idx++) {
                int v = order[idx];
                int i = v / W;
                int j = v % W;

                int currentType = curType[i][j];
                int curS = tileLocalScore(curType, i, j, currentType);

                int bestRot = r[i][j];
                int bestS = curS;
                int bestTypeHere = currentType;

                for (int ro = 0; ro < 4; ro++) {
                    if (ro == r[i][j]) continue;
                    int newType = rotType[base[i][j]][ro];
                    int sc = tileLocalScore(curType, i, j, newType);
                    if (sc > bestS || (sc == bestS && rng.next_int(2) == 0)) {
                        bestS = sc;
                        bestRot = ro;
                        bestTypeHere = newType;
                    }
                }
                if (bestRot != r[i][j]) {
                    r[i][j] = bestRot;
                    curType[i][j] = bestTypeHere;
                    improved = true;
                }
            }
            iter++;
        }

        long long energy = 0;
        for (int i = 0; i < H; i++) {
            for (int j = 0; j < W; j++) {
                energy += tileLocalScore(curType, i, j, curType[i][j]);
            }
        }
        if (energy > bestEnergy) {
            bestEnergy = energy;
            bestR = r;
        }
    }

    string out;
    out.reserve(H * W);
    for (int i = 0; i < H; i++) {
        for (int j = 0; j < W; j++) {
            out.push_back(char('0' + (bestR[i][j] & 3)));
        }
    }
    cout << out << '\n';
    return 0;
}