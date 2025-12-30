#include <iostream>
#include <vector>
#include <string>
#include <algorithm>

using namespace std;

int main() {
    // Optimize standard I/O operations for speed
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    int b, w, x, y;
    if (!(cin >> b >> w >> x >> y)) return 0;

    // We need exactly b black components and w white components.
    // Our strategy is to have two zones stacked vertically:
    // Zone 1: Black background with (w - 1) white single-tile islands.
    // Zone 2: White background with (b - 1) black single-tile islands.
    // The backgrounds of the two zones touch at the boundary (last row of Zone 1 is @, 
    // first row of Zone 2 is .). The black background forms one large black component,
    // and the white background forms one large white component.
    
    int cntW = w - 1; // Number of additional white components needed
    int cntB = b - 1; // Number of additional black components needed

    long long minCost = -1;
    int bestW = -1;
    int bestH1 = -1;
    int bestH2 = -1;

    // Iterate over possible widths W.
    // The constraint on total tiles is 100,000.
    // We check a range of W to find the configuration that minimizes the cost.
    // A wider range up to 50000 is safe given the loop complexity is trivial.
    for (int W = 1; W <= 50000; ++W) { 
        int H1 = 0, H2 = 0;
        
        // Calculate dimensions for Zone 1 (Black base, White islands)
        if (cntW == 0) {
            H1 = 1; // Just one row of black base
        } else {
            int k = W / 2; // Number of islands that fit in one row of width W (pattern @.@.@)
            if (k == 0) continue; // Cannot fit any islands if width is too small
            int rows = (cntW + k - 1) / k; // Number of rows containing islands needed
            H1 = 2 * rows + 1; // Rows are interleaved: Buffer, Island, Buffer, Island, ..., Buffer
        }

        // Calculate dimensions for Zone 2 (White base, Black islands)
        if (cntB == 0) {
            H2 = 1; // Just one row of white base
        } else {
            int k = W / 2;
            if (k == 0) continue;
            int rows = (cntB + k - 1) / k;
            H2 = 2 * rows + 1;
        }

        // Check if total size fits the problem constraints
        long long totalArea = (long long)(H1 + H2) * W;
        if (totalArea > 100000) continue;

        // Calculate tile counts for cost estimation
        // Zone 1: Black background, cntW white tiles.
        long long b1 = (long long)H1 * W - cntW;
        long long w1 = cntW;

        // Zone 2: White background, cntB black tiles.
        long long w2 = (long long)H2 * W - cntB;
        long long b2 = cntB;

        long long totalBlack = b1 + b2;
        long long totalWhite = w1 + w2;
        
        long long currentCost = totalBlack * x + totalWhite * y;

        if (minCost == -1 || currentCost < minCost) {
            minCost = currentCost;
            bestW = W;
            bestH1 = H1;
            bestH2 = H2;
        }
    }

    // Output the best configuration
    int H = bestH1 + bestH2;
    int W = bestW;
    
    cout << H << " " << W << "\n";
    
    // Construct Zone 1: Even rows '@' (Buffer), Odd rows islands
    int placedW = 0;
    for (int r = 0; r < bestH1; ++r) {
        if (r % 2 == 0) {
            for (int c = 0; c < W; ++c) cout << '@';
            cout << "\n";
        } else {
            string row(W, '@');
            // Place islands at indices 1, 3, 5, ...
            for (int c = 1; c < W; c += 2) {
                if (placedW < cntW) {
                    row[c] = '.';
                    placedW++;
                }
            }
            cout << row << "\n";
        }
    }

    // Construct Zone 2: Even rows '.' (Buffer), Odd rows islands
    int placedB = 0;
    for (int r = 0; r < bestH2; ++r) {
        if (r % 2 == 0) {
            for (int c = 0; c < W; ++c) cout << '.';
            cout << "\n";
        } else {
            string row(W, '.');
            // Place islands at indices 1, 3, 5, ...
            for (int c = 1; c < W; c += 2) {
                if (placedB < cntB) {
                    row[c] = '@';
                    placedB++;
                }
            }
            cout << row << "\n";
        }
    }

    return 0;
}