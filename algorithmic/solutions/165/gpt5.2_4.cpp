#include <bits/stdc++.h>
using namespace std;

static inline int encode5(const string &s) {
    int x = 0;
    for (char ch : s) x = x * 26 + (ch - 'A');
    return x;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int N, M;
    cin >> N >> M;
    int si, sj;
    cin >> si >> sj;

    vector<string> grid(N);
    for (int i = 0; i < N; i++) cin >> grid[i];

    vector<vector<int>> letterCells(26);
    auto cellId = [&](int i, int j) { return i * N + j; };
    auto cellPos = [&](int id) { return pair<int,int>(id / N, id % N); };

    for (int i = 0; i < N; i++) {
        for (int j = 0; j < N; j++) {
            int c = grid[i][j] - 'A';
            letterCells[c].push_back(cellId(i, j));
        }
    }

    int V = N * N;
    vector<vector<unsigned short>> dist(V, vector<unsigned short>(V));
    for (int a = 0; a < V; a++) {
        auto [ai, aj] = cellPos(a);
        for (int b = 0; b < V; b++) {
            auto [bi, bj] = cellPos(b);
            dist[a][b] = (unsigned short)(abs(ai - bi) + abs(aj - bj));
        }
    }

    vector<string> t(M);
    vector<int> tCode(M);
    for (int i = 0; i < M; i++) {
        cin >> t[i];
        tCode[i] = encode5(t[i]);
    }

    // Choose initial string whose first letter is closest to the start (rough heuristic).
    int startCell = cellId(si, sj);
    int startIdx = 0;
    int bestInit = INT_MAX;
    for (int i = 0; i < M; i++) {
        int c = t[i][0] - 'A';
        int bestD = INT_MAX;
        for (int p : letterCells[c]) bestD = min(bestD, (int)dist[startCell][p]);
        if (bestD < bestInit) {
            bestInit = bestD;
            startIdx = i;
        }
    }

    string S = t[startIdx];

    vector<char> covered(M, 0);

    auto rebuildCovered = [&]() -> int {
        unordered_set<int> grams;
        grams.reserve(S.size() * 2 + 16);
        for (int i = 0; i + 5 <= (int)S.size(); i++) {
            grams.insert(encode5(S.substr(i, 5)));
        }
        int cnt = 0;
        for (int i = 0; i < M; i++) {
            if (!covered[i] && grams.find(tCode[i]) != grams.end()) covered[i] = 1;
            if (covered[i]) cnt++;
        }
        return cnt;
    };

    int coveredCnt = rebuildCovered();

    auto overlapLen = [&](const string &a, const string &b) -> int {
        int maxL = min(4, (int)min(a.size(), b.size()));
        for (int l = maxL; l >= 1; l--) {
            bool ok = true;
            for (int k = 0; k < l; k++) {
                if (a[a.size() - l + k] != b[k]) {
                    ok = false;
                    break;
                }
            }
            if (ok) return l;
        }
        return 0;
    };

    // Greedy: repeatedly append an uncovered t_i with maximum overlap to the current suffix.
    for (int it = 0; it < M && coveredCnt < M; it++) {
        int bestI = -1, bestOv = -1;
        int bestAddLen = INT_MAX;

        for (int i = 0; i < M; i++) if (!covered[i]) {
            int ov = overlapLen(S, t[i]);
            int addLen = 5 - ov;
            if (ov > bestOv || (ov == bestOv && addLen < bestAddLen) || (ov == bestOv && addLen == bestAddLen && i < bestI)) {
                bestOv = ov;
                bestAddLen = addLen;
                bestI = i;
            }
        }

        if (bestI == -1) break;
        S += t[bestI].substr(bestOv);
        coveredCnt = rebuildCovered();
        if ((int)S.size() > 5000) break; // safety; should never happen with constraints.
    }

    // Generate operations: for each char in S, move to a chosen cell with that letter.
    int cur = startCell;
    vector<pair<int,int>> ops;
    ops.reserve(S.size());

    for (int idx = 0; idx < (int)S.size(); idx++) {
        int c = S[idx] - 'A';
        const auto &cells = letterCells[c];

        int nextC = -1;
        const vector<int> *nextCells = nullptr;
        if (idx + 1 < (int)S.size()) {
            nextC = S[idx + 1] - 'A';
            nextCells = &letterCells[nextC];
        }

        int bestP = cells[0];
        int bestScore = INT_MAX;

        if (nextCells && !nextCells->empty()) {
            for (int p : cells) {
                int d1 = dist[cur][p];
                int d2 = INT_MAX;
                for (int q : *nextCells) d2 = min(d2, (int)dist[p][q]);
                int score = d1 + d2;
                if (score < bestScore) {
                    bestScore = score;
                    bestP = p;
                }
            }
        } else {
            for (int p : cells) {
                int d1 = dist[cur][p];
                if (d1 < bestScore) {
                    bestScore = d1;
                    bestP = p;
                }
            }
        }

        auto [pi, pj] = cellPos(bestP);
        ops.push_back({pi, pj});
        cur = bestP;
        if ((int)ops.size() >= 5000) break; // safety
    }

    for (auto [i, j] : ops) {
        cout << i << ' ' << j << '\n';
    }
    return 0;
}