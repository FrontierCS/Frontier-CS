#include <bits/stdc++.h>
using namespace std;
using namespace chrono;

const int ROWS = 8;
const int COLS = 14;
const int CELLS = ROWS * COLS;
const int LIMIT = 5000; // test numbers up to this

mt19937 rng(steady_clock::now().time_since_epoch().count());
uniform_int_distribution<int> dist(0, 9);

struct Grid {
    char g[ROWS][COLS];
    vector<int> neighbors[CELLS];
    vector<int> digit_cells[10];

    void build() {
        // fill grid randomly
        for (int i = 0; i < ROWS; ++i)
            for (int j = 0; j < COLS; ++j)
                g[i][j] = dist(rng) + '0';

        // precompute neighbors and digit positions
        for (int i = 0; i < CELLS; ++i) neighbors[i].clear();
        for (int d = 0; d < 10; ++d) digit_cells[d].clear();

        for (int i = 0; i < ROWS; ++i) {
            for (int j = 0; j < COLS; ++j) {
                int idx = i * COLS + j;
                int d = g[i][j] - '0';
                digit_cells[d].push_back(idx);

                for (int di = -1; di <= 1; ++di) {
                    for (int dj = -1; dj <= 1; ++dj) {
                        if (di == 0 && dj == 0) continue;
                        int ni = i + di, nj = j + dj;
                        if (ni >= 0 && ni < ROWS && nj >= 0 && nj < COLS) {
                            int nidx = ni * COLS + nj;
                            neighbors[idx].push_back(nidx);
                        }
                    }
                }
            }
        }
    }

    // check if a single number can be read
    bool test(int n) {
        string s = to_string(n);
        int L = s.size();

        vector<bool> cur(CELLS, false), nxt(CELLS, false);
        // initial layer: cells matching first digit
        for (int idx : digit_cells[s[0] - '0'])
            cur[idx] = true;

        for (int k = 1; k < L; ++k) {
            fill(nxt.begin(), nxt.end(), false);
            char need = s[k];
            for (int idx = 0; idx < CELLS; ++idx) {
                if (cur[idx]) {
                    for (int nidx : neighbors[idx]) {
                        if (g[nidx / COLS][nidx % COLS] == need) {
                            nxt[nidx] = true;
                        }
                    }
                }
            }
            swap(cur, nxt);
        }

        for (int idx = 0; idx < CELLS; ++idx)
            if (cur[idx]) return true;
        return false;
    }

    // return first missing number up to LIMIT (or LIMIT+1 if all readable)
    int first_missing() {
        for (int n = 1; n <= LIMIT; ++n)
            if (!test(n)) return n;
        return LIMIT + 1;
    }
};

int main() {
    auto start = steady_clock::now();
    auto deadline = start + milliseconds(55000); // run for 55 seconds

    Grid best_grid;
    int best_score = 0; // X = first_missing - 1

    while (steady_clock::now() < deadline) {
        Grid cur;
        cur.build();
        int missing = cur.first_missing();
        int X = missing - 1;
        if (X > best_score) {
            best_score = X;
            best_grid = cur;
        }
    }

    // output the best grid found
    for (int i = 0; i < ROWS; ++i) {
        for (int j = 0; j < COLS; ++j)
            cout << best_grid.g[i][j];
        cout << '\n';
    }

    return 0;
}