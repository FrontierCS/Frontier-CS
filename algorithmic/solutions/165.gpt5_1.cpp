#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int N, M;
    if (!(cin >> N >> M)) return 0;
    int si, sj;
    cin >> si >> sj;
    vector<string> grid(N);
    for (int i = 0; i < N; i++) cin >> grid[i];
    vector<string> t(M);
    for (int i = 0; i < M; i++) cin >> t[i];

    // Positions for each letter
    vector<vector<int>> pos(26);
    for (int i = 0; i < N; i++) {
        for (int j = 0; j < N; j++) {
            char c = grid[i][j];
            pos[c - 'A'].push_back(i * N + j);
        }
    }

    auto manh = [&](int a, int b) -> int {
        int r1 = a / N, c1 = a % N;
        int r2 = b / N, c2 = b % N;
        return abs(r1 - r2) + abs(c1 - c2);
    };

    // DP: minimal cost to type a 5-letter word starting from start position (si,sj)
    auto minCostTypeFromStart = [&](int startId, const string& w) -> long long {
        const long long INF = (1LL<<60);
        vector<int> cells0 = pos[w[0] - 'A'];
        vector<long long> dpPrev(cells0.size(), INF);
        for (size_t j = 0; j < cells0.size(); j++) {
            dpPrev[j] = manh(startId, cells0[j]) + 1;
        }
        vector<int> prevCells = cells0;
        for (int idx = 1; idx < 5; idx++) {
            vector<int> cells = pos[w[idx] - 'A'];
            vector<long long> dpNext(cells.size(), INF);
            for (size_t j = 0; j < cells.size(); j++) {
                int idj = cells[j];
                long long best = INF;
                for (size_t i = 0; i < prevCells.size(); i++) {
                    long long cand = dpPrev[i] + manh(prevCells[i], idj) + 1;
                    if (cand < best) best = cand;
                }
                dpNext[j] = best;
            }
            dpPrev.swap(dpNext);
            prevCells.swap(cells);
        }
        long long res = (1LL<<60);
        for (auto v : dpPrev) res = min(res, v);
        return res;
    };

    // Overlap between suffix of S and prefix of word (max 4)
    auto overlapSuffixPrefix = [&](const string& S, const string& w) -> int {
        int maxr = min(4, (int)min(S.size(), w.size()));
        for (int r = maxr; r >= 1; r--) {
            bool ok = true;
            for (int k = 0; k < r; k++) {
                if (S[S.size() - r + k] != w[k]) { ok = false; break; }
            }
            if (ok) return r;
        }
        return 0;
    };

    // Estimated cost to append word w with overlap r, starting from any position of lastChar
    auto estimateAppendCost = [&](char lastChar, const string& w, int r) -> long long {
        string sub;
        if (r < (int)w.size()) sub = w.substr(r);
        if (sub.empty()) return 0;
        const long long INF = (1LL<<60);
        vector<int> prevCells = pos[lastChar - 'A'];
        vector<long long> dpPrev(prevCells.size(), 0);
        for (size_t step = 0; step < sub.size(); step++) {
            vector<int> cells = pos[sub[step] - 'A'];
            vector<long long> dpNext(cells.size(), INF);
            for (size_t j = 0; j < cells.size(); j++) {
                int idj = cells[j];
                long long best = INF;
                for (size_t i = 0; i < prevCells.size(); i++) {
                    long long cand = dpPrev[i] + manh(prevCells[i], idj) + 1;
                    if (cand < best) best = cand;
                }
                dpNext[j] = best;
            }
            dpPrev.swap(dpNext);
            prevCells.swap(cells);
        }
        long long res = (1LL<<60);
        for (auto v : dpPrev) res = min(res, v);
        return res;
    };

    // Choose first word: minimal cost from start to type it
    int startId = si * N + sj;
    int firstIdx = 0;
    long long bestStartCost = (1LL<<60);
    for (int i = 0; i < M; i++) {
        long long c = minCostTypeFromStart(startId, t[i]);
        if (c < bestStartCost) {
            bestStartCost = c;
            firstIdx = i;
        }
    }

    // Build superstring S by greedy chaining with maximum overlap from current suffix
    vector<int> used(M, 0);
    string S = t[firstIdx];
    used[firstIdx] = 1;
    int usedCnt = 1;

    while (usedCnt < M) {
        int bestK = -1;
        int bestR = -1;
        long long bestEst = (1LL<<60);
        for (int k = 0; k < M; k++) {
            if (used[k]) continue;
            int r = overlapSuffixPrefix(S, t[k]);
            if (r > bestR) {
                bestR = r;
                long long est = estimateAppendCost(S.back(), t[k], r);
                bestEst = est;
                bestK = k;
            } else if (r == bestR) {
                long long est = estimateAppendCost(S.back(), t[k], r);
                if (est < bestEst) {
                    bestEst = est;
                    bestK = k;
                }
            }
        }
        if (bestK == -1) {
            // Should not happen; pick any remaining
            for (int k = 0; k < M; k++) if (!used[k]) { bestK = k; bestR = 0; break; }
        }
        int r = overlapSuffixPrefix(S, t[bestK]);
        S += t[bestK].substr(r);
        used[bestK] = 1;
        usedCnt++;
    }

    // DP across S to select positions
    int L = (int)S.size();
    vector<vector<int>> stepCells(L);
    vector<vector<int>> pred(L);
    const long long INF = (1LL<<60);

    // Step 0
    stepCells[0] = pos[S[0] - 'A'];
    vector<long long> dpPrev(stepCells[0].size(), INF);
    for (size_t j = 0; j < stepCells[0].size(); j++) {
        dpPrev[j] = manh(startId, stepCells[0][j]) + 1;
    }

    // Steps 1..L-1
    for (int idx = 1; idx < L; idx++) {
        stepCells[idx] = pos[S[idx] - 'A'];
        vector<long long> dpNext(stepCells[idx].size(), INF);
        vector<int> pr(stepCells[idx].size(), -1);
        for (size_t j = 0; j < stepCells[idx].size(); j++) {
            int idj = stepCells[idx][j];
            long long best = INF;
            int bestp = -1;
            for (size_t i = 0; i < stepCells[idx-1].size(); i++) {
                long long cand = dpPrev[i] + manh(stepCells[idx-1][i], idj) + 1;
                if (cand < best) {
                    best = cand;
                    bestp = (int)i;
                }
            }
            dpNext[j] = best;
            pr[j] = bestp;
        }
        pred[idx] = pr;
        dpPrev.swap(dpNext);
    }

    // Backtrack
    int lastBestIdx = 0;
    for (size_t j = 1; j < dpPrev.size(); j++) {
        if (dpPrev[j] < dpPrev[lastBestIdx]) lastBestIdx = (int)j;
    }
    vector<int> chosen(L);
    chosen[L-1] = stepCells[L-1][lastBestIdx];
    int curIdx = lastBestIdx;
    for (int idx = L-1; idx >= 1; idx--) {
        int prevIdx = pred[idx][curIdx];
        chosen[idx-1] = stepCells[idx-1][prevIdx];
        curIdx = prevIdx;
    }

    // Output operations: one coordinate per typed letter
    for (int i = 0; i < L; i++) {
        int id = chosen[i];
        int r = id / N, c = id % N;
        cout << r << ' ' << c << '\n';
    }
    return 0;
}