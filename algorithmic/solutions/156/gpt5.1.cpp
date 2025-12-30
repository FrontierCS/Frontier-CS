#include <bits/stdc++.h>
using namespace std;

using ll = long long;
using Clock = chrono::steady_clock;

const int N = 30;
const int TOT = N * N;
const int MAX_STATES = 4000;

int baseTile[TOT];
int orientationArr[TOT];
int bestOrientationArr[TOT];
int actualTileArr[TOT];

int rotTile[8][4];
int rotateOnceMap[8] = {1, 2, 3, 0, 5, 4, 7, 6};
int TO_TABLE[8][4] = {
    {1, 0, -1, -1},
    {3, -1, -1, 0},
    {-1, -1, 3, 2},
    {-1, 2, 1, -1},
    {1, 0, 3, 2},
    {3, 2, 1, 0},
    {2, -1, 0, -1},
    {-1, 3, -1, 1},
};

int di[4] = {0, -1, 0, 1};
int dj[4] = {-1, 0, 1, 0};

int stateId[N][N][4];
int S_states = 0;
int s_i[MAX_STATES], s_j[MAX_STATES], s_d[MAX_STATES];

int nextStateArr[MAX_STATES];
int indegArr[MAX_STATES];
unsigned char visArr[MAX_STATES];

inline ll Evaluate(const int *orient) {
    // Compute actual tile type for each cell under given orientation.
    for (int idx = 0; idx < TOT; ++idx) {
        int t0 = baseTile[idx];
        int r = orient[idx];
        actualTileArr[idx] = rotTile[t0][r];
    }

    // Build next-state function and indegrees.
    for (int s = 0; s < S_states; ++s) indegArr[s] = 0;

    for (int s = 0; s < S_states; ++s) {
        int i = s_i[s];
        int j = s_j[s];
        int d = s_d[s];

        int tile = actualTileArr[i * N + j];
        int d2 = TO_TABLE[tile][d];

        if (d2 == -1) {
            nextStateArr[s] = -1;
            continue;
        }

        int ni = i + di[d2];
        int nj = j + dj[d2];
        if (ni < 0 || ni >= N || nj < 0 || nj >= N) {
            nextStateArr[s] = -1;
            continue;
        }

        int nd = (d2 + 2) & 3;
        int ns = stateId[ni][nj][nd];
        // ns should be valid
        nextStateArr[s] = ns;
        indegArr[ns]++;
    }

    // Kahn's algorithm to remove nodes not in cycles.
    static int q[MAX_STATES];
    int qh = 0, qt = 0;
    for (int s = 0; s < S_states; ++s) {
        if (indegArr[s] == 0) q[qt++] = s;
    }
    while (qh < qt) {
        int v = q[qh++];
        int w = nextStateArr[v];
        if (w != -1) {
            if (--indegArr[w] == 0) q[qt++] = w;
        }
    }

    // Find cycles and their lengths.
    memset(visArr, 0, S_states);
    ll best1 = 0, best2 = 0;
    int loopsCount = 0;

    for (int s = 0; s < S_states; ++s) {
        if (indegArr[s] > 0 && !visArr[s]) {
            loopsCount++;
            int cur = s;
            int len = 0;
            do {
                visArr[cur] = 1;
                cur = nextStateArr[cur];
                ++len;
            } while (cur != s);
            if (len > best1) {
                best2 = best1;
                best1 = len;
            } else if (len > best2) {
                best2 = len;
            }
        }
    }

    if (loopsCount >= 2) return best1 * best2;
    return 0;
}

void init_states() {
    S_states = 0;
    for (int i = 0; i < N; ++i) {
        for (int j = 0; j < N; ++j) {
            for (int d = 0; d < 4; ++d) {
                int pi = i + di[d];
                int pj = j + dj[d];
                if (pi >= 0 && pi < N && pj >= 0 && pj < N) {
                    stateId[i][j][d] = S_states;
                    s_i[S_states] = i;
                    s_j[S_states] = j;
                    s_d[S_states] = d;
                    ++S_states;
                } else {
                    stateId[i][j][d] = -1;
                }
            }
        }
    }
}

void localSearchLimited(int *orient, ll &currentScore, ll &bestScore, int maxPass) {
    for (int pass = 0; pass < maxPass; ++pass) {
        bool improvedGlobal = false;
        for (int idx = 0; idx < TOT; ++idx) {
            int origR = orient[idx];
            ll bestLocalScore = currentScore;
            int bestR = origR;

            for (int r = 0; r < 4; ++r) {
                if (r == origR) continue;
                orient[idx] = r;
                ll sc = Evaluate(orient);
                if (sc > bestLocalScore) {
                    bestLocalScore = sc;
                    bestR = r;
                }
            }

            orient[idx] = bestR;
            if (bestLocalScore > currentScore) {
                currentScore = bestLocalScore;
                improvedGlobal = true;
                if (bestLocalScore > bestScore) {
                    bestScore = bestLocalScore;
                    memcpy(bestOrientationArr, orient, sizeof(int) * TOT);
                }
            }
        }
        if (!improvedGlobal) break;
    }
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    // Read input
    for (int i = 0; i < N; ++i) {
        string s;
        if (!(cin >> s)) return 0;
        for (int j = 0; j < N; ++j) {
            baseTile[i * N + j] = s[j] - '0';
        }
    }

    // Precompute rotation mappings.
    for (int t = 0; t < 8; ++t) {
        rotTile[t][0] = t;
        for (int r = 1; r < 4; ++r) {
            rotTile[t][r] = rotateOnceMap[rotTile[t][r - 1]];
        }
    }

    // Initialize state graph structure (independent of orientations).
    init_states();

    mt19937_64 rng((uint64_t)chrono::high_resolution_clock::now().time_since_epoch().count());
    const double TIME_LIMIT = 1.9;
    auto startTime = Clock::now();

    // Initial random orientation.
    for (int i = 0; i < TOT; ++i) {
        orientationArr[i] = rng() & 3;
    }

    ll currentScore = Evaluate(orientationArr);
    ll bestScore = currentScore;
    memcpy(bestOrientationArr, orientationArr, sizeof(int) * TOT);

    // Temperature calibration by sampling a few random moves.
    const int SAMPLE_ITERS = 200;
    long double sumAbsDelta = 0.0L;
    int sampleCount = 0;
    for (int k = 0; k < SAMPLE_ITERS; ++k) {
        int idx = (int)(rng() % TOT);
        int oldR = orientationArr[idx];
        int newR = (int)(rng() % 3);
        if (newR >= oldR) newR++;
        orientationArr[idx] = newR;
        ll newScore = Evaluate(orientationArr);
        ll delta = newScore - currentScore;
        sumAbsDelta += llabs(delta);
        ++sampleCount;
        orientationArr[idx] = oldR;
    }
    long double avgDelta = (sampleCount ? sumAbsDelta / sampleCount : 1.0L);
    double T0 = (double)avgDelta * 5.0;
    double T1 = (double)avgDelta * 0.1;
    if (T0 < 1.0) T0 = 1.0;
    if (T1 < 0.01) T1 = 0.01;

    // First local search pass from initial solution.
    localSearchLimited(orientationArr, currentScore, bestScore, 1);

    // Ensure bestOrientationArr matches bestScore (localSearch keeps non-decreasing).
    // If bestScore improved in localSearch, bestOrientationArr already updated.
    // Otherwise, bestOrientationArr was from initial orientation; orientationArr may be same or better.
    // To start SA from current best, sync orientationArr with bestOrientationArr.
    memcpy(orientationArr, bestOrientationArr, sizeof(int) * TOT);
    currentScore = bestScore;

    // Simulated Annealing
    const int MAX_SA_ITERS = 15000;
    double elapsed = 0.0;
    double T = T0;

    for (int iter = 0; iter < MAX_SA_ITERS; ++iter) {
        if ((iter & 127) == 0) {
            elapsed = chrono::duration<double>(Clock::now() - startTime).count();
            if (elapsed > TIME_LIMIT) break;
            double progress = elapsed / TIME_LIMIT;
            if (progress > 1.0) progress = 1.0;
            T = T0 + (T1 - T0) * progress;
            if (T < 0.01) T = 0.01;
        }

        int idx = (int)(rng() % TOT);
        int oldR = orientationArr[idx];
        int newR = (int)(rng() % 3);
        if (newR >= oldR) newR++;
        orientationArr[idx] = newR;

        ll newScore = Evaluate(orientationArr);
        ll delta = newScore - currentScore;

        if (delta >= 0) {
            currentScore = newScore;
            if (newScore > bestScore) {
                bestScore = newScore;
                memcpy(bestOrientationArr, orientationArr, sizeof(int) * TOT);
            }
        } else {
            double prob = exp((double)delta / T);
            double r01 = (double)rng() / (double)rng.max();
            if (r01 < prob) {
                currentScore = newScore;
            } else {
                orientationArr[idx] = oldR; // revert
            }
        }
    }

    // Optional final local search from best solution if time allows.
    elapsed = chrono::duration<double>(Clock::now() - startTime).count();
    if (elapsed < TIME_LIMIT * 0.7) {
        memcpy(orientationArr, bestOrientationArr, sizeof(int) * TOT);
        currentScore = bestScore;
        localSearchLimited(orientationArr, currentScore, bestScore, 1);
        memcpy(bestOrientationArr, orientationArr, sizeof(int) * TOT);
    }

    // Output best orientation found.
    string ans;
    ans.reserve(TOT);
    for (int i = 0; i < TOT; ++i) {
        int r = bestOrientationArr[i];
        if (r < 0) r = 0;
        if (r > 3) r = 3;
        ans.push_back(char('0' + r));
    }
    cout << ans << '\n';

    return 0;
}