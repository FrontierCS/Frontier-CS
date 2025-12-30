#include <bits/stdc++.h>
using namespace std;

static inline uint64_t rng64() {
    static uint64_t x = chrono::steady_clock::now().time_since_epoch().count();
    x ^= x << 7;
    x ^= x >> 9;
    return x;
}
static inline int randint(int l, int r) {
    return (int)(rng64() % (uint64_t)(r - l + 1)) + l;
}

struct Timer {
    chrono::steady_clock::time_point st;
    Timer() { st = chrono::steady_clock::now(); }
    double elapsed() const {
        auto ed = chrono::steady_clock::now();
        return chrono::duration<double>(ed - st).count();
    }
};

static inline bool occursInCycle(const string &cycle, const string &pattern) {
    int N = (int)cycle.size();
    int k = (int)pattern.size();
    if (k > N) return false;
    char first = pattern[0];
    for (int start = 0; start < N; ++start) {
        if (cycle[start] != first) continue;
        int idx = start + 1;
        if (idx == N) idx = 0;
        int p = 1;
        for (; p < k; ++p) {
            if (cycle[idx] != pattern[p]) break;
            ++idx; if (idx == N) idx = 0;
        }
        if (p == k) return true;
    }
    return false;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int N, M;
    if (!(cin >> N >> M)) {
        return 0;
    }
    vector<string> S(M);
    for (int i = 0; i < M; ++i) cin >> S[i];

    // Initialize rows
    vector<string> rows(N, string(N, 'A'));
    // Choose seeds from top by length
    vector<int> ord(M);
    iota(ord.begin(), ord.end(), 0);
    sort(ord.begin(), ord.end(), [&](int a, int b){
        if (S[a].size() != S[b].size()) return S[a].size() > S[b].size();
        return a < b;
    });
    int topK = min(M, 200);

    for (int i = 0; i < N; ++i) {
        bool useSeed = (i < N/2) || (topK > 0);
        if (useSeed && topK > 0) {
            int idx = ord[randint(0, topK-1)];
            const string &t = S[idx];
            int shift = randint(0, N-1);
            for (int j = 0; j < N; ++j) {
                rows[i][(j + shift) % N] = t[j % (int)t.size()];
            }
        } else {
            for (int j = 0; j < N; ++j) rows[i][j] = char('A' + randint(0,7));
        }
    }

    // Build columns from rows
    vector<string> cols(N, string(N, 'A'));
    for (int j = 0; j < N; ++j) {
        for (int i = 0; i < N; ++i) cols[j][i] = rows[i][j];
    }

    // Precompute matches
    vector<vector<uint8_t>> rowMatch(N, vector<uint8_t>(M, 0));
    vector<vector<uint8_t>> colMatch(N, vector<uint8_t>(M, 0));
    vector<int> cntR(M, 0), cntC(M, 0);
    for (int r = 0; r < N; ++r) {
        for (int i = 0; i < M; ++i) {
            rowMatch[r][i] = occursInCycle(rows[r], S[i]);
            if (rowMatch[r][i]) cntR[i]++;
        }
    }
    for (int c = 0; c < N; ++c) {
        for (int i = 0; i < M; ++i) {
            colMatch[c][i] = occursInCycle(cols[c], S[i]);
            if (colMatch[c][i]) cntC[i]++;
        }
    }
    int covered = 0;
    for (int i = 0; i < M; ++i) {
        if (cntR[i] > 0 || cntC[i] > 0) covered++;
    }

    vector<string> bestRows = rows;
    int bestCovered = covered;

    // SA parameters
    Timer timer;
    const double TL = 0.9; // time limit in seconds (conservative)
    const double T0 = 1.0, T1 = 0.01;

    vector<uint8_t> newRowMatch(M), newColMatch(M);

    while (timer.elapsed() < TL) {
        int r = randint(0, N-1);
        int j = randint(0, N-1);
        char oldCh = rows[r][j];
        char newCh;
        do { newCh = char('A' + randint(0,7)); } while (newCh == oldCh);

        string rowCand = rows[r];
        rowCand[j] = newCh;
        int cidx = j;
        string colCand = cols[cidx];
        colCand[r] = newCh;

        int delta = 0;
        for (int i = 0; i < M; ++i) {
            bool nr = occursInCycle(rowCand, S[i]);
            bool nc = occursInCycle(colCand, S[i]);
            newRowMatch[i] = (uint8_t)nr;
            newColMatch[i] = (uint8_t)nc;

            int oldR = rowMatch[r][i];
            int oldC = colMatch[cidx][i];

            bool oldCov = (cntR[i] > 0 || cntC[i] > 0);
            int newCntR = cntR[i] - oldR + (int)nr;
            int newCntC = cntC[i] - oldC + (int)nc;
            bool newCov = (newCntR > 0 || newCntC > 0);
            delta += (int)newCov - (int)oldCov;
        }

        double t = timer.elapsed() / TL;
        if (t > 1.0) t = 1.0;
        double Temp = T0 + (T1 - T0) * t;
        bool accept = false;
        if (delta >= 0) accept = true;
        else {
            double prob = exp((double)delta / Temp);
            uint64_t r64 = rng64();
            double rv = (r64 >> 11) * (1.0 / 9007199254740992.0); // uniform [0,1)
            if (rv < prob) accept = true;
        }

        if (accept) {
            rows[r][j] = newCh;
            cols[cidx][r] = newCh;
            for (int i = 0; i < M; ++i) {
                int oldR = rowMatch[r][i];
                int oldC = colMatch[cidx][i];
                if (oldR != newRowMatch[i]) {
                    rowMatch[r][i] = newRowMatch[i];
                    cntR[i] += (int)newRowMatch[i] - oldR;
                }
                if (oldC != newColMatch[i]) {
                    colMatch[cidx][i] = newColMatch[i];
                    cntC[i] += (int)newColMatch[i] - oldC;
                }
            }
            covered += delta;
            if (covered > bestCovered) {
                bestCovered = covered;
                bestRows = rows;
            }
        }
    }

    // Output best rows
    for (int i = 0; i < N; ++i) {
        cout << bestRows[i] << '\n';
    }
    return 0;
}