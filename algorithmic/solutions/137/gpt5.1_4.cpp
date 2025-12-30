#include <iostream>
#include <vector>
#include <array>
#include <random>
#include <utility>
#include <algorithm>

using namespace std;

const int N = 20;
const int M = 20;

using Grid = array<array<char, M>, N>;

int occ[2][N][M];

int countAdj(const Grid &g, int x, int y) {
    int cnt = 0;
    static const int dx[4] = {-1, 1, 0, 0};
    static const int dy[4] = {0, 0, -1, 1};
    for (int k = 0; k < 4; ++k) {
        int nx = x + dx[k], ny = y + dy[k];
        if (nx >= 0 && nx < N && ny >= 0 && ny < M && g[nx][ny] == '1') {
            ++cnt;
        }
    }
    return cnt;
}

void buildTree(mt19937 &rng, Grid &g) {
    for (int i = 0; i < N; ++i)
        for (int j = 0; j < M; ++j)
            g[i][j] = '0';

    int rootX = N / 2;
    int rootY = M / 2;
    g[rootX][rootY] = '1';

    vector<pair<int,int>> frontier;
    static const int dx[4] = {-1, 1, 0, 0};
    static const int dy[4] = {0, 0, -1, 1};

    auto tryAddFront = [&](int x, int y) {
        if (x < 0 || x >= N || y < 0 || y >= M) return;
        if (g[x][y] == '1') return;
        if (countAdj(g, x, y) == 1) frontier.emplace_back(x, y);
    };

    for (int k = 0; k < 4; ++k) {
        tryAddFront(rootX + dx[k], rootY + dy[k]);
    }

    while (!frontier.empty()) {
        int idx = (int)(rng() % frontier.size());
        auto cell = frontier[idx];
        frontier[idx] = frontier.back();
        frontier.pop_back();

        int x = cell.first, y = cell.second;
        if (g[x][y] == '1') continue;
        if (countAdj(g, x, y) != 1) continue;

        g[x][y] = '1';
        for (int k = 0; k < 4; ++k) {
            tryAddFront(x + dx[k], y + dy[k]);
        }
    }
}

int evaluate(const Grid &g, mt19937 &rng) {
    vector<pair<int,int>> cells;
    for (int i = 0; i < N; ++i)
        for (int j = 0; j < M; ++j)
            if (g[i][j] == '1')
                cells.emplace_back(i, j);

    int K = (int)cells.size();
    if (K < 2) return -1000000; // invalid / very bad

    const int TRIALS = 40;
    const int STEPS = 200;

    int fail = 0;

    for (int t = 0; t < TRIALS; ++t) {
        // zero occupancy arrays
        for (int z = 0; z < 2; ++z)
            for (int i = 0; i < N; ++i)
                for (int j = 0; j < M; ++j)
                    occ[z][i][j] = 0;

        int cur = 0, nxt = 1;
        for (auto &p : cells) {
            occ[cur][p.first][p.second] = 1;
        }

        for (int step = 0; step < STEPS; ++step) {
            int dir = (int)(rng() % 4); // 0=U,1=D,2=L,3=R

            // clear next layer on empty cells
            for (auto &p : cells) {
                occ[nxt][p.first][p.second] = 0;
            }

            for (auto &p : cells) {
                int x = p.first, y = p.second;
                int c = occ[cur][x][y];
                if (!c) continue;
                int nx = x, ny = y;
                if (dir == 0) { // U
                    if (x > 0 && g[x-1][y] == '1') nx = x - 1;
                } else if (dir == 1) { // D
                    if (x + 1 < N && g[x+1][y] == '1') nx = x + 1;
                } else if (dir == 2) { // L
                    if (y > 0 && g[x][y-1] == '1') ny = y - 1;
                } else { // R
                    if (y + 1 < M && g[x][y+1] == '1') ny = y + 1;
                }
                occ[nxt][nx][ny] += c;
            }
            swap(cur, nxt);
        }

        bool allSame = false;
        for (auto &p : cells) {
            if (occ[cur][p.first][p.second] == K) {
                allSame = true;
                break;
            }
        }
        if (!allSame) ++fail;
    }

    return fail;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    const int NUM_CANDIDATES = 7;
    const unsigned int base1 = 123456789u;
    const unsigned int base2 = 362436069u;

    Grid bestG{};
    int bestScore = -1;
    int bestOnes = -1;

    for (int c = 0; c < NUM_CANDIDATES; ++c) {
        mt19937 rngBuild(base1 + c * 101u);
        Grid g;
        buildTree(rngBuild, g);

        mt19937 rngSim(base2 + c * 797u);
        int score = evaluate(g, rngSim);

        int ones = 0;
        for (int i = 0; i < N; ++i)
            for (int j = 0; j < M; ++j)
                if (g[i][j] == '1') ++ones;

        if (score > bestScore || (score == bestScore && ones > bestOnes)) {
            bestScore = score;
            bestOnes = ones;
            bestG = g;
        }
    }

    cout << N << " " << M << "\n";
    for (int i = 0; i < N; ++i) {
        for (int j = 0; j < M; ++j)
            cout << bestG[i][j];
        cout << '\n';
    }

    return 0;
}