#include <iostream>
#include <vector>
#include <array>

using namespace std;

const int N = 30;
int b[N][N]; // balls, only use b[x][y] for 0 <= y <= x < N

struct Swap {
    int x1, y1, x2, y2;
};

vector<Swap> swaps;

void swap_balls(int x1, int y1, int x2, int y2) {
    swaps.push_back({x1, y1, x2, y2});
    swap(b[x1][y1], b[x2][y2]);
}

void sift_down(int x, int y) {
    while (x < N - 1) {
        int left = b[x+1][y];
        int right = b[x+1][y+1];
        int cur = b[x][y];
        if (cur <= left && cur <= right) {
            break;
        }
        if (left < right) {
            swap_balls(x, y, x+1, y);
            x = x+1;
            // y stays y
        } else {
            swap_balls(x, y, x+1, y+1);
            x = x+1;
            y = y+1;
        }
    }
}

int main() {
    // read input
    for (int x = 0; x < N; ++x) {
        for (int y = 0; y <= x; ++y) {
            cin >> b[x][y];
        }
    }

    // heapify from bottom row upward
    for (int x = N-2; x >= 0; --x) {
        for (int y = 0; y <= x; ++y) {
            sift_down(x, y);
        }
    }

    // output
    cout << swaps.size() << endl;
    for (const Swap& s : swaps) {
        cout << s.x1 << " " << s.y1 << " " << s.x2 << " " << s.y2 << endl;
    }

    return 0;
}