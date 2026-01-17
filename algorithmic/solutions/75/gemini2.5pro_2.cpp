#include <iostream>
#include <vector>
#include <string>
#include <algorithm>

using namespace std;

void generate_grid(int r, int c, const vector<string>& grid) {
    cout << r << " " << c << endl;
    for (const string& row : grid) {
        cout << row << endl;
    }
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    long long b, w, x, y;
    cin >> b >> w >> x >> y;

    long long cost1 = -1, cost2 = -1;

    // Strategy 1: Black is the main color, white tiles form separators and islands.
    // This construction is possible if we have enough white components from separators
    // for the required number of white components, i.e., w >= b - 1.
    if (w >= b - 1) {
        long long k = w - (b - 1);
        long long C;
        if (k > 0) {
            C = 2 * k -1;
        } else {
            C = 1;
        }
        
        long long num_black = 0;
        long long num_white = 0;

        if (k > 0) {
            // A special block of 3 rows to create k white islands in a black sea.
            // This contributes 1 black component and k white components.
            num_black += 3 * C - k;
            num_white += k;
            // b-1 simple black blocks (1 row each).
            num_black += (b - 1) * C;
            // b-1 white separator rows.
            num_white += (b - 1) * C;
        } else { // k == 0, means w = b - 1. A simple alternating structure works.
            num_black += b * C;
            num_white += (b - 1) * C;
        }
        cost1 = num_black * x + num_white * y;
    }

    // Strategy 2: White is the main color, black tiles form separators and islands.
    // This is possible if b >= w - 1.
    if (b >= w - 1) {
        long long k = b - (w - 1);
        long long C;
        if (k > 0) {
            C = 2 * k - 1;
        } else {
            C = 1;
        }

        long long num_black = 0;
        long long num_white = 0;

        if (k > 0) {
            // Special block for k black islands in a white sea.
            num_white += 3 * C - k;
            num_black += k;
            // w-1 simple white blocks.
            num_white += (w - 1) * C;
            // w-1 black separator rows.
            num_black += (w - 1) * C;
        } else { // k == 0, means b = w - 1.
            num_white += w * C;
            num_black += (w - 1) * C;
        }
        cost2 = num_black * x + num_white * y;
    }
    
    bool black_main_cheaper;
    if (cost1 != -1 && cost2 != -1) {
        black_main_cheaper = cost1 <= cost2;
    } else if (cost1 != -1) {
        black_main_cheaper = true;
    } else {
        black_main_cheaper = false;
    }
    
    if (black_main_cheaper) {
        long long k = w - (b - 1);
        long long C;
        
        vector<string> grid;
        if (k > 0) {
            C = 2 * k - 1;
            // Special block
            string top_bottom_row(C, '@');
            string middle_row(C, '@');
            for (int i = 0; i < k; ++i) {
                middle_row[2 * i] = '.';
            }
            grid.push_back(top_bottom_row);
            grid.push_back(middle_row);
            grid.push_back(top_bottom_row);

            // Other blocks and separators
            for (int i = 0; i < b - 1; ++i) {
                grid.push_back(string(C, '.'));
                grid.push_back(string(C, '@'));
            }
            generate_grid(3 + 2 * (b - 1), C, grid);
        } else { // k == 0
            C = 1;
            for (int i = 0; i < b; ++i) {
                grid.push_back(string(C, '@'));
                if (i < b - 1) {
                    grid.push_back(string(C, '.'));
                }
            }
            generate_grid(2 * b - 1, C, grid);
        }
    } else { // white main
        long long k = b - (w - 1);
        long long C;

        vector<string> grid;
        if (k > 0) {
            C = 2 * k - 1;
            // Special block
            string top_bottom_row(C, '.');
            string middle_row(C, '.');
            for (int i = 0; i < k; ++i) {
                middle_row[2 * i] = '@';
            }
            grid.push_back(top_bottom_row);
            grid.push_back(middle_row);
            grid.push_back(top_bottom_row);

            // Other blocks and separators
            for (int i = 0; i < w - 1; ++i) {
                grid.push_back(string(C, '@'));
                grid.push_back(string(C, '.'));
            }
            generate_grid(3 + 2 * (w - 1), C, grid);
        } else { // k == 0
            C = 1;
            for (int i = 0; i < w; ++i) {
                grid.push_back(string(C, '.'));
                if (i < w - 1) {
                    grid.push_back(string(C, '@'));
                }
            }
            generate_grid(2 * w - 1, C, grid);
        }
    }

    return 0;
}