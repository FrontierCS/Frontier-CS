#include <iostream>
#include <vector>
#include <algorithm>
using namespace std;

int main() {
    const int N = 30;
    vector<vector<int>> a(N, vector<int>(N, -1));
    
    // Read input
    for (int x = 0; x < N; ++x) {
        for (int y = 0; y <= x; ++y) {
            cin >> a[x][y];
        }
    }
    
    vector<array<int, 4>> swaps;
    
    // Bottom-up heapify
    for (int x = N-2; x >= 0; --x) {
        for (int y = 0; y <= x; ++y) {
            int cx = x, cy = y;
            while (true) {
                if (cx+1 >= N) break; // no children
                int left_x = cx+1, left_y = cy;
                int right_x = cx+1, right_y = cy+1;
                // Determine the smaller child
                int small_x, small_y;
                if (a[left_x][left_y] < a[right_x][right_y]) {
                    small_x = left_x; small_y = left_y;
                } else {
                    small_x = right_x; small_y = right_y;
                }
                if (a[cx][cy] <= a[small_x][small_y]) break;
                // Swap with the smaller child
                swap(a[cx][cy], a[small_x][small_y]);
                swaps.push_back({cx, cy, small_x, small_y});
                // Move down
                cx = small_x;
                cy = small_y;
            }
        }
    }
    
    // Output
    cout << swaps.size() << endl;
    for (auto& s : swaps) {
        cout << s[0] << " " << s[1] << " " << s[2] << " " << s[3] << endl;
    }
    
    return 0;
}