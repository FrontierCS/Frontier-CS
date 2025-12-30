#include <bits/stdc++.h>
using namespace std;

const int H = 30;
const int W = 30;
const int TOT = H * W * 4;

int orig[H][W];
int tileState[H][W];
int rotCnt[H][W];
int bestRot[H][W];

int rotate_map[8][4];

const int di[4] = {0, -1, 0, 1};
const int dj[4] = {-1, 0, 1, 0};

int toTable[8][4] = {
    {1, 0, -1, -1},
    {3, -1, -1, 0},
    {-1, -1, 3, 2},
    {-1, 2, 1, -1},
    {1, 0, 3, 2},
    {3, 2, 1, 0},
    {2, -1, 0, -1},
    {-1, 3, -1, 1}
};

int nextNode[TOT];
unsigned char vis[TOT];
int idxPos[TOT];
int stackNodes[TOT];

uint64_t rng_state = 88172645463325252ull;
inline uint64_t rng() {
    rng_state ^= rng_state << 7;
    rng_state ^= rng_state >> 9;
    return rng_state;
}
inline int randInt(int n) {
    return (int)(rng() % n);
}
inline double randDouble() {
    return (rng() >> 11) * (1.0 / 9007199254740992.0); // 2^53
}

inline void recalcNextForCell(int i, int j) {
    int t = tileState[i][j];
    for (int d = 0; d < 4; d++) {
        int id = ((i * W + j) << 2) | d;
        int d2 = toTable[t][d];
        if (d2 == -1) {
            nextNode[id] = -1;
        } else {
            int ni = i + di[d2];
            int nj = j + dj[d2];
            if (ni < 0 || ni >= H || nj < 0 || nj >= W) {
                nextNode[id] = -1;
            } else {
                int nd = (d2 + 2) & 3;
                nextNode[id] = ((ni * W + nj) << 2) | nd;
            }
        }
    }
}

inline void buildAllNext() {
    for (int i = 0; i < H; i++) {
        for (int j = 0; j < W; j++) {
            recalcNextForCell(i, j);
        }
    }
}

inline long long computeScore() {
    const int N = TOT;
    memset(vis, 0, N * sizeof(unsigned char));
    long long L1 = 0, L2 = 0;
    for (int s = 0; s < N; s++) {
        if (vis[s]) continue;
        int u = s;
        if (nextNode[u] == -1) {
            vis[u] = 2;
            continue;
        }
        int top = 0;
        while (true) {
            vis[u] = 1;
            idxPos[u] = top;
            stackNodes[top++] = u;
            int v = nextNode[u];
            if (v == -1) {
                while (top > 0) vis[stackNodes[--top]] = 2;
                break;
            }
            if (vis[v] == 0) {
                u = v;
                continue;
            }
            if (vis[v] == 1) {
                int clen = top - idxPos[v];
                if (clen > L1) {
                    L2 = L1;
                    L1 = clen;
                } else if (clen > L2) {
                    L2 = clen;
                }
                while (top > 0) vis[stackNodes[--top]] = 2;
                break;
            }
            if (vis[v] == 2) {
                while (top > 0) vis[stackNodes[--top]] = 2;
                break;
            }
        }
    }
    if (L2 == 0) return 0;
    return L1 * L2;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    vector<string> s(H);
    for (int i = 0; i < H; i++) {
        if (!(cin >> s[i])) return 0;
    }
    for (int i = 0; i < H; i++) {
        for (int j = 0; j < W; j++) {
            orig[i][j] = s[i][j] - '0';
        }
    }

    int rot1[8] = {1, 2, 3, 0, 5, 4, 7, 6};
    for (int t = 0; t < 8; t++) rotate_map[t][0] = t;
    for (int r = 1; r < 4; r++) {
        for (int t = 0; t < 8; t++) {
            rotate_map[t][r] = rot1[rotate_map[t][r - 1]];
        }
    }

    // Random initial orientations
    for (int i = 0; i < H; i++) {
        for (int j = 0; j < W; j++) {
            int r0 = randInt(4);
            rotCnt[i][j] = r0;
            tileState[i][j] = rotate_map[orig[i][j]][r0];
        }
    }

    buildAllNext();
    long long curScore = computeScore();
    long long bestScore = curScore;
    for (int i = 0; i < H; i++)
        for (int j = 0; j < W; j++)
            bestRot[i][j] = rotCnt[i][j];

    auto startTime = chrono::steady_clock::now();
    const double TIME_LIMIT = 1.9; // seconds
    const double T0 = 1e6;
    const double T1 = 1e3;

    while (true) {
        double elapsed = chrono::duration<double>(chrono::steady_clock::now() - startTime).count();
        if (elapsed > TIME_LIMIT) break;
        double progress = elapsed / TIME_LIMIT;
        if (progress > 1.0) progress = 1.0;
        double T = T0 + (T1 - T0) * progress;

        int i = randInt(H);
        int j = randInt(W);

        int prevR = rotCnt[i][j];
        int prevState = tileState[i][j];

        int delta = 1 + randInt(3);
        int newR = (prevR + delta) & 3;
        rotCnt[i][j] = newR;
        tileState[i][j] = rotate_map[orig[i][j]][newR];
        recalcNextForCell(i, j);

        long long newScore = computeScore();
        long long diff = newScore - curScore;
        if (diff >= 0 || exp((double)diff / T) > randDouble()) {
            curScore = newScore;
            if (newScore > bestScore) {
                bestScore = newScore;
                for (int a = 0; a < H; a++)
                    for (int b = 0; b < W; b++)
                        bestRot[a][b] = rotCnt[a][b];
            }
        } else {
            // revert
            rotCnt[i][j] = prevR;
            tileState[i][j] = prevState;
            recalcNextForCell(i, j);
        }
    }

    string out;
    out.reserve(H * W);
    for (int i = 0; i < H; i++) {
        for (int j = 0; j < W; j++) {
            out.push_back('0' + bestRot[i][j]);
        }
    }
    cout << out << '\n';
    return 0;
}