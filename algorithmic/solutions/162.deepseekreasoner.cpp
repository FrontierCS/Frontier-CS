#include <iostream>
#include <vector>
#include <algorithm>
using namespace std;

const int N = 30;
const int MAX_BALLS = 465;

int grid[N][N];
int pos_x[MAX_BALLS], pos_y[MAX_BALLS];
int swaps_count = 0;
vector<tuple<int, int, int, int>> swaps;

void swap_balls(int x1, int y1, int x2, int y2) {
    int v1 = grid[x1][y1];
    int v2 = grid[x2][y2];
    grid[x1][y1] = v2;
    grid[x2][y2] = v1;
    pos_x[v1] = x2;
    pos_y[v1] = y2;
    pos_x[v2] = x1;
    pos_y[v2] = y1;
    swaps.emplace_back(x1, y1, x2, y2);
    ++swaps_count;
}

void sift_down(int x, int y, bool& changed) {
    while (x < N - 1) {
        int cur = grid[x][y];
        int left = grid[x+1][y];
        int right = grid[x+1][y+1];
        if (cur <= left && cur <= right) break;
        changed = true;
        if (left < right) {
            swap_balls(x, y, x+1, y);
            x = x + 1; // y unchanged
        } else {
            swap_balls(x, y, x+1, y+1);
            x = x + 1;
            y = y + 1;
        }
        if (swaps_count >= 10000) return;
    }
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(0);

    // Read input
    for (int x = 0; x < N; ++x) {
        for (int y = 0; y <= x; ++y) {
            cin >> grid[x][y];
        }
    }

    // Initialize positions
    for (int x = 0; x < N; ++x) {
        for (int y = 0; y <= x; ++y) {
            int v = grid[x][y];
            pos_x[v] = x;
            pos_y[v] = y;
        }
    }

    // Heapify by repeated bottom-up passes
    bool changed;
    do {
        changed = false;
        for (int x = N-2; x >= 0; --x) {
            for (int y = 0; y <= x; ++y) {
                sift_down(x, y, changed);
                if (swaps_count >= 10000) break;
            }
            if (swaps_count >= 10000) break;
        }
        if (swaps_count >= 10000) break;
    } while (changed);

    // Output
    cout << swaps_count << '\n';
    for (auto [x1, y1, x2, y2] : swaps) {
        cout << x1 << ' ' << y1 << ' ' << x2 << ' ' << y2 << '\n';
    }
    return 0;
}