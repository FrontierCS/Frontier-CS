#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    int n, m;
    if (!(cin >> n >> m)) return 0;
    vector<string> s(m);
    for (int i = 0; i < m; ++i) cin >> s[i];

    // Early check: if any pattern is all '?', probability is 1
    for (int i = 0; i < m; ++i) {
        bool allq = true;
        for (char c : s[i]) if (c != '?') { allq = false; break; }
        if (allq) {
            cout.setf(std::ios::fixed); cout << setprecision(15) << 1.0 << "\n";
            return 0;
        }
    }

    int W = (n + 63) >> 6; // number of 64-bit words
    using ULL = unsigned long long;

    // Prepare per-pattern per-letter bitsets
    vector<vector<ULL>> A(m, vector<ULL>(W, 0)), C(m, vector<ULL>(W, 0)), G(m, vector<ULL>(W, 0)), T(m, vector<ULL>(W, 0));
    for (int i = 0; i < m; ++i) {
        for (int j = 0; j < n; ++j) {
            char ch = s[i][j];
            if (ch == '?') continue;
            int w = j >> 6;
            int b = j & 63;
            ULL bit = (ULL)1 << b;
            if (ch == 'A') A[i][w] |= bit;
            else if (ch == 'C') C[i][w] |= bit;
            else if (ch == 'G') G[i][w] |= bit;
            else if (ch == 'T') T[i][w] |= bit;
        }
    }

    // Precompute changed words per pattern to speed updates
    vector<vector<int>> changedWords(m);
    for (int i = 0; i < m; ++i) {
        for (int w = 0; w < W; ++w) {
            if ((A[i][w] | C[i][w] | G[i][w] | T[i][w]) != 0) {
                changedWords[i].push_back(w);
            }
        }
    }

    // Precompute powers of 1/4
    vector<double> pow4(n + 1, 1.0);
    for (int i = 1; i <= n; ++i) pow4[i] = pow4[i - 1] * 0.25;

    // Global seen bitsets
    vector<ULL> seenA(W, 0), seenC(W, 0), seenG(W, 0), seenT(W, 0);

    double ans = 0.0;

    // Save buffers per depth for restoration
    vector<vector<ULL>> saveA(m), saveC(m), saveG(m), saveT(m);

    function<void(int, int, int)> dfs = [&](int idx, int chosenCnt, int assignedCnt) {
        if (idx == m) {
            if (chosenCnt > 0) {
                double contrib = pow4[assignedCnt];
                if (chosenCnt & 1) ans += contrib;
                else ans -= contrib;
            }
            return;
        }
        // Skip current pattern
        dfs(idx + 1, chosenCnt, assignedCnt);

        // Include current pattern
        const auto& cw = changedWords[idx];
        int len = (int)cw.size();
        saveA[idx].resize(len);
        saveC[idx].resize(len);
        saveG[idx].resize(len);
        saveT[idx].resize(len);
        int delta = 0;

        for (int t = 0; t < len; ++t) {
            int w = cw[t];
            ULL oA = seenA[w], oC = seenC[w], oG = seenG[w], oT = seenT[w];
            saveA[idx][t] = oA; saveC[idx][t] = oC; saveG[idx][t] = oG; saveT[idx][t] = oT;

            ULL oU = oA | oC | oG | oT;
            ULL oX1 = oA & (oC | oG | oT);
            ULL oX2 = oC & (oG | oT);
            ULL oX3 = oG & oT;
            ULL oConf = oX1 | oX2 | oX3;
            int oldGood = __builtin_popcountll(oU & ~oConf);

            ULL nA = oA | A[idx][w];
            ULL nC = oC | C[idx][w];
            ULL nG = oG | G[idx][w];
            ULL nT = oT | T[idx][w];
            seenA[w] = nA; seenC[w] = nC; seenG[w] = nG; seenT[w] = nT;

            ULL nU = nA | nC | nG | nT;
            ULL nX1 = nA & (nC | nG | nT);
            ULL nX2 = nC & (nG | nT);
            ULL nX3 = nG & nT;
            ULL nConf = nX1 | nX2 | nX3;
            int newGood = __builtin_popcountll(nU & ~nConf);

            delta += (newGood - oldGood);
        }

        dfs(idx + 1, chosenCnt + 1, assignedCnt + delta);

        // Restore
        for (int t = 0; t < len; ++t) {
            int w = cw[t];
            seenA[w] = saveA[idx][t];
            seenC[w] = saveC[idx][t];
            seenG[w] = saveG[idx][t];
            seenT[w] = saveT[idx][t];
        }
    };

    dfs(0, 0, 0);

    cout.setf(std::ios::fixed);
    cout << setprecision(15) << ans << "\n";
    return 0;
}