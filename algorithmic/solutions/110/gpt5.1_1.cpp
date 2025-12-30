#include <bits/stdc++.h>
using namespace std;

const int H = 8, W = 14, NODES = H * W;
const int MAX_NUM = 300;

vector<char> numDigits[MAX_NUM + 1];
vector<int> adjList[NODES];

mt19937_64 rng(chrono::steady_clock::now().time_since_epoch().count());

bool canRead(const char grid[], const vector<char> &ds) {
    int L = (int)ds.size();
    bool cur[NODES] = {0};
    bool nxt[NODES];

    char t0 = ds[0];
    for (int i = 0; i < NODES; ++i) {
        if (grid[i] == t0) cur[i] = true;
    }

    for (int p = 1; p < L; ++p) {
        memset(nxt, 0, sizeof(nxt));
        char t = ds[p];
        for (int j = 0; j < NODES; ++j) {
            if (grid[j] != t) continue;
            const vector<int> &nb = adjList[j];
            for (int v : nb) {
                if (cur[v]) {
                    nxt[j] = true;
                    break;
                }
            }
        }
        for (int i = 0; i < NODES; ++i) cur[i] = nxt[i];
    }

    for (int i = 0; i < NODES; ++i) if (cur[i]) return true;
    return false;
}

int evaluate(const char grid[]) {
    for (int n = 1; n <= MAX_NUM; ++n) {
        if (!canRead(grid, numDigits[n])) return n - 1;
    }
    return MAX_NUM;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    // Precompute digit representations
    for (int n = 1; n <= MAX_NUM; ++n) {
        string s = to_string(n);
        numDigits[n] = vector<char>(s.begin(), s.end());
    }

    // Build adjacency list (8 directions)
    int dr[8] = {-1,-1,-1,0,0,1,1,1};
    int dc[8] = {-1,0,1,-1,1,-1,0,1};
    for (int id = 0; id < NODES; ++id) {
        int r = id / W;
        int c = id % W;
        for (int k = 0; k < 8; ++k) {
            int nr = r + dr[k], nc = c + dc[k];
            if (nr >= 0 && nr < H && nc >= 0 && nc < W) {
                int nid = nr * W + nc;
                adjList[id].push_back(nid);
            }
        }
    }

    char curGrid[NODES];
    char bestGrid[NODES];

    // Initial random grid
    for (int i = 0; i < NODES; ++i) {
        curGrid[i] = char('0' + (rng() % 10));
        bestGrid[i] = curGrid[i];
    }

    int bestScore = evaluate(curGrid);

    auto start = chrono::steady_clock::now();
    const double timeLimit = 0.9; // seconds

    while (true) {
        double elapsed = chrono::duration<double>(chrono::steady_clock::now() - start).count();
        if (elapsed > timeLimit) break;

        int pos = (int)(rng() % NODES);
        char oldVal = curGrid[pos];
        char newVal = oldVal;
        while (newVal == oldVal) {
            newVal = char('0' + (rng() % 10));
        }
        curGrid[pos] = newVal;

        int score = evaluate(curGrid);
        if (score > bestScore || (score == bestScore && (rng() & 1))) {
            bestScore = score;
            for (int i = 0; i < NODES; ++i) bestGrid[i] = curGrid[i];
        } else {
            curGrid[pos] = oldVal;
        }
    }

    // Output best grid found
    for (int r = 0; r < H; ++r) {
        for (int c = 0; c < W; ++c) {
            cout << bestGrid[r * W + c];
        }
        cout << '\n';
    }

    return 0;
}