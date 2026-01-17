#include <iostream>
#include <vector>
#include <string>
#include <algorithm>

using namespace std;

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    int b, w, x, y;
    cin >> b >> w >> x >> y;

    char black_char = '@';
    char white_char = '.';

    long long cost_b_ge_w = -1;
    if (b >= w) {
        cost_b_ge_w = (long long)x * (b + w) + (long long)y * (3 * b - w);
    }
    long long cost_w_gt_b = -1;
    if (w > b) {
        cost_w_gt_b = (long long)x * (3 * w - b) + (long long)y * (w + b);
    }

    long long cost_b_ge_w_swapped = -1;
    if (b >= w) {
        cost_b_ge_w_swapped = (long long)y * (b + w) + (long long)x * (3 * b - w);
    }
    long long cost_w_gt_b_swapped = -1;
    if (w > b) {
        cost_w_gt_b_swapped = (long long)y * (3 * w - b) + (long long)x * (w + b);
    }

    long long cost1 = (b >= w) ? cost_b_ge_w : cost_w_gt_b;
    long long cost2 = (b >= w) ? cost_b_ge_w_swapped : cost_w_gt_b_swapped;

    if (cost2 < cost1) {
        swap(black_char, white_char);
    }
    
    if (b >= w) {
        int k = b;
        int r = 2;
        int c = 2 * k;
        cout << r << " " << c << endl;
        vector<string> grid(r, string(c, ' '));

        for (int i = 0; i < r; ++i) {
            for (int j = 0; j < c; ++j) {
                if ((j % 2) == 0) grid[i][j] = white_char;
                else grid[i][j] = black_char;
            }
        }

        int merges_needed = b - w;
        for (int i = 0; i < merges_needed; ++i) {
            grid[0][2 * i + 1] = white_char;
        }

        for (int i = 0; i < r; ++i) {
            cout << grid[i] << endl;
        }
    } else { // w > b
        int k = w;
        int r = 2;
        int c = 2 * k;
        cout << r << " " << c << endl;
        vector<string> grid(r, string(c, ' '));
        
        for (int i = 0; i < r; ++i) {
            for (int j = 0; j < c; ++j) {
                if ((j % 2) == 0) grid[i][j] = black_char;
                else grid[i][j] = white_char;
            }
        }
        
        int merges_needed = w - b;
        for (int i = 0; i < merges_needed; ++i) {
            grid[0][2 * i + 1] = black_char;
        }
        
        for (int i = 0; i < r; ++i) {
            cout << grid[i] << endl;
        }
    }

    return 0;
}