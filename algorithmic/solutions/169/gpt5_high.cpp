#include <bits/stdc++.h>
using namespace std;

struct Cand {
    char dir; // 'U','D','L','R'
    int idx;  // column for U/D, row for L/R
    int k;    // number of shifts one way (total cost = 2*k)
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    int N;
    if (!(cin >> N)) return 0;
    vector<string> C(N);
    for (int i = 0; i < N; i++) cin >> C[i];

    vector<vector<bool>> fuku(N, vector<bool>(N, false));
    vector<vector<bool>> alive(N, vector<bool>(N, false));
    int aliveCount = 0;
    for (int i = 0; i < N; i++) {
        for (int j = 0; j < N; j++) {
            if (C[i][j] == 'o') fuku[i][j] = true;
            if (C[i][j] == 'x') { alive[i][j] = true; aliveCount++; }
        }
    }

    // Generate all safe candidates (segments without any Fuku)
    vector<Cand> cands;
    cands.reserve(4 * N * N);
    // Columns: Up and Down
    for (int j = 0; j < N; j++) {
        int topLen = 0;
        while (topLen < N && !fuku[topLen][j]) topLen++;
        for (int k = 1; k <= topLen; k++) cands.push_back({'U', j, k});
        int botLen = 0;
        while (botLen < N && !fuku[N - 1 - botLen][j]) botLen++;
        for (int k = 1; k <= botLen; k++) cands.push_back({'D', j, k});
    }
    // Rows: Left and Right
    for (int i = 0; i < N; i++) {
        int leftLen = 0;
        while (leftLen < N && !fuku[i][leftLen]) leftLen++;
        for (int k = 1; k <= leftLen; k++) cands.push_back({'L', i, k});
        int rightLen = 0;
        while (rightLen < N && !fuku[i][N - 1 - rightLen]) rightLen++;
        for (int k = 1; k <= rightLen; k++) cands.push_back({'R', i, k});
    }

    vector<pair<char,int>> ops;
    ops.reserve(4 * N * N);

    auto countGain = [&](const Cand &c)->int{
        int k = c.k, idx = c.idx;
        int cnt = 0;
        if (c.dir == 'U') {
            int j = idx;
            for (int r = 0; r < k; r++) if (alive[r][j]) cnt++;
        } else if (c.dir == 'D') {
            int j = idx;
            for (int r = N - k; r < N; r++) if (alive[r][j]) cnt++;
        } else if (c.dir == 'L') {
            int i = idx;
            for (int col = 0; col < k; col++) if (alive[i][col]) cnt++;
        } else { // 'R'
            int i = idx;
            for (int col = N - k; col < N; col++) if (alive[i][col]) cnt++;
        }
        return cnt;
    };

    auto apply = [&](const Cand &c){
        int k = c.k, idx = c.idx;
        if (c.dir == 'U') {
            for (int t = 0; t < k; t++) ops.push_back({'U', idx});
            for (int t = 0; t < k; t++) ops.push_back({'D', idx});
            int j = idx;
            for (int r = 0; r < k; r++) {
                if (alive[r][j]) { alive[r][j] = false; aliveCount--; }
            }
        } else if (c.dir == 'D') {
            for (int t = 0; t < k; t++) ops.push_back({'D', idx});
            for (int t = 0; t < k; t++) ops.push_back({'U', idx});
            int j = idx;
            for (int r = N - k; r < N; r++) {
                if (alive[r][j]) { alive[r][j] = false; aliveCount--; }
            }
        } else if (c.dir == 'L') {
            for (int t = 0; t < k; t++) ops.push_back({'L', idx});
            for (int t = 0; t < k; t++) ops.push_back({'R', idx});
            int i = idx;
            for (int col = 0; col < k; col++) {
                if (alive[i][col]) { alive[i][col] = false; aliveCount--; }
            }
        } else { // 'R'
            for (int t = 0; t < k; t++) ops.push_back({'R', idx});
            for (int t = 0; t < k; t++) ops.push_back({'L', idx});
            int i = idx;
            for (int col = N - k; col < N; col++) {
                if (alive[i][col]) { alive[i][col] = false; aliveCount--; }
            }
        }
    };

    while (aliveCount > 0) {
        int bestIdx = -1;
        long long bestScore = LLONG_MIN;
        for (int cid = 0; cid < (int)cands.size(); cid++) {
            int gain = countGain(cands[cid]);
            if (gain == 0) continue;
            int cost = 2 * cands[cid].k;
            long long score = (long long)gain * 1000 - cost; // prioritize gain strongly
            if (score > bestScore) {
                bestScore = score;
                bestIdx = cid;
            }
        }
        if (bestIdx == -1) {
            // Fallback: pick first alive Oni and remove it by minimal safe direction
            bool found = false;
            for (int i = 0; i < N && !found; i++) {
                for (int j = 0; j < N && !found; j++) {
                    if (!alive[i][j]) continue;
                    vector<pair<int, Cand>> options;
                    bool can = true;
                    for (int r = 0; r < i; r++) if (fuku[r][j]) { can = false; break; }
                    if (can) options.push_back({2 * (i + 1), Cand{'U', j, i + 1}});
                    can = true;
                    for (int r = i + 1; r < N; r++) if (fuku[r][j]) { can = false; break; }
                    if (can) options.push_back({2 * (N - i), Cand{'D', j, N - i}});
                    can = true;
                    for (int c = 0; c < j; c++) if (fuku[i][c]) { can = false; break; }
                    if (can) options.push_back({2 * (j + 1), Cand{'L', i, j + 1}});
                    can = true;
                    for (int c = j + 1; c < N; c++) if (fuku[i][c]) { can = false; break; }
                    if (can) options.push_back({2 * (N - j), Cand{'R', i, N - j}});
                    if (!options.empty()) {
                        sort(options.begin(), options.end(), [](const auto &a, const auto &b){
                            if (a.first != b.first) return a.first < b.first;
                            return false;
                        });
                        Cand chosen = options[0].second;
                        if ((int)ops.size() + 2 * chosen.k <= 4 * N * N) apply(chosen);
                        found = true;
                    }
                }
            }
            if (!found) break;
        } else {
            Cand c = cands[bestIdx];
            if ((int)ops.size() + 2 * c.k > 4 * N * N) break;
            apply(c);
        }
    }

    for (auto &op : ops) {
        cout << op.first << ' ' << op.second << '\n';
    }
    return 0;
}