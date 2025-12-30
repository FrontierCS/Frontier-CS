#include <bits/stdc++.h>
using namespace std;

const int H = 50;
const int W = 50;
const int di[4] = {-1, 1, 0, 0};
const int dj[4] = {0, 0, -1, 1};
const char dch[4] = {'U', 'D', 'L', 'R'};
const int DEPTH = 6;

int si, sj;
int tid[H][W];
int pval[H][W];
vector<char> visitedTile;

int dfs(int i, int j, int depth) {
    if (depth == 0) return 0;
    int best = 0;
    for (int dir = 0; dir < 4; ++dir) {
        int ni = i + di[dir];
        int nj = j + dj[dir];
        if (ni < 0 || ni >= H || nj < 0 || nj >= W) continue;
        int t = tid[ni][nj];
        if (visitedTile[t]) continue;
        visitedTile[t] = 1;
        int val = pval[ni][nj] + dfs(ni, nj, depth - 1);
        visitedTile[t] = 0;
        if (val > best) best = val;
    }
    return best;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    cin >> si >> sj;
    int maxT = -1;
    for (int i = 0; i < H; ++i) {
        for (int j = 0; j < W; ++j) {
            cin >> tid[i][j];
            if (tid[i][j] > maxT) maxT = tid[i][j];
        }
    }
    for (int i = 0; i < H; ++i) {
        for (int j = 0; j < W; ++j) {
            cin >> pval[i][j];
        }
    }

    int M = maxT + 1;
    visitedTile.assign(M, 0);

    int ci = si, cj = sj;
    visitedTile[tid[ci][cj]] = 1;

    string path;
    while (true) {
        int bestScore = -1;
        int bestDir = -1;
        for (int dir = 0; dir < 4; ++dir) {
            int ni = ci + di[dir];
            int nj = cj + dj[dir];
            if (ni < 0 || ni >= H || nj < 0 || nj >= W) continue;
            int t = tid[ni][nj];
            if (visitedTile[t]) continue;
            visitedTile[t] = 1;
            int future = dfs(ni, nj, DEPTH - 1);
            visitedTile[t] = 0;
            int val = pval[ni][nj] + future;
            if (val > bestScore) {
                bestScore = val;
                bestDir = dir;
            }
        }
        if (bestDir == -1) break;
        ci += di[bestDir];
        cj += dj[bestDir];
        visitedTile[tid[ci][cj]] = 1;
        path.push_back(dch[bestDir]);
    }

    cout << path << '\n';
    return 0;
}