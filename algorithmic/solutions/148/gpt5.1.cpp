#include <bits/stdc++.h>
using namespace std;

const int H = 50;
const int W = 50;

int si, sj;
int tileId[H][W];
int scoreVal[H][W];

int dr[4] = {-1, 1, 0, 0};
int dc[4] = {0, 0, -1, 1};
char dirChar[4] = {'U', 'D', 'L', 'R'};

int runGreedy(mt19937_64 &rng, vector<char> &visited, int alpha, string &outPath) {
    fill(visited.begin(), visited.end(), 0);
    outPath.clear();

    int r = si, c = sj;
    int curTile = tileId[r][c];
    visited[curTile] = 1;
    int totalScore = scoreVal[r][c];

    while (true) {
        int bestDir = -1;
        int bestVal = INT_MIN;
        int bestR = r, bestC = c, bestTile = curTile;

        for (int d = 0; d < 4; d++) {
            int nr = r + dr[d];
            int nc = c + dc[d];
            if (nr < 0 || nr >= H || nc < 0 || nc >= W) continue;
            int tile2 = tileId[nr][nc];
            if (visited[tile2]) continue;

            int deg = 0;
            for (int d2 = 0; d2 < 4; d2++) {
                int mr = nr + dr[d2];
                int mc = nc + dc[d2];
                if (mr < 0 || mr >= H || mc < 0 || mc >= W) continue;
                int tileNext = tileId[mr][mc];
                if (!visited[tileNext] && tileNext != tile2) deg++;
            }

            int val = scoreVal[nr][nc] + alpha * deg;
            if (val > bestVal || (val == bestVal && (rng() & 1))) {
                bestVal = val;
                bestDir = d;
                bestR = nr;
                bestC = nc;
                bestTile = tile2;
            }
        }

        if (bestDir == -1) break;

        r = bestR;
        c = bestC;
        curTile = bestTile;
        visited[curTile] = 1;
        totalScore += scoreVal[r][c];
        outPath.push_back(dirChar[bestDir]);
    }

    return totalScore;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    if (!(cin >> si >> sj)) return 0;

    int maxTile = 0;
    for (int i = 0; i < H; i++) {
        for (int j = 0; j < W; j++) {
            cin >> tileId[i][j];
            maxTile = max(maxTile, tileId[i][j]);
        }
    }
    for (int i = 0; i < H; i++) {
        for (int j = 0; j < W; j++) {
            cin >> scoreVal[i][j];
        }
    }

    int M = maxTile + 1;
    vector<char> visited(M);

    mt19937_64 rng(chrono::steady_clock::now().time_since_epoch().count());

    auto start = chrono::steady_clock::now();
    const long long TIME_LIMIT_NS = 1800000000LL; // ~1.8 seconds

    string bestPath;
    int bestScore = -1;

    while (true) {
        long long elapsed = chrono::duration_cast<chrono::nanoseconds>(
                                chrono::steady_clock::now() - start)
                                .count();
        if (elapsed > TIME_LIMIT_NS) break;

        int alpha = 10 + (int)(rng() % 21); // 10..30
        string path;
        int sc = runGreedy(rng, visited, alpha, path);
        if (sc > bestScore) {
            bestScore = sc;
            bestPath = path;
        }
    }

    cout << bestPath << '\n';
    return 0;
}