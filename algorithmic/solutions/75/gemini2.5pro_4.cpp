#include <iostream>
#include <vector>
#include <string>
#include <algorithm>

using namespace std;

typedef long long ll;

void solve() {
    ll b_orig, w_orig, x_orig, y_orig;
    cin >> b_orig >> w_orig >> x_orig >> y_orig;

    ll b = b_orig, w = w_orig, x = x_orig, y = y_orig;

    bool swapped = false;
    if (x > y) {
        swapped = true;
        swap(b, w);
        swap(x, y);
    }
    // Now x <= y, so the character for 'b' is cheaper or equal cost.

    ll cost1 = -1, cost2 = -1;

    // Strategy 1: "White" sea. "Black" objects.
    // (Sea of the more expensive color)
    // Requires b >= w - 1.
    if (b >= w - 1) {
        ll num_b_tiles = (w > 0 ? 8 * (w - 1) : 0) + (b - (w - 1));
        ll grid_rows = 3;
        ll grid_cols = 4 * b;
        ll num_w_tiles = grid_rows * grid_cols - num_b_tiles;
        cost1 = num_b_tiles * x + num_w_tiles * y;
    }

    // Strategy 2: "Black" sea. "White" objects.
    // (Sea of the cheaper color)
    // Requires w >= b - 1.
    if (w >= b - 1) {
        ll num_w_tiles = (b > 0 ? 8 * (b - 1) : 0) + (w - (b - 1));
        ll grid_rows = 3;
        ll grid_cols = 4 * w;
        ll num_b_tiles = grid_rows * grid_cols - num_w_tiles;
        cost2 = num_b_tiles * x + num_w_tiles * y;
    }
    
    char b_char = swapped ? '.' : '@';
    char w_char = swapped ? '@' : '.';

    if ((cost1 != -1 && cost2 == -1) || (cost1 != -1 && cost2 != -1 && cost1 <= cost2)) {
        // Use Strategy 1: "White" sea, "black" objects.
        ll R = 3;
        ll C = 4 * b;
        vector<string> grid(R, string(C, w_char));

        // w-1 "black" donuts
        for (ll i = 0; i < w - 1; ++i) {
            ll c = 4 * i + 1;
            grid[0][c] = grid[0][c+1] = grid[0][c+2] = b_char;
            grid[1][c] = grid[1][c+2] = b_char;
            grid[2][c] = grid[2][c+1] = grid[2][c+2] = b_char;
        }

        // b-(w-1) "black" singletons
        for (ll i = 0; i < b - (w - 1); ++i) {
            ll c = 4 * (w - 1) + 4 * i + 1;
            grid[1][c] = b_char;
        }
        
        cout << R << " " << C << endl;
        for (int i = 0; i < R; ++i) {
            cout << grid[i] << endl;
        }

    } else {
        // Use Strategy 2: "Black" sea, "white" objects.
        ll R = 3;
        ll C = 4 * w;
        vector<string> grid(R, string(C, b_char));

        // b-1 "white" donuts
        for (ll i = 0; i < b - 1; ++i) {
            ll c = 4 * i + 1;
            grid[0][c] = grid[0][c+1] = grid[0][c+2] = w_char;
            grid[1][c] = grid[1][c+2] = w_char;
            grid[2][c] = grid[2][c+1] = grid[2][c+2] = w_char;
        }

        // w-(b-1) "white" singletons
        for (ll i = 0; i < w - (b - 1); ++i) {
            ll c = 4 * (b - 1) + 4 * i + 1;
            grid[1][c] = w_char;
        }
        
        cout << R << " " << C << endl;
        for (int i = 0; i < R; ++i) {
            cout << grid[i] << endl;
        }
    }
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);
    solve();
    return 0;
}