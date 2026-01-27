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

    // Build a superstring S that contains all t[i] as substrings using greedy pairwise merging with overlap up to 4
    auto overlap4 = [](const string &a, const string &b) -> int {
        int la = (int)a.size(), lb = (int)b.size();
        int mx = min(4, min(la, lb));
        for (int k = mx; k >= 1; --k) {
            bool ok = true;
            for (int u = 0; u < k; ++u) {
                if (a[la - k + u] != b[u]) { ok = false; break; }
            }
            if (ok) return k;
        }
        return 0;
    };

    vector<string> words = t;
    while ((int)words.size() > 1) {
        int n = (int)words.size();
        int bi = 0, bj = 1, bov = -1;
        for (int i = 0; i < n; ++i) {
            for (int j = 0; j < n; ++j) if (i != j) {
                int ov = overlap4(words[i], words[j]);
                if (ov > bov) { bov = ov; bi = i; bj = j; }
            }
        }
        string merged = words[bi] + words[bj].substr(bov);
        if (bi > bj) swap(bi, bj);
        words.erase(words.begin() + bj);
        words.erase(words.begin() + bi);
        words.push_back(move(merged));
    }
    string S = words.empty() ? string() : words[0];

    // Prepare cell lists by character
    int SZ = N * N;
    vector<int> cell_i(SZ), cell_j(SZ);
    for (int i = 0; i < N; ++i) for (int j = 0; j < N; ++j) {
        int id = i * N + j;
        cell_i[id] = i;
        cell_j[id] = j;
    }
    vector<vector<int>> cellsByChar(26);
    for (int i = 0; i < N; ++i) for (int j = 0; j < N; ++j) {
        int c = grid[i][j] - 'A';
        cellsByChar[c].push_back(i * N + j);
    }

    // DP to choose sequence of cells minimizing movement cost
    int L = (int)S.size();
    if (L == 0) return 0;

    vector<vector<int>> candIds(L);
    for (int tpos = 0; tpos < L; ++tpos) {
        int c = S[tpos] - 'A';
        candIds[tpos] = cellsByChar[c];
    }

    auto manh = [&](int id1, int id2) -> int {
        return abs(cell_i[id1] - cell_i[id2]) + abs(cell_j[id1] - cell_j[id2]);
    };

    vector<int> prevIds = candIds[0];
    int K0 = (int)prevIds.size();
    vector<int> prevCost(K0, INT_MAX/4);
    vector<vector<int>> parent(L);
    parent[0].assign(K0, -1);
    int startId = si * N + sj;
    for (int idx = 0; idx < K0; ++idx) {
        prevCost[idx] = manh(startId, prevIds[idx]) + 1;
    }

    for (int tpos = 1; tpos < L; ++tpos) {
        vector<int> &currIds = candIds[tpos];
        int Kc = (int)currIds.size();
        vector<int> currCost(Kc, INT_MAX/4);
        parent[tpos].assign(Kc, -1);
        for (int xi = 0; xi < Kc; ++xi) {
            int x = currIds[xi];
            int best = INT_MAX/4, bestp = -1;
            for (int yi = 0; yi < (int)prevIds.size(); ++yi) {
                int y = prevIds[yi];
                int cost = prevCost[yi] + manh(y, x) + 1;
                if (cost < best) { best = cost; bestp = prevIds[yi]; }
            }
            currCost[xi] = best;
            parent[tpos][xi] = bestp;
        }
        prevIds.swap(currIds); // careful: we need currIds later for backtrack; do not modify candIds
        // swap back to preserve candIds: We'll not swap to avoid corrupting candIds.
        // Instead, set prevIds = candIds[tpos]; and keep prevCost
        prevIds = candIds[tpos];
        prevCost.swap(currCost);
    }

    // Reconstruction
    vector<int> chosenIds(L);
    // Find best at last position
    int lastIdx = 0;
    int bestCost = INT_MAX/4;
    for (int idx = 0; idx < (int)candIds[L-1].size(); ++idx) {
        if (prevCost[idx] < bestCost) { bestCost = prevCost[idx]; lastIdx = idx; }
    }
    chosenIds[L-1] = candIds[L-1][lastIdx];
    for (int tpos = L-1; tpos >= 1; --tpos) {
        int pid = parent[tpos][lastIdx];
        chosenIds[tpos-1] = pid;
        // find index of pid in candIds[tpos-1]
        int found = 0;
        for (int yi = 0; yi < (int)candIds[tpos-1].size(); ++yi) {
            if (candIds[tpos-1][yi] == pid) { lastIdx = yi; found = 1; break; }
        }
        if (!found) lastIdx = 0; // fallback (should not happen)
    }

    // Output the sequence of coordinates
    for (int tpos = 0; tpos < L; ++tpos) {
        int id = chosenIds[tpos];
        cout << cell_i[id] << ' ' << cell_j[id] << '\n';
    }
    return 0;
}