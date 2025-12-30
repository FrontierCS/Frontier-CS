#include <iostream>
#include <vector>
#include <tuple>
#include <algorithm>

using namespace std;

const int N = 30;
vector<vector<int>> val(N);
vector<tuple<int, int, int, int>> swaps;

void record_swap(int x1, int y1, int x2, int y2) {
    swaps.emplace_back(x1, y1, x2, y2);
    swap(val[x1][y1], val[x2][y2]);
}

void sift_down(int x, int y) {
    while (x < N - 1) {
        int left_x = x + 1, left_y = y;
        int right_x = x + 1, right_y = y + 1;
        int cur = val[x][y];
        int left_val = val[left_x][left_y];
        int right_val = val[right_x][right_y];
        if (cur <= left_val && cur <= right_val) break;
        if (left_val < right_val) {
            record_swap(x, y, left_x, left_y);
            x = left_x; y = left_y;
        } else {
            record_swap(x, y, right_x, right_y);
            x = right_x; y = right_y;
        }
        if (swaps.size() >= 10000) return;
    }
}

int main() {
    // read input
    for (int x = 0; x < N; ++x) {
        val[x].resize(x + 1);
        for (int y = 0; y <= x; ++y) {
            cin >> val[x][y];
        }
    }

    // heapify from bottom up
    for (int x = N - 2; x >= 0; --x) {
        for (int y = 0; y <= x; ++y) {
            sift_down(x, y);
            if (swaps.size() >= 10000) goto finish;
        }
    }

    // bubble phase: repeatedly fix parent > child violations
    bool changed;
    do {
        changed = false;
        for (int x = 0; x <= N - 2; ++x) {
            for (int y = 0; y <= x; ++y) {
                // check child (x+1, y)
                if (val[x][y] > val[x+1][y]) {
                    record_swap(x, y, x+1, y);
                    changed = true;
                    if (swaps.size() >= 10000) goto finish;
                }
                // check child (x+1, y+1)
                if (val[x][y] > val[x+1][y+1]) {
                    record_swap(x, y, x+1, y+1);
                    changed = true;
                    if (swaps.size() >= 10000) goto finish;
                }
            }
        }
    } while (changed);

finish:
    // output
    cout << swaps.size() << endl;
    for (auto& s : swaps) {
        cout << get<0>(s) << " " << get<1>(s) << " "
             << get<2>(s) << " " << get<3>(s) << endl;
    }
    return 0;
}