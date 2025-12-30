#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int N;
    if (!(cin >> N)) return 0;
    vector<string> C(N);
    for (int i = 0; i < N; i++) cin >> C[i];

    vector<vector<bool>> isF(N, vector<bool>(N, false));
    vector<vector<bool>> isO(N, vector<bool>(N, false));

    for (int i = 0; i < N; i++) {
        for (int j = 0; j < N; j++) {
            if (C[i][j] == 'o') isF[i][j] = true;
            else if (C[i][j] == 'x') isO[i][j] = true;
        }
    }

    vector<pair<char,int>> ops;

    for (int i = 0; i < N; i++) {
        for (int j = 0; j < N; j++) {
            if (!isO[i][j]) continue;

            int bestK = INT_MAX;
            int bestDir = -1; // 0:U,1:D,2:L,3:R

            // Up
            {
                bool ok = true;
                for (int r = 0; r < i; r++) {
                    if (isF[r][j]) { ok = false; break; }
                }
                if (ok) {
                    int k = i + 1;
                    if (k < bestK) { bestK = k; bestDir = 0; }
                }
            }
            // Down
            {
                bool ok = true;
                for (int r = i + 1; r < N; r++) {
                    if (isF[r][j]) { ok = false; break; }
                }
                if (ok) {
                    int k = N - i;
                    if (k < bestK) { bestK = k; bestDir = 1; }
                }
            }
            // Left
            {
                bool ok = true;
                for (int c = 0; c < j; c++) {
                    if (isF[i][c]) { ok = false; break; }
                }
                if (ok) {
                    int k = j + 1;
                    if (k < bestK) { bestK = k; bestDir = 2; }
                }
            }
            // Right
            {
                bool ok = true;
                for (int c = j + 1; c < N; c++) {
                    if (isF[i][c]) { ok = false; break; }
                }
                if (ok) {
                    int k = N - j;
                    if (k < bestK) { bestK = k; bestDir = 3; }
                }
            }

            if (bestDir == -1) continue; // should not happen

            int k = bestK;
            if (k <= 0) continue;

            if (bestDir == 0) { // Up
                int col = j;
                for (int t = 0; t < k; t++) ops.emplace_back('U', col);
                for (int t = 0; t < k; t++) ops.emplace_back('D', col);
                for (int r = 0; r < k; r++) isO[r][col] = false;
            } else if (bestDir == 1) { // Down
                int col = j;
                for (int t = 0; t < k; t++) ops.emplace_back('D', col);
                for (int t = 0; t < k; t++) ops.emplace_back('U', col);
                int start = N - k; // equals i
                for (int r = start; r < N; r++) isO[r][col] = false;
            } else if (bestDir == 2) { // Left
                int row = i;
                for (int t = 0; t < k; t++) ops.emplace_back('L', row);
                for (int t = 0; t < k; t++) ops.emplace_back('R', row);
                for (int c = 0; c < k; c++) isO[row][c] = false;
            } else if (bestDir == 3) { // Right
                int row = i;
                for (int t = 0; t < k; t++) ops.emplace_back('R', row);
                for (int t = 0; t < k; t++) ops.emplace_back('L', row);
                int start = N - k; // equals j
                for (int c = start; c < N; c++) isO[row][c] = false;
            }
        }
    }

    for (auto &op : ops) {
        cout << op.first << ' ' << op.second << '\n';
    }

    return 0;
}