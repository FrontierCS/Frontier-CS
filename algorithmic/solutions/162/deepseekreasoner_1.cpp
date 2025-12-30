#include <iostream>
#include <vector>
#include <algorithm>
using namespace std;

const int N = 30;

int b[N][N]; // ball numbers

struct Swap {
    int x1, y1, x2, y2;
};

vector<Swap> swaps;

void perform_swap(int x1, int y1, int x2, int y2) {
    swaps.push_back({x1, y1, x2, y2});
    swap(b[x1][y1], b[x2][y2]);
}

int main() {
    // input
    for (int x = 0; x < N; ++x) {
        for (int y = 0; y <= x; ++y) {
            cin >> b[x][y];
        }
    }

    int total_swaps = 0;
    const int MAX_SWAPS = 10000;
    bool changed = true;
    while (changed && total_swaps < MAX_SWAPS) {
        changed = false;
        // bottom-up pass: process tiers from second last to top
        for (int x = N-2; x >= 0; --x) {
            for (int y = 0; y <= x; ++y) {
                // sift down the ball at (x,y)
                int cx = x, cy = y;
                while (cx < N-1) {
                    int cur = b[cx][cy];
                    int left = b[cx+1][cy];
                    int right = b[cx+1][cy+1];
                    if (cur < left && cur < right) {
                        // heap condition satisfied
                        break;
                    }
                    // find smaller child
                    int swap_x, swap_y;
                    if (left < right) {
                        swap_x = cx+1;
                        swap_y = cy;
                    } else {
                        swap_x = cx+1;
                        swap_y = cy+1;
                    }
                    perform_swap(cx, cy, swap_x, swap_y);
                    total_swaps++;
                    changed = true;
                    if (total_swaps >= MAX_SWAPS) break;
                    // update current position to the child
                    cx = swap_x;
                    cy = swap_y;
                }
                if (total_swaps >= MAX_SWAPS) break;
            }
            if (total_swaps >= MAX_SWAPS) break;
        }
    }

    // output
    cout << swaps.size() << endl;
    for (const Swap& s : swaps) {
        cout << s.x1 << " " << s.y1 << " " << s.x2 << " " << s.y2 << endl;
    }

    return 0;
}