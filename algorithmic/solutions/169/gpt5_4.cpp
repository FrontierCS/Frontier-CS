#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    int N;
    if (!(cin >> N)) return 0;
    vector<string> C(N);
    for (int i = 0; i < N; ++i) cin >> C[i];

    vector<vector<int>> isFuku(N, vector<int>(N, 0));
    vector<vector<int>> isOni(N, vector<int>(N, 0));
    vector<pair<int,int>> onis;
    for (int i = 0; i < N; ++i) {
        for (int j = 0; j < N; ++j) {
            if (C[i][j] == 'o') isFuku[i][j] = 1;
            else if (C[i][j] == 'x') {
                isOni[i][j] = 1;
                onis.emplace_back(i, j);
            }
        }
    }
    int remainingOnis = (int)onis.size();
    const int LIMIT = 4 * N * N;
    vector<pair<char,int>> ops;

    auto safeUp = [&](int i, int j)->bool{
        for (int r = 0; r < i; ++r) if (isFuku[r][j]) return false;
        return true;
    };
    auto safeDown = [&](int i, int j)->bool{
        for (int r = i + 1; r < N; ++r) if (isFuku[r][j]) return false;
        return true;
    };
    auto safeLeft = [&](int i, int j)->bool{
        for (int c = 0; c < j; ++c) if (isFuku[i][c]) return false;
        return true;
    };
    auto safeRight = [&](int i, int j)->bool{
        for (int c = j + 1; c < N; ++c) if (isFuku[i][c]) return false;
        return true;
    };

    auto countRegion = [&](int i, int j, char dir)->int{
        int cnt = 0;
        if (dir == 'U') {
            for (int r = 0; r <= i; ++r) if (isOni[r][j]) ++cnt;
        } else if (dir == 'D') {
            for (int r = i; r < N; ++r) if (isOni[r][j]) ++cnt;
        } else if (dir == 'L') {
            for (int c = 0; c <= j; ++c) if (isOni[i][c]) ++cnt;
        } else if (dir == 'R') {
            for (int c = j; c < N; ++c) if (isOni[i][c]) ++cnt;
        }
        return cnt;
    };

    auto clearRegion = [&](int i, int j, char dir)->int{
        int cleared = 0;
        if (dir == 'U') {
            for (int r = 0; r <= i; ++r) {
                if (isOni[r][j]) { isOni[r][j] = 0; ++cleared; }
            }
        } else if (dir == 'D') {
            for (int r = i; r < N; ++r) {
                if (isOni[r][j]) { isOni[r][j] = 0; ++cleared; }
            }
        } else if (dir == 'L') {
            for (int c = 0; c <= j; ++c) {
                if (isOni[i][c]) { isOni[i][c] = 0; ++cleared; }
            }
        } else if (dir == 'R') {
            for (int c = j; c < N; ++c) {
                if (isOni[i][c]) { isOni[i][c] = 0; ++cleared; }
            }
        }
        remainingOnis -= cleared;
        return cleared;
    };

    auto appendOps = [&](char dir, int p, int s){
        for (int t = 0; t < s; ++t) ops.emplace_back(dir, p);
        char rev;
        if (dir == 'U') rev = 'D';
        else if (dir == 'D') rev = 'U';
        else if (dir == 'L') rev = 'R';
        else rev = 'L';
        for (int t = 0; t < s; ++t) ops.emplace_back(rev, p);
    };

    while (remainingOnis > 0) {
        int bestI = -1, bestJ = -1, bestS = 0, bestK = -1;
        char bestDir = '?';
        int bestScore = INT_MIN;

        for (int i = 0; i < N; ++i) {
            for (int j = 0; j < N; ++j) if (isOni[i][j]) {
                // Evaluate all safe directions
                // Up
                if (safeUp(i, j)) {
                    int s = i + 1;
                    int k = countRegion(i, j, 'U');
                    int score = k * 1000 - 2 * s;
                    if (score > bestScore || (score == bestScore && (k > bestK || (k == bestK && s < bestS)))) {
                        bestScore = score; bestI = i; bestJ = j; bestS = s; bestK = k; bestDir = 'U';
                    }
                }
                // Down
                if (safeDown(i, j)) {
                    int s = N - i;
                    int k = countRegion(i, j, 'D');
                    int score = k * 1000 - 2 * s;
                    if (score > bestScore || (score == bestScore && (k > bestK || (k == bestK && s < bestS)))) {
                        bestScore = score; bestI = i; bestJ = j; bestS = s; bestK = k; bestDir = 'D';
                    }
                }
                // Left
                if (safeLeft(i, j)) {
                    int s = j + 1;
                    int k = countRegion(i, j, 'L');
                    int score = k * 1000 - 2 * s;
                    if (score > bestScore || (score == bestScore && (k > bestK || (k == bestK && s < bestS)))) {
                        bestScore = score; bestI = i; bestJ = j; bestS = s; bestK = k; bestDir = 'L';
                    }
                }
                // Right
                if (safeRight(i, j)) {
                    int s = N - j;
                    int k = countRegion(i, j, 'R');
                    int score = k * 1000 - 2 * s;
                    if (score > bestScore || (score == bestScore && (k > bestK || (k == bestK && s < bestS)))) {
                        bestScore = score; bestI = i; bestJ = j; bestS = s; bestK = k; bestDir = 'R';
                    }
                }
            }
        }

        if (bestDir == '?') break; // Should not happen

        // Check limit; if exceeding, try to pick minimal s action that fits
        if ((int)ops.size() + 2 * bestS > LIMIT) {
            int rest = LIMIT - (int)ops.size();
            int minS = INT_MAX;
            int mi=-1, mj=-1; char md='?';
            for (int i = 0; i < N; ++i) {
                for (int j = 0; j < N; ++j) if (isOni[i][j]) {
                    if (safeUp(i, j)) {
                        int s = i + 1;
                        if (2 * s <= rest && s < minS) { minS = s; mi = i; mj = j; md = 'U'; }
                    }
                    if (safeDown(i, j)) {
                        int s = N - i;
                        if (2 * s <= rest && s < minS) { minS = s; mi = i; mj = j; md = 'D'; }
                    }
                    if (safeLeft(i, j)) {
                        int s = j + 1;
                        if (2 * s <= rest && s < minS) { minS = s; mi = i; mj = j; md = 'L'; }
                    }
                    if (safeRight(i, j)) {
                        int s = N - j;
                        if (2 * s <= rest && s < minS) { minS = s; mi = i; mj = j; md = 'R'; }
                    }
                }
            }
            if (md == '?') break;
            bestI = mi; bestJ = mj; bestS = minS; bestDir = md;
        }

        // Append operations
        if (bestDir == 'U' || bestDir == 'D') {
            appendOps(bestDir, bestJ, bestS);
        } else {
            appendOps(bestDir, bestI, bestS);
        }
        // Clear region
        clearRegion(bestI, bestJ, bestDir);
    }

    // Output operations
    for (auto &op : ops) {
        cout << op.first << ' ' << op.second << '\n';
    }
    return 0;
}